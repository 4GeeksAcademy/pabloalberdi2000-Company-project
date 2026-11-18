"""
FastAPI Router - SSE Notifications

Endpoint de Server-Sent Events para notificaciones en tiempo real.

CRÍTICO:
- Protocolo SSE estructurado (event: rfp_ticket_created)
- Headers correctos (text/event-stream, no-cache, keep-alive)
- Autenticación JWT obligatoria
- Heartbeat keep-alive cada 30s
- Reconexión resiliente del cliente
"""

import asyncio
import json
import logging
from typing import Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, Header, Request, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from services.notifications import connection_manager, RFPTicketEvent

# CRÍTICO: Importar dependencia JWT del sistema de autenticación existente
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from app.auth.dependencies import get_current_active_user

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ============================================================
# DEPENDENCY: JWT AUTHENTICATION (Reutilización del sistema existente)
# ============================================================
# La autenticación JWT se delega a get_current_active_user de app.auth.dependencies
# Esta dependency verifica el token, valida expiración y retorna el usuario activo


# ============================================================
# SSE ENDPOINT
# ============================================================

@router.get("/sse")
async def sse_stream(
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Endpoint de Server-Sent Events para notificaciones en tiempo real.

    **Autenticación**: Requiere header `Authorization: Bearer <jwt_token>`
    - Validación JWT delegada a `get_current_active_user` (sistema de auth existente)
    - Solo usuarios activos pueden suscribirse

    **Protocolo SSE**:
    ```
    event: rfp_ticket_created
    data: {"ticket_id": 123, "status": "analizando", "filename": "...", ...}

    : keep-alive

    ```

    **Eventos emitidos**:
    - `connected`: Confirmación de conexión establecida
    - `rfp_ticket_created`: Nuevo ticket RFP registrado en BD
    - `: keep-alive`: Heartbeat cada 30s (comentario SSE)

    **Reconexión**: Cliente debe implementar backoff exponencial (hook ya implementado)

    **Headers**:
    - Content-Type: text/event-stream
    - Cache-Control: no-cache
    - Connection: keep-alive
    - X-Accel-Buffering: no (para proxies NGINX)

    **Recuperación**:
    - El cliente debe refetch `/rfp/tickets` al reconectar para sincronizar estado
    - SSE solo envía eventos NUEVOS posteriores a la conexión
    - No se implementa replay de eventos perdidos (patrón refetch + SSE)
    """
    # Extraer user_id del usuario autenticado
    user_id = current_user.get("doc_id") or current_user.get("id") or "unknown"
    user_email = current_user.get("email", "unknown@example.com")

    # Generar connection_id único
    connection_id = f"{user_id}_{uuid.uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"

    logger.info(f"[SSE] Iniciando stream para usuario {user_email} (conn: {connection_id})")

    # Generador asíncrono de eventos
    async def event_generator():
        """
        Generador asíncrono que produce eventos SSE.

        Yields:
            str: Fragmentos SSE formateados
        """
        # Registrar conexión
        queue = await connection_manager.connect(connection_id)

        try:
            # Enviar evento inicial de conexión
            yield format_sse_event(
                event_type="connected",
                data={
                    "connection_id": connection_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": "SSE stream established"
                },
                event_id=f"init_{int(datetime.utcnow().timestamp())}"
            )

            # Loop infinito de eventos
            heartbeat_interval = 30  # segundos
            last_heartbeat = asyncio.get_event_loop().time()

            while True:
                # Check si cliente desconectó
                if await request.is_disconnected():
                    logger.info(f"[SSE] Cliente {connection_id} desconectado")
                    break

                try:
                    # Esperar evento con timeout para heartbeat
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=heartbeat_interval
                    )

                    # Enviar evento real
                    yield format_sse_event(
                        event_type=event.event_type,
                        data=event.to_dict(),
                        event_id=f"{event.event_type}_{event.ticket_id}_{int(datetime.utcnow().timestamp())}"
                    )

                    last_heartbeat = asyncio.get_event_loop().time()

                except asyncio.TimeoutError:
                    # Timeout → Enviar heartbeat keep-alive
                    current_time = asyncio.get_event_loop().time()

                    if current_time - last_heartbeat >= heartbeat_interval:
                        yield format_sse_keepalive()
                        last_heartbeat = current_time

        except asyncio.CancelledError:
            logger.info(f"[SSE] Stream cancelado para {connection_id}")
        except Exception as e:
            logger.error(f"[SSE] Error en stream {connection_id}: {e}")
        finally:
            # Desregistrar conexión
            await connection_manager.disconnect(connection_id)
            logger.info(f"[SSE] Stream finalizado para {connection_id}")

    # Retornar StreamingResponse con headers SSE
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Para NGINX
            "Access-Control-Allow-Origin": "*",  # CORS (ajustar en producción)
        }
    )


# ============================================================
# SSE FORMATTING HELPERS
# ============================================================

def format_sse_event(
    event_type: str,
    data: dict,
    event_id: Optional[str] = None
) -> str:
    """
    Formatea evento SSE según protocolo.

    Args:
        event_type: Tipo de evento (ej: "rfp_ticket_created")
        data: Payload JSON
        event_id: ID opcional del evento (para Last-Event-ID)

    Returns:
        Fragmento SSE formateado

    Formato:
        id: <event_id>
        event: <event_type>
        data: <json>

        (doble newline al final)
    """
    lines = []

    # ID (opcional)
    if event_id:
        lines.append(f"id: {event_id}")

    # Event type
    lines.append(f"event: {event_type}")

    # Data (JSON serializado)
    json_data = json.dumps(data, ensure_ascii=False)
    lines.append(f"data: {json_data}")

    # Doble newline al final
    lines.append("")
    lines.append("")

    return "\n".join(lines)


def format_sse_keepalive() -> str:
    """
    Formatea comentario keep-alive SSE.

    Returns:
        Comentario SSE (": keep-alive\\n\\n")
    """
    # Comentario SSE (línea que empieza con ":")
    return f": keep-alive {datetime.utcnow().isoformat()}\n\n"


# ============================================================
# HEALTH CHECK
# ============================================================

@router.get("/health")
async def notifications_health():
    """
    Health check del sistema de notificaciones.

    Returns:
        {
            "status": "healthy",
            "active_connections": 5,
            "timestamp": "2026-10-31T12:00:00Z"
        }
    """
    return {
        "status": "healthy",
        "active_connections": connection_manager.get_active_connections_count(),
        "timestamp": datetime.utcnow().isoformat()
    }
