"""
FastAPI Router - WebSocket Chat con Token Streaming

DOMINIO: Brasaland Digital - Agente de Soporte
Usuario: Equipo Interno (Operaciones, RRHH, Dirección)

CARACTERÍSTICAS CRÍTICAS:
- WebSocket bidireccional (envío + recepción concurrentes)
- Token streaming en tiempo real desde LangGraph
- Abort genuino de generación (asyncio.Task.cancel())
- Preservación de mensajes parciales (status=interrupted)
- Reconexión con rehidratación de historial
- Autenticación JWT via query string
- Pub/Sub desacoplado (multi-observador por sesión)

DIFERENCIACIÓN:
- Abort stream ≠ LangGraph interrupt() HITL
- Abort cancela Task de generación, interrupt() pausa grafo
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Optional, Set, Any
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.websockets import WebSocketState

# Placeholder imports (ajustar según implementación real)
# from services.agent.graph import get_agent_graph
# from services.auth import verify_jwt_token
# from services.database import get_chat_history, save_message

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/ws", tags=["WebSocket Chat"])


# ============================================================
# CONNECTION MANAGER - PUB/SUB DESACOPLADO
# ============================================================

class ChatSessionManager:
    """
    Gestor de conexiones WebSocket con Pub/Sub por sesión.

    ARQUITECTURA:
    - 1 generador de tokens (productor) por session_id
    - N WebSockets (consumidores) pueden observar la misma sesión
    - Cada WebSocket tiene su propia asyncio.Queue
    - El productor broadcast a todas las queues de la sesión

    CASO DE USO:
    - Supervisor observa conversación de agente con empleado
    - Dashboard muestra chat en vivo
    """

    def __init__(self):
        # session_id -> Set[connection_id]
        self.sessions: Dict[str, Set[str]] = {}

        # connection_id -> WebSocket
        self.connections: Dict[str, WebSocket] = {}

        # connection_id -> asyncio.Queue
        self.queues: Dict[str, asyncio.Queue] = {}

        # session_id -> asyncio.Task (tarea de generación activa)
        self.active_generations: Dict[str, asyncio.Task] = {}

        # session_id -> str (message_id del mensaje en generación)
        self.current_message_ids: Dict[str, str] = {}

        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        connection_id: str
    ):
        """Registra nueva conexión WebSocket a una sesión."""
        async with self._lock:
            # Aceptar WebSocket
            await websocket.accept()

            # Registrar conexión
            self.connections[connection_id] = websocket

            # Crear queue para eventos
            self.queues[connection_id] = asyncio.Queue(maxsize=100)

            # Agregar a sesión
            if session_id not in self.sessions:
                self.sessions[session_id] = set()
            self.sessions[session_id].add(connection_id)

            logger.info(
                f"[WS] Cliente conectado: {connection_id} → sesión {session_id} "
                f"({len(self.sessions[session_id])} observadores)"
            )

    async def disconnect(self, connection_id: str, session_id: str):
        """Desregistra conexión WebSocket."""
        async with self._lock:
            # Remover de sesión
            if session_id in self.sessions:
                self.sessions[session_id].discard(connection_id)

                # Limpiar sesión vacía
                if not self.sessions[session_id]:
                    del self.sessions[session_id]

                    # Cancelar generación activa si no hay observadores
                    if session_id in self.active_generations:
                        self.active_generations[session_id].cancel()
                        del self.active_generations[session_id]

            # Limpiar recursos
            self.connections.pop(connection_id, None)
            self.queues.pop(connection_id, None)

            logger.info(f"[WS] Cliente desconectado: {connection_id}")

    async def broadcast_to_session(
        self,
        session_id: str,
        event: Dict[str, Any]
    ):
        """
        Broadcast de evento a todos los WebSockets de una sesión.

        Patrón Pub/Sub: 1 productor → N consumidores
        """
        async with self._lock:
            if session_id not in self.sessions:
                return

            # Encolar evento en todas las queues de la sesión
            for connection_id in self.sessions[session_id]:
                queue = self.queues.get(connection_id)
                if queue:
                    try:
                        queue.put_nowait(event)
                    except asyncio.QueueFull:
                        logger.warning(
                            f"[WS] Queue llena para {connection_id}, "
                            f"descartando evento {event.get('type')}"
                        )

    async def send_to_connection(
        self,
        connection_id: str,
        event: Dict[str, Any]
    ):
        """Envía evento a una conexión específica."""
        websocket = self.connections.get(connection_id)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json(event)
            except Exception as e:
                logger.error(f"[WS] Error enviando a {connection_id}: {e}")

    def set_active_generation(
        self,
        session_id: str,
        task: asyncio.Task,
        message_id: str
    ):
        """Registra la tarea de generación activa."""
        self.active_generations[session_id] = task
        self.current_message_ids[session_id] = message_id

    async def abort_generation(self, session_id: str) -> Optional[str]:
        """
        Cancela la generación activa de una sesión.

        Returns:
            message_id del mensaje interrumpido, o None si no había generación
        """
        task = self.active_generations.get(session_id)
        message_id = self.current_message_ids.get(session_id)

        if task and not task.done():
            # ABORT GENUINO: Cancelar tarea asyncio
            task.cancel()
            logger.info(f"[WS] Generación abortada para sesión {session_id}")

            # Limpiar referencias
            del self.active_generations[session_id]
            del self.current_message_ids[session_id]

            return message_id

        return None


# Singleton global
session_manager = ChatSessionManager()


# ============================================================
# JWT AUTHENTICATION
# ============================================================

async def verify_jwt_from_query(token: Optional[str]) -> str:
    """
    Verifica token JWT desde query string.

    Args:
        token: JWT desde query param ?token=...

    Returns:
        user_id extraído del token

    Raises:
        HTTPException 401 si token inválido
    """
    if not token:
        raise HTTPException(401, "Missing token in query string")

    # TODO: Implementar validación JWT real
    # from jose import jwt
    # try:
    #     payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    #     user_id = payload.get("sub")
    #     if not user_id:
    #         raise HTTPException(401, "Invalid token payload")
    #     return user_id
    # except JWTError:
    #     raise HTTPException(401, "Invalid token")

    # Mock: Aceptar token no vacío
    if len(token) < 10:
        raise HTTPException(401, "Invalid token")

    return "user_mock_id"


# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================

@router.websocket("/chat/{session_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None)
):
    """
    Endpoint WebSocket para chat con token streaming.

    FLOW:
    1. Autenticación JWT via query string
    2. Conexión y registro en SessionManager
    3. Loop bidireccional:
       - Recibir: Mensajes usuario + señales abort
       - Enviar: Token chunks + eventos control
    4. Desconexión y cleanup

    FRAMES CLIENTE → SERVIDOR:
    ```json
    {"type": "user_message", "content": "...", "message_id": "..."}
    {"type": "abort"}
    ```

    FRAMES SERVIDOR → CLIENTE:
    ```json
    {"type": "token_chunk", "delta": "...", "message_id": "..."}
    {"type": "generation_completed", "message_id": "..."}
    {"type": "generation_interrupted", "message_id": "..."}
    {"type": "error", "message": "..."}
    {"type": "history", "messages": [...]}
    ```

    Args:
        session_id: ID de sesión de chat (thread_id de LangGraph)
        token: JWT en query string
    """
    # Generar connection_id único
    connection_id = f"{session_id}_{uuid.uuid4().hex[:8]}"

    try:
        # 1. AUTENTICACIÓN
        try:
            user_id = await verify_jwt_from_query(token)
            logger.info(f"[WS] Usuario {user_id} autenticado para sesión {session_id}")
        except HTTPException as e:
            await websocket.close(code=1008, reason=str(e.detail))
            return

        # 2. CONECTAR
        await session_manager.connect(websocket, session_id, connection_id)

        # 3. REHIDRATACIÓN: Enviar historial al conectar
        try:
            history = await load_chat_history(session_id)
            await session_manager.send_to_connection(
                connection_id,
                {
                    "type": "history",
                    "messages": history,
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"[WS] Error cargando historial: {e}")

        # 4. LOOP BIDIRECCIONAL
        # Tarea 1: Consumir eventos de la queue (servidor → cliente)
        consumer_task = asyncio.create_task(
            consume_events(connection_id, websocket)
        )

        # Tarea 2: Recibir mensajes del cliente (cliente → servidor)
        producer_task = asyncio.create_task(
            receive_messages(websocket, session_id, connection_id)
        )

        # Esperar a que alguna termine (desconexión o error)
        done, pending = await asyncio.wait(
            {consumer_task, producer_task},
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancelar tarea pendiente
        for task in pending:
            task.cancel()

    except WebSocketDisconnect:
        logger.info(f"[WS] Cliente desconectado (normal): {connection_id}")

    except Exception as e:
        logger.error(f"[WS] Error en conexión {connection_id}: {e}")

    finally:
        # 5. CLEANUP
        await session_manager.disconnect(connection_id, session_id)


# ============================================================
# CONSUMER: Queue → WebSocket
# ============================================================

async def consume_events(connection_id: str, websocket: WebSocket):
    """
    Consume eventos de la queue y los envía al WebSocket.

    Patrón: Pub/Sub consumidor
    """
    queue = session_manager.queues.get(connection_id)
    if not queue:
        return

    try:
        while True:
            # Esperar evento de la queue
            event = await queue.get()

            # Enviar al WebSocket
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(event)
            else:
                break

    except asyncio.CancelledError:
        logger.info(f"[WS] Consumer cancelado: {connection_id}")
    except Exception as e:
        logger.error(f"[WS] Error en consumer {connection_id}: {e}")


# ============================================================
# PRODUCER: WebSocket → Procesamiento
# ============================================================

async def receive_messages(
    websocket: WebSocket,
    session_id: str,
    connection_id: str
):
    """
    Recibe mensajes del cliente y los procesa.

    TIPOS DE MENSAJE:
    - user_message: Prompt del usuario
    - abort: Cancelar generación actual
    """
    try:
        while True:
            # Recibir frame JSON
            data = await websocket.receive_json()

            message_type = data.get("type")

            if message_type == "user_message":
                # Mensaje del usuario
                content = data.get("content", "").strip()
                if not content:
                    continue

                logger.info(
                    f"[WS] Mensaje recibido en sesión {session_id}: "
                    f"{content[:50]}..."
                )

                # ABORT AUTOMÁTICO: Si hay generación activa, abortarla
                interrupted_msg_id = await session_manager.abort_generation(session_id)
                if interrupted_msg_id:
                    # Notificar interrupción
                    await session_manager.broadcast_to_session(
                        session_id,
                        {
                            "type": "generation_interrupted",
                            "message_id": interrupted_msg_id,
                            "reason": "new_user_message",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )

                    # Guardar mensaje parcial como interrupted
                    await save_partial_message(
                        session_id,
                        interrupted_msg_id,
                        status="interrupted"
                    )

                # Procesar nuevo mensaje
                await process_user_message(session_id, content, connection_id)

            elif message_type == "abort":
                # Señal explícita de abort
                logger.info(f"[WS] Abort recibido para sesión {session_id}")

                interrupted_msg_id = await session_manager.abort_generation(session_id)
                if interrupted_msg_id:
                    await session_manager.broadcast_to_session(
                        session_id,
                        {
                            "type": "generation_interrupted",
                            "message_id": interrupted_msg_id,
                            "reason": "user_abort",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )

                    await save_partial_message(
                        session_id,
                        interrupted_msg_id,
                        status="interrupted"
                    )

            else:
                logger.warning(f"[WS] Tipo de mensaje desconocido: {message_type}")

    except WebSocketDisconnect:
        logger.info(f"[WS] WebSocket desconectado: {connection_id}")
    except asyncio.CancelledError:
        logger.info(f"[WS] Receiver cancelado: {connection_id}")
    except Exception as e:
        logger.error(f"[WS] Error en receiver {connection_id}: {e}")


# ============================================================
# AGENT PROCESSING - TOKEN STREAMING
# ============================================================

async def process_user_message(
    session_id: str,
    content: str,
    connection_id: str
):
    """
    Procesa mensaje del usuario y streamea respuesta del agente.

    FLOW:
    1. Guardar mensaje usuario en BD
    2. Invocar agente con streaming
    3. Streamear tokens vía broadcast
    4. Guardar respuesta completa

    CRÍTICO:
    - Usar asyncio.Task para permitir cancelación
    - Broadcast a TODOS los observadores de la sesión
    """
    # Generar IDs
    user_message_id = f"msg_{uuid.uuid4().hex[:12]}"
    assistant_message_id = f"msg_{uuid.uuid4().hex[:12]}"

    try:
        # 1. Guardar mensaje usuario
        await save_message(
            session_id=session_id,
            message_id=user_message_id,
            role="user",
            content=content,
            status="completed"
        )

        # 2. Crear tarea de generación
        generation_task = asyncio.create_task(
            stream_agent_response(
                session_id,
                content,
                assistant_message_id
            )
        )

        # Registrar tarea activa
        session_manager.set_active_generation(
            session_id,
            generation_task,
            assistant_message_id
        )

        # 3. Esperar a que termine (o se cancele)
        await generation_task

    except asyncio.CancelledError:
        logger.info(f"[WS] Generación cancelada para sesión {session_id}")
        # Ya se manejó en abort_generation

    except Exception as e:
        logger.error(f"[WS] Error procesando mensaje: {e}")

        # Enviar error a sesión
        await session_manager.broadcast_to_session(
            session_id,
            {
                "type": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


async def stream_agent_response(
    session_id: str,
    user_input: str,
    message_id: str
):
    """
    Streamea respuesta del agente token por token.

    IMPLEMENTACIÓN CON LANGGRAPH:
    ```python
    graph = get_agent_graph()

    config = {"configurable": {"thread_id": session_id}}

    async for event in graph.astream_events(
        {"messages": [{"role": "user", "content": user_input}]},
        config=config,
        version="v2"
    ):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            delta = chunk.content

            await session_manager.broadcast_to_session(
                session_id,
                {
                    "type": "token_chunk",
                    "delta": delta,
                    "message_id": message_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    ```

    MOCK para testing sin LangGraph:
    """
    # Mock: Simular streaming de respuesta
    mock_response = (
        "Hola, soy el asistente de Brasaland. "
        "¿En qué puedo ayudarte con la gestión de los 14 restaurantes? "
        "Puedo ayudarte con incidencias, candidatos, operaciones y más."
    )

    accumulated_content = ""

    try:
        # Simular streaming token por token
        for word in mock_response.split():
            # Check point de cancelación
            await asyncio.sleep(0.05)  # Simular latencia LLM

            delta = word + " "
            accumulated_content += delta

            # Broadcast token chunk
            await session_manager.broadcast_to_session(
                session_id,
                {
                    "type": "token_chunk",
                    "delta": delta,
                    "message_id": message_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        # Generación completada
        await session_manager.broadcast_to_session(
            session_id,
            {
                "type": "generation_completed",
                "message_id": message_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

        # Guardar mensaje completo
        await save_message(
            session_id=session_id,
            message_id=message_id,
            role="assistant",
            content=accumulated_content.strip(),
            status="completed"
        )

    except asyncio.CancelledError:
        # Abort: Guardar contenido parcial
        logger.info(f"[WS] Streaming cancelado, guardando parcial: {accumulated_content[:50]}...")

        await save_message(
            session_id=session_id,
            message_id=message_id,
            role="assistant",
            content=accumulated_content.strip(),
            status="interrupted"
        )

        raise  # Re-raise para limpiar en caller


# ============================================================
# DATABASE HELPERS (Placeholders)
# ============================================================

async def load_chat_history(session_id: str) -> list:
    """
    Carga historial de chat desde BD.

    Returns:
        Lista de mensajes con estructura:
        [
            {
                "message_id": "msg_xxx",
                "role": "user" | "assistant",
                "content": "...",
                "status": "completed" | "interrupted",
                "created_at": "2026-10-31T12:00:00Z"
            }
        ]
    """
    # TODO: Implementar query a BD real
    # return await db.query(ChatMessage).filter_by(session_id=session_id).all()

    # Mock
    return []


async def save_message(
    session_id: str,
    message_id: str,
    role: str,
    content: str,
    status: str
):
    """Guarda mensaje en BD."""
    # TODO: Implementar insert a BD real
    logger.info(
        f"[DB] Guardando mensaje {message_id} ({role}, {status}): "
        f"{content[:50]}..."
    )


async def save_partial_message(
    session_id: str,
    message_id: str,
    status: str
):
    """Actualiza status de mensaje a interrupted."""
    # TODO: Implementar update a BD real
    logger.info(f"[DB] Marcando mensaje {message_id} como {status}")


# ============================================================
# HEALTH CHECK
# ============================================================

@router.get("/health")
async def websocket_health():
    """Health check del sistema WebSocket."""
    return {
        "status": "healthy",
        "active_sessions": len(session_manager.sessions),
        "total_connections": len(session_manager.connections),
        "active_generations": len(session_manager.active_generations),
        "timestamp": datetime.utcnow().isoformat()
    }
