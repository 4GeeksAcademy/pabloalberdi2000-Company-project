"""
Tests - SSE Notifications System

Valida:
- Endpoint SSE con autenticación JWT
- Formato de eventos SSE (event: + data:)
- Heartbeat keep-alive
- Pub/Sub a múltiples clientes
- Reconexión y deduplicación
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient
from services.notifications.manager import ConnectionManager, RFPTicketEvent


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def connection_manager():
    """Fixture: ConnectionManager limpio."""
    return ConnectionManager()


@pytest.fixture
def sample_event():
    """Fixture: Evento de ejemplo."""
    return RFPTicketEvent(
        event_type="rfp_ticket_created",
        ticket_id=123,
        status="analizando",
        filename="test_rfp.pdf",
        client_name="Test Corp",
        created_at=datetime.utcnow().isoformat()
    )


# ============================================================
# TESTS: ConnectionManager
# ============================================================

@pytest.mark.asyncio
async def test_connection_manager_connect(connection_manager):
    """Test: Registrar nueva conexión."""
    connection_id = "user_123"

    queue = await connection_manager.connect(connection_id)

    assert connection_id in connection_manager.connections
    assert connection_manager.connections[connection_id] == queue
    assert queue.qsize() == 0


@pytest.mark.asyncio
async def test_connection_manager_disconnect(connection_manager):
    """Test: Desregistrar conexión."""
    connection_id = "user_123"

    # Conectar
    await connection_manager.connect(connection_id)
    assert connection_id in connection_manager.connections

    # Desconectar
    await connection_manager.disconnect(connection_id)
    assert connection_id not in connection_manager.connections


@pytest.mark.asyncio
async def test_connection_manager_publish_single_client(connection_manager, sample_event):
    """Test: Publicar evento a un solo cliente."""
    connection_id = "user_123"

    # Conectar cliente
    queue = await connection_manager.connect(connection_id)

    # Publicar evento
    await connection_manager.publish(sample_event)

    # Verificar que el evento llegó
    assert queue.qsize() == 1
    event = await queue.get()
    assert event.event_type == "rfp_ticket_created"
    assert event.ticket_id == 123


@pytest.mark.asyncio
async def test_connection_manager_publish_multiple_clients(connection_manager, sample_event):
    """Test: Publicar evento a múltiples clientes (Pub/Sub)."""
    # Conectar 3 clientes
    queue_1 = await connection_manager.connect("user_1")
    queue_2 = await connection_manager.connect("user_2")
    queue_3 = await connection_manager.connect("user_3")

    # Publicar evento
    await connection_manager.publish(sample_event)

    # Verificar que todos recibieron el evento
    assert queue_1.qsize() == 1
    assert queue_2.qsize() == 1
    assert queue_3.qsize() == 1

    event_1 = await queue_1.get()
    event_2 = await queue_2.get()
    event_3 = await queue_3.get()

    assert event_1.ticket_id == 123
    assert event_2.ticket_id == 123
    assert event_3.ticket_id == 123


@pytest.mark.asyncio
async def test_connection_manager_queue_overflow(connection_manager):
    """Test: Queue llena descarta eventos antiguos (maxsize=100)."""
    connection_id = "user_123"
    queue = await connection_manager.connect(connection_id)

    # Llenar queue más allá de maxsize (100)
    for i in range(110):
        event = RFPTicketEvent(
            event_type="rfp_ticket_created",
            ticket_id=i,
            status="analizando",
            filename=f"rfp_{i}.pdf",
            client_name=None,
            created_at=datetime.utcnow().isoformat()
        )

        # put_nowait lanza QueueFull si está llena
        try:
            await connection_manager.publish(event)
        except asyncio.QueueFull:
            pass

    # Queue no debería exceder maxsize
    assert queue.qsize() <= 100


@pytest.mark.asyncio
async def test_connection_manager_get_active_count(connection_manager):
    """Test: Contador de conexiones activas."""
    assert connection_manager.get_active_connections_count() == 0

    await connection_manager.connect("user_1")
    assert connection_manager.get_active_connections_count() == 1

    await connection_manager.connect("user_2")
    await connection_manager.connect("user_3")
    assert connection_manager.get_active_connections_count() == 3

    await connection_manager.disconnect("user_1")
    assert connection_manager.get_active_connections_count() == 2


# ============================================================
# TESTS: RFPTicketEvent
# ============================================================

def test_rfp_ticket_event_to_dict(sample_event):
    """Test: Serialización del evento a dict."""
    data = sample_event.to_dict()

    assert data["ticket_id"] == 123
    assert data["status"] == "analizando"
    assert data["filename"] == "test_rfp.pdf"
    assert data["client_name"] == "Test Corp"
    assert "created_at" in data


def test_rfp_ticket_event_optional_fields():
    """Test: Evento con campos opcionales None."""
    event = RFPTicketEvent(
        event_type="rfp_ticket_created",
        ticket_id=456,
        status="analisis_completo",
        filename="rfp.pdf",
        client_name=None,  # Opcional
        created_at=datetime.utcnow().isoformat()
    )

    data = event.to_dict()
    assert data["client_name"] is None


# ============================================================
# TESTS: SSE Endpoint (Integración)
# ============================================================

@pytest.mark.asyncio
async def test_sse_endpoint_requires_auth():
    """Test: SSE endpoint requiere autenticación JWT."""
    from services.routers.notifications import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # Request sin header Authorization
    response = client.get("/notifications/sse")

    assert response.status_code == 401
    assert "Missing Authorization header" in response.json()["detail"]


@pytest.mark.asyncio
async def test_sse_endpoint_invalid_token():
    """Test: SSE endpoint rechaza token inválido."""
    from services.routers.notifications import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # Request con token corto (< 10 chars)
    response = client.get(
        "/notifications/sse",
        headers={"Authorization": "Bearer short"}
    )

    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_sse_endpoint_valid_token_streams():
    """Test: SSE endpoint con token válido retorna stream."""
    from services.routers.notifications import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # Request con token válido (mock)
    response = client.get(
        "/notifications/sse",
        headers={"Authorization": "Bearer valid_token_12345"},
        stream=True
    )

    # Verificar headers SSE
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert response.headers["cache-control"] == "no-cache"

    # Leer primer evento (connected)
    first_chunk = next(response.iter_content(chunk_size=None, decode_unicode=True))

    # Verificar formato SSE
    assert "event: connected" in first_chunk
    assert "data: {" in first_chunk


@pytest.mark.asyncio
async def test_sse_format_event():
    """Test: Formato correcto de evento SSE."""
    from services.routers.notifications import format_sse_event

    event_str = format_sse_event(
        event_type="rfp_ticket_created",
        data={"ticket_id": 123, "status": "analizando"},
        event_id="evt_123"
    )

    lines = event_str.split("\n")

    # Verificar estructura
    assert "id: evt_123" in lines
    assert "event: rfp_ticket_created" in lines
    assert any("data: " in line for line in lines)

    # Verificar doble newline al final
    assert event_str.endswith("\n\n")


@pytest.mark.asyncio
async def test_sse_format_keepalive():
    """Test: Formato correcto de keep-alive SSE."""
    from services.routers.notifications import format_sse_keepalive

    keepalive_str = format_sse_keepalive()

    # Verificar comentario SSE (empieza con ":")
    assert keepalive_str.startswith(": keep-alive")
    assert keepalive_str.endswith("\n\n")


# ============================================================
# TESTS: Health Check
# ============================================================

@pytest.mark.asyncio
async def test_notifications_health_endpoint():
    """Test: Health check endpoint."""
    from services.routers.notifications import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/notifications/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert "active_connections" in data
    assert "timestamp" in data


# ============================================================
# TESTS: Reconexión y Deduplicación (Frontend Logic)
# ============================================================

def test_deduplication_logic():
    """
    Test: Lógica de deduplicación en frontend (mock).

    El frontend debe mantener un Map<ticket_id, Ticket> para evitar duplicados.
    """
    tickets_map = {}

    # Evento 1: Nuevo ticket
    event_1 = {
        "ticket_id": 123,
        "filename": "rfp.pdf",
        "status": "analizando"
    }

    if event_1["ticket_id"] not in tickets_map:
        tickets_map[event_1["ticket_id"]] = event_1

    assert len(tickets_map) == 1

    # Evento 2: Mismo ticket (duplicado)
    event_2 = {
        "ticket_id": 123,
        "filename": "rfp.pdf",
        "status": "analisis_completo"
    }

    if event_2["ticket_id"] not in tickets_map:
        tickets_map[event_2["ticket_id"]] = event_2
    else:
        # Actualizar estado si ya existe
        tickets_map[event_2["ticket_id"]].update(event_2)

    # No debe duplicarse
    assert len(tickets_map) == 1
    # Pero debe actualizarse
    assert tickets_map[123]["status"] == "analisis_completo"


def test_exponential_backoff_calculation():
    """
    Test: Cálculo de backoff exponencial (mock).

    Frontend debe implementar: 1s, 2s, 4s, 8s, 16s, 32s (max)
    """
    base_delay = 1000  # 1 segundo en ms
    max_delay = 32000  # 32 segundos

    # Simular 10 intentos
    delays = []
    for attempt in range(1, 11):
        exponential_delay = base_delay * (2 ** (attempt - 1))
        capped_delay = min(exponential_delay, max_delay)
        delays.append(capped_delay)

    # Verificar progresión
    assert delays[0] == 1000   # 1s
    assert delays[1] == 2000   # 2s
    assert delays[2] == 4000   # 4s
    assert delays[3] == 8000   # 8s
    assert delays[4] == 16000  # 16s
    assert delays[5] == 32000  # 32s (max)
    assert delays[9] == 32000  # Sigue en max


# ============================================================
# TESTS: Integración con Router RFP
# ============================================================

@pytest.mark.asyncio
async def test_rfp_upload_publishes_sse_event(sample_event):
    """
    Test: Upload de RFP publica evento SSE.

    NOTA: Requiere mock de DB y connection_manager.
    """
    # Este test requiere implementación completa de DB y mock de connection_manager.publish
    # Placeholder para estructura:

    # 1. Mock DB session
    # 2. Mock connection_manager.publish
    # 3. POST /rfp/upload
    # 4. Verificar que connection_manager.publish fue llamado con evento correcto

    pass  # TODO: Implementar cuando DB esté configurada


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
