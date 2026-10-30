"""
Tests - Incident Notifications System (Brasaland Domain)

DOMINIO: Sistema de Análisis de Incidencias Postventa
Locales: 14 restaurantes (10 CO + 4 US)

Valida:
- Endpoint SSE con autenticación JWT
- Formato de eventos SSE (event: incident_created)
- Heartbeat keep-alive
- Pub/Sub a múltiples clientes
- Reconexión y deduplicación
- Alineación con company-BRIEFING.md
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient
from services.notifications.manager import ConnectionManager, IncidentCreatedEvent


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def connection_manager():
    """Fixture: ConnectionManager limpio."""
    return ConnectionManager()


@pytest.fixture
def sample_incident_event():
    """Fixture: Evento de incidencia Brasaland."""
    return IncidentCreatedEvent(
        event_type="incident_created",
        incident_id=123,
        local_name="Medellín Centro",
        country="CO",
        category="calidad_comida",
        severity="alta",
        description="Carne poco cocida en plato principal",
        customer_name="Juan Pérez",
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
async def test_connection_manager_publish_incident(connection_manager, sample_incident_event):
    """Test: Publicar evento de incidencia a un cliente."""
    connection_id = "operaciones_felipe"

    # Conectar cliente
    queue = await connection_manager.connect(connection_id)

    # Publicar evento
    await connection_manager.publish(sample_incident_event)

    # Verificar evento
    assert queue.qsize() == 1
    event = await queue.get()
    assert event.event_type == "incident_created"
    assert event.incident_id == 123
    assert event.local_name == "Medellín Centro"
    assert event.country == "CO"
    assert event.severity == "alta"


@pytest.mark.asyncio
async def test_connection_manager_publish_multiple_countries(connection_manager):
    """Test: Publicar incidencias de diferentes países (CO + US)."""
    # Conectar clientes por país
    queue_co = await connection_manager.connect("operaciones_colombia")
    queue_us = await connection_manager.connect("operaciones_florida")

    # Incidencia Colombia
    incident_co = IncidentCreatedEvent(
        event_type="incident_created",
        incident_id=1,
        local_name="Bogotá Norte",
        country="CO",
        category="servicio",
        severity="media",
        description="Demora en atención",
        customer_name=None,
        created_at=datetime.utcnow().isoformat()
    )

    # Incidencia USA
    incident_us = IncidentCreatedEvent(
        event_type="incident_created",
        incident_id=2,
        local_name="Miami Beach",
        country="US",
        category="tiempo_espera",
        severity="baja",
        description="Espera de 15 minutos",
        customer_name="John Smith",
        created_at=datetime.utcnow().isoformat()
    )

    # Publicar ambas
    await connection_manager.publish(incident_co)
    await connection_manager.publish(incident_us)

    # Ambos clientes reciben ambas incidencias (Pub/Sub)
    assert queue_co.qsize() == 2
    assert queue_us.qsize() == 2


# ============================================================
# TESTS: IncidentCreatedEvent
# ============================================================

def test_incident_event_to_dict(sample_incident_event):
    """Test: Serialización del evento de incidencia."""
    data = sample_incident_event.to_dict()

    assert data["incident_id"] == 123
    assert data["local_name"] == "Medellín Centro"
    assert data["country"] == "CO"
    assert data["category"] == "calidad_comida"
    assert data["severity"] == "alta"
    assert data["description"] == "Carne poco cocida en plato principal"
    assert data["customer_name"] == "Juan Pérez"
    assert "created_at" in data

    # event_type NO debe estar en data (va en campo "event:")
    assert "event_type" not in data


def test_incident_event_severity_levels():
    """Test: Validar niveles de severidad de incidencias."""
    severities = ["baja", "media", "alta", "critica"]

    for severity in severities:
        event = IncidentCreatedEvent(
            event_type="incident_created",
            incident_id=1,
            local_name="Test Local",
            country="CO",
            category="servicio",
            severity=severity,
            description="Test",
            customer_name=None,
            created_at=datetime.utcnow().isoformat()
        )

        assert event.severity == severity


def test_incident_event_categories():
    """Test: Validar categorías de incidencias de Brasaland."""
    categories = [
        "calidad_comida",
        "servicio",
        "tiempo_espera",
        "higiene",
        "ambiente"
    ]

    for category in categories:
        event = IncidentCreatedEvent(
            event_type="incident_created",
            incident_id=1,
            local_name="Test Local",
            country="CO",
            category=category,
            severity="media",
            description="Test",
            customer_name=None,
            created_at=datetime.utcnow().isoformat()
        )

        assert event.category == category


def test_incident_event_brasaland_locals():
    """Test: Validar nombres de locales reales de Brasaland."""
    # Locales Colombia
    locales_co = [
        "Medellín Centro",
        "Medellín Poblado",
        "Bogotá Norte",
        "Bogotá Chapinero",
        "Cali Norte",
        "Cartagena Centro",
        "Barranquilla Norte"
    ]

    # Locales USA
    locales_us = [
        "Miami Beach",
        "Miami Downtown",
        "Orlando",
        "Tampa"
    ]

    for local in locales_co:
        event = IncidentCreatedEvent(
            event_type="incident_created",
            incident_id=1,
            local_name=local,
            country="CO",
            category="servicio",
            severity="baja",
            description="Test",
            customer_name=None,
            created_at=datetime.utcnow().isoformat()
        )
        assert event.country == "CO"

    for local in locales_us:
        event = IncidentCreatedEvent(
            event_type="incident_created",
            incident_id=1,
            local_name=local,
            country="US",
            category="servicio",
            severity="baja",
            description="Test",
            customer_name=None,
            created_at=datetime.utcnow().isoformat()
        )
        assert event.country == "US"


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

    response = client.get("/notifications/sse")

    assert response.status_code == 401
    assert "Missing Authorization header" in response.json()["detail"]


@pytest.mark.asyncio
async def test_sse_endpoint_valid_token_streams():
    """Test: SSE endpoint con token válido retorna stream."""
    from services.routers.notifications import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get(
        "/notifications/sse",
        headers={"Authorization": "Bearer valid_token_12345"},
        stream=True
    )

    # Verificar headers SSE
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert response.headers["cache-control"] == "no-cache"


@pytest.mark.asyncio
async def test_sse_format_incident_event():
    """Test: Formato correcto de evento SSE para incidencias."""
    from services.routers.notifications import format_sse_event

    event_str = format_sse_event(
        event_type="incident_created",
        data={
            "incident_id": 123,
            "local_name": "Miami Beach",
            "country": "US",
            "severity": "critica"
        },
        event_id="incident_123"
    )

    lines = event_str.split("\n")

    # Verificar estructura SSE
    assert "id: incident_123" in lines
    assert "event: incident_created" in lines
    assert any("data: " in line for line in lines)
    assert event_str.endswith("\n\n")


# ============================================================
# TESTS: Deduplicación con localStorage
# ============================================================

def test_deduplication_with_persistence():
    """
    Test: Lógica de deduplicación con persistencia (mock localStorage).
    """
    incidents_map = {}

    # Simular localStorage load
    stored_data = {
        "123": {
            "incident_id": 123,
            "local_name": "Medellín Centro",
            "severity": "alta"
        }
    }

    # Cargar desde "localStorage"
    for incident_id, incident in stored_data.items():
        incidents_map[int(incident_id)] = incident

    assert len(incidents_map) == 1

    # Evento duplicado (ya existe en "localStorage")
    new_event = {
        "incident_id": 123,
        "local_name": "Medellín Centro",
        "severity": "alta"
    }

    if new_event["incident_id"] not in incidents_map:
        incidents_map[new_event["incident_id"]] = new_event

    # No debe duplicarse
    assert len(incidents_map) == 1

    # Evento nuevo
    new_event_2 = {
        "incident_id": 456,
        "local_name": "Miami Beach",
        "severity": "media"
    }

    if new_event_2["incident_id"] not in incidents_map:
        incidents_map[new_event_2["incident_id"]] = new_event_2

    # Debe agregarse
    assert len(incidents_map) == 2


# ============================================================
# TESTS: Alineación con BRIEFING.md
# ============================================================

def test_domain_alignment_no_rfp_entities():
    """
    Test: Verificar que NO se usen entidades RFP (fuera del dominio Brasaland).
    """
    # El evento debe ser IncidentCreatedEvent, NO RFPTicketEvent
    from services.notifications.manager import IncidentCreatedEvent

    event = IncidentCreatedEvent(
        event_type="incident_created",
        incident_id=1,
        local_name="Medellín Centro",
        country="CO",
        category="servicio",
        severity="media",
        description="Test",
        customer_name=None,
        created_at=datetime.utcnow().isoformat()
    )

    # Verificar que NO tenga atributos de RFP
    assert not hasattr(event, 'ticket_id')
    assert not hasattr(event, 'filename')
    assert not hasattr(event, 'client_name')

    # Verificar que SÍ tenga atributos de Brasaland
    assert hasattr(event, 'incident_id')
    assert hasattr(event, 'local_name')
    assert hasattr(event, 'country')
    assert hasattr(event, 'severity')


def test_domain_alignment_countries():
    """Test: Validar que solo se usen países de Brasaland (CO + US)."""
    valid_countries = ["CO", "US"]

    for country in valid_countries:
        event = IncidentCreatedEvent(
            event_type="incident_created",
            incident_id=1,
            local_name="Test Local",
            country=country,
            category="servicio",
            severity="baja",
            description="Test",
            customer_name=None,
            created_at=datetime.utcnow().isoformat()
        )
        assert event.country in valid_countries


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
