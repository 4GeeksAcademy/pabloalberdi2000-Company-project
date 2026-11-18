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
import os
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

async def verify_jwt_from_query(token: Optional[str]) -> dict:
    """
    Verifica token JWT desde query string.

    Args:
        token: JWT desde query param ?token=...

    Returns:
        dict con datos del usuario autenticado

    Raises:
        HTTPException 401 si token inválido
    """
    if not token:
        raise HTTPException(401, "Missing token in query string")

    # Importar sistema de autenticación existente
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from app.auth.jwt import verify_token
        from app.tinydb_database import get_user_by_id
    except ImportError as e:
        logger.error(f"[WS] Error importando auth: {e}")
        raise HTTPException(500, "Authentication system not available")

    # Verificar token JWT
    payload = verify_token(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")

    # Extraer user_id del payload
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(401, "Invalid token payload: missing user_id")

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(401, "Invalid token payload: malformed user_id")

    # Buscar usuario en BD
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(401, "User not found")

    # Verificar que usuario esté activo
    if not user.get("is_active", False):
        raise HTTPException(401, "User account is inactive")

    logger.info(f"[WS] Usuario autenticado: {user.get('email')} (ID: {user_id})")

    return user


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
# CONVERSATIONAL HELPERS
# ============================================================

def _make_conversational(rag_response: str, user_input: str) -> str:
    """
    Transforma la respuesta del RAG en algo más conversacional.

    Args:
        rag_response: Respuesta técnica del RAG
        user_input: Pregunta original del usuario (en minúsculas)

    Returns:
        Respuesta más amigable y conversacional
    """
    # Detectar el tipo de pregunta
    is_question_about_count = any(word in user_input for word in ["cuántos", "cuantos", "cantidad", "número", "numero"])
    is_question_about_what = any(word in user_input for word in ["qué", "que", "cuál", "cual", "cuales", "cuáles"])
    is_question_about_who = any(word in user_input for word in ["quién", "quien", "quienes", "quiénes"])
    is_question_about_how = any(word in user_input for word in ["cómo", "como"])

    # Prefijos conversacionales según el tipo de pregunta
    prefixes = [
        "¡Claro! Te cuento:",
        "Con gusto te ayudo con eso.",
        "Perfecto, aquí está la información:",
        "Déjame compartirte eso:",
    ]

    # Si es una pregunta sobre cantidad, agregar intro más específico
    if is_question_about_count:
        intro = "Déjame darte los números exactos:\n\n"
    elif is_question_about_who:
        intro = "Te cuento sobre el equipo:\n\n"
    elif is_question_about_what:
        intro = "¡Buena pregunta! Aquí está la información:\n\n"
    elif is_question_about_how:
        intro = "Te explico:\n\n"
    else:
        intro = "Aquí está lo que encontré:\n\n"

    # Si la respuesta del RAG ya es conversacional (empieza con mayúscula y es larga), no modificar mucho
    if len(rag_response) > 200 and not rag_response.startswith("**"):
        response = intro + rag_response
    else:
        response = intro + rag_response

    # Agregar cierre conversacional si la respuesta es muy técnica
    if "**" in rag_response and len(rag_response) > 100:
        response += "\n\n¿Necesitas que profundice en algo específico? 😊"

    return response


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
    Streamea respuesta del agente token por token usando LangGraph.

    ARQUITECTURA:
    - Invoca build_agent_graph() del agente existente
    - Usa astream_events() para streaming de tokens
    - NO modifica el agente, solo cambia la capa de transporte
    - Broadcast a todos los observadores de la sesión (Pub/Sub)

    ABORT GENUINO:
    - Si asyncio.Task se cancela → raise asyncio.CancelledError
    - El stream se detiene inmediatamente
    - Mensaje parcial se guarda con status="interrupted"
    """
    # Flag para controlar modo de ejecución
    USE_REAL_AGENT = os.getenv("USE_REAL_LANGGRAPH_AGENT", "false").lower() == "true"

    if USE_REAL_AGENT:
        # ============================================================
        # MODO REAL: LangGraph Agent Streaming
        # ============================================================
        try:
            from services.agent.graph import build_agent_graph

            logger.info(f"[WS] Invocando agente LangGraph para sesión {session_id}")

            graph = build_agent_graph()
            config = {"configurable": {"thread_id": session_id}}

            accumulated_content = ""

            async for event in graph.astream_events(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
                version="v2"
            ):
                # Token streaming del modelo
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    delta = chunk.content if hasattr(chunk, 'content') else str(chunk)

                    if delta:
                        accumulated_content += delta

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
                    "total_tokens": len(accumulated_content.split()),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            # Guardar mensaje completo
            await save_message(
                session_id=session_id,
                message_id=message_id,
                role="assistant",
                content=accumulated_content,
                status="completed"
            )

            logger.info(f"[WS] Agente LangGraph completó respuesta ({len(accumulated_content)} caracteres)")

        except asyncio.CancelledError:
            # ABORT GENUINO: Stream cancelado por usuario
            logger.info(f"[WS] Stream LangGraph abortado para mensaje {message_id}")
            raise

        except Exception as e:
            logger.error(f"[WS] Error en streaming LangGraph: {e}")
            await session_manager.broadcast_to_session(
                session_id,
                {
                    "type": "error",
                    "message": f"Error del agente: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            raise

    else:
        # ============================================================
        # MODO MOCK: RAG + Streaming Simulado (para desarrollo/testing)
        # ============================================================
        logger.info(f"[WS] Modo MOCK activo (USE_REAL_LANGGRAPH_AGENT=false)")
        await _stream_mock_response(session_id, user_input, message_id)


async def _stream_mock_response(
    session_id: str,
    user_input: str,
    message_id: str
):
    """
    MODO MOCK: Streaming simulado con RAG para desarrollo/testing.

    Se activa cuando USE_REAL_LANGGRAPH_AGENT != true
    Útil para desarrollo frontend sin dependencia del agente real.
    """
    # MOCK: Procesar entrada del usuario de forma conversacional
    user_input_lower = user_input.lower().strip()

    # Detectar saludos
    greetings = ["hola", "buenos días", "buenas tardes", "buenas noches", "hey", "hi", "hello", "qué tal", "como estas"]
    is_greeting = any(greeting in user_input_lower for greeting in greetings)

    # Detectar despedidas
    farewells = ["adiós", "adios", "chao", "hasta luego", "nos vemos", "bye", "hasta pronto"]
    is_farewell = any(farewell in user_input_lower for farewell in farewells)

    # Integración con RAG: Usar el sistema de conocimiento existente
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from rag_mock import query as rag_query

        # Respuesta personalizada según el contexto
        if is_greeting and len(user_input_lower.split()) <= 5:
            # Saludo simple
            mock_response = (
                "¡Hola! 👋 Soy tu asistente virtual de Brasaland.\n\n"
                "Estoy aquí para ayudarte con información sobre nuestros 14 restaurantes en Colombia y Florida. "
                "Puedo contarte sobre:\n\n"
                "• **Candidatos y reclutamiento** - Tenemos 30 candidatos activos\n"
                "• **Inventario** - 11 ingredientes gestionados en tiempo real\n"
                "• **Operaciones** - Información de nuestros locales\n"
                "• **Sistemas técnicos** - ATS, incidencias, inventario\n"
                "• **El equipo** - CEO, CTO, directores de área\n\n"
                "¿En qué te puedo ayudar hoy? 😊"
            )
        elif is_farewell:
            # Despedida
            mock_response = (
                "¡Hasta pronto! 👋\n\n"
                "Fue un placer ayudarte. Si necesitas algo más sobre Brasaland, "
                "aquí estaré. ¡Que tengas un excelente día! 😊"
            )
        else:
            # Consultar RAG con la pregunta del usuario
            logger.info(f"[RAG] Consultando: {user_input}")
            rag_response = rag_query(user_input)

            # Hacer la respuesta más conversacional
            mock_response = _make_conversational(rag_response, user_input_lower)

            logger.info(f"[RAG] Respuesta obtenida: {len(mock_response)} caracteres")

    except Exception as e:
        logger.error(f"[RAG] Error consultando RAG: {e}")
        # Fallback a respuesta genérica
        mock_response = (
            "Hola, soy el asistente de Brasaland. "
            "¿En qué puedo ayudarte con la gestión de los 14 restaurantes? "
            "Puedo ayudarte con incidencias, candidatos, operaciones y más."
        )

    accumulated_content = ""

    try:
        # Simular streaming token por token con velocidad variable
        words = mock_response.split()
        for i, word in enumerate(words):
            # Check point de cancelación
            # Velocidad más rápida para palabras cortas, más lenta para puntuación
            if word.endswith(('.', '!', '?', ':')):
                await asyncio.sleep(0.08)  # Pausa en puntuación
            elif word.endswith(','):
                await asyncio.sleep(0.05)  # Pausa en comas
            else:
                await asyncio.sleep(0.02)  # Rápido para palabras normales

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
    # Importar funciones de TinyDB
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from app.tinydb_database import get_chat_history

    # Cargar historial real desde TinyDB
    messages = get_chat_history(session_id)

    logger.info(f"[DB] Cargado historial de sesión {session_id}: {len(messages)} mensajes")

    return messages


async def save_message(
    session_id: str,
    message_id: str,
    role: str,
    content: str,
    status: str
):
    """Guarda mensaje en BD."""
    # Importar funciones de TinyDB
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from app.tinydb_database import save_chat_message

    # Guardar mensaje real en TinyDB
    saved_message = save_chat_message(
        session_id=session_id,
        message_id=message_id,
        role=role,
        content=content,
        status=status
    )

    logger.info(
        f"[DB] Mensaje guardado: {message_id} ({role}, {status}) - "
        f"{len(content)} caracteres"
    )


async def save_partial_message(
    session_id: str,
    message_id: str,
    status: str
):
    """Actualiza status de mensaje a interrupted."""
    # Importar funciones de TinyDB
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from app.tinydb_database import update_chat_message_status

    # Actualizar status en TinyDB
    updated_message = update_chat_message_status(message_id, status)

    if updated_message:
        logger.info(f"[DB] Mensaje {message_id} marcado como {status}")
    else:
        logger.warning(f"[DB] No se encontró mensaje {message_id} para actualizar")


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
