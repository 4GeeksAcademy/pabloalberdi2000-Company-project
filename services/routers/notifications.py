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

from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from services.notifications import connection_manager, RFPTicketEvent

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ============================================================
# DEPENDENCY: JWT AUTHENTICATION
# ============================================================

async def verify_jwt_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Verifica token JWT desde header Authorization.

    Args:
        authorization: Header "Authorization: Bearer <token>"

    Returns:
        user_id extraído del token

    Raises:
        HTTPException 401 si token inválido
    """
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid Authorization header format")

    token = authorization.replace("Bearer ", "")

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

    # Mock: Aceptar cualquier token no vacío
    if len(token) < 10:
        raise HTTPException(401, "Invalid token")

    # Retornar mock user_id
    return "user_mock_id"


# ============================================================
# SSE ENDPOINT
# ============================================================

@router.get("/sse")
async def sse_stream(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Endpoint de Server-Sent Events para notificaciones en tiempo real.

    **Autenticación**: Requiere header `Authorization: Bearer <jwt_token>`

    **Protocolo SSE**:
    ```
    event: rfp_ticket_created
    data: {"ticket_id": 123, "status": "analizando", ...}

    event: keep-alive
    data: {"timestamp": "2026-10-31T12:00:00Z"}
    ```

    **Reconexión**: Cliente debe implementar backoff exponencial

    **Headers**:
    - Content-Type: text/event-stream
    - Cache-Control: no-cache
    - Connection: keep-alive
    - X-Accel-Buffering: no (para proxies NGINX)
    """
    # Verificar autenticación JWT
    try:
        user_id = await verify_jwt_token(authorization)
    except HTTPException as e:
        logger.warning(f"[SSE] Autenticación fallida: {e.detail}")
        raise

    # Generar connection_id único
    connection_id = f"{user_id}_{uuid.uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"

    logger.info(f"[SSE] Iniciando stream para {connection_id}")

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
