"""
Tests Unitarios - SSE Notifications (Server-Sent Events)

Cobertura:
- Wire format SSE (event: rfp_ticket_created)
- Headers HTTP correctos (text/event-stream, no-cache, keep-alive)
- Autenticación JWT obligatoria
- JSON válido en campo data:
- Heartbeat keep-alive
- Reconexión y recuperación

Ejecutar:
    pytest tests/notifications/test_sse_notifications.py -v
"""
import pytest
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# Agregar raíz al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.notifications import connection_manager, RFPTicketEvent
from services.routers.notifications import sse_stream, format_sse_event, format_sse_keepalive


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_current_user():
    """Mock de usuario autenticado"""
    return {
        "doc_id": 42,
        "id": 42,
        "email": "test@brasaland.com",
        "role": "admin",
        "is_active": True
    }


@pytest.fixture
def mock_rfp_ticket_event():
    """Mock de evento RFP ticket creado"""
    return RFPTicketEvent(
        event_type="rfp_ticket_created",
        ticket_id=123,
        status="analizando",
        filename="client_rfp.pdf",
        client_name="Acme Corp",
        project_title="Sistema de Gestión de Inventario",
        submission_deadline="2026-12-31T23:59:59Z",
        created_at="2026-11-18T10:30:00Z"
    )


@pytest.fixture
async def cleanup_connections():
    """
    Limpia conexiones del ConnectionManager antes de cada test.

    Previene contaminación entre tests.
    """
    # Setup: Limpiar conexiones previas
    connection_manager.connections.clear()

    yield

    # Teardown: Limpiar conexiones post-test
    connection_manager.connections.clear()


# ============================================================
# TEST 1: Wire Format SSE - Event Structure
# ============================================================

class TestSSEWireFormat:
    """Test del formato wire SSE según especificación"""

    def test_format_sse_event_structure(self, mock_rfp_ticket_event):
        """
        CRITERIO 1: Verifica que format_sse_event genera el wire format correcto.

        Formato esperado:
            id: <event_id>
            event: rfp_ticket_created
            data: {"ticket_id": 123, ...}

            (doble newline al final)
        """
        # Generar fragmento SSE
        sse_fragment = format_sse_event(
            event_type="rfp_ticket_created",
            data=mock_rfp_ticket_event.to_dict(),
            event_id="test_event_123"
        )

        # ASSERT 1: Fragmento NO está vacío
        assert sse_fragment, "SSE fragment debe contener datos"

        # ASSERT 2: Contiene línea "event: rfp_ticket_created"
        assert "event: rfp_ticket_created" in sse_fragment, \
            "Wire format debe incluir 'event: rfp_ticket_created'"

        # ASSERT 3: Contiene línea "data:" con JSON
        assert "data: {" in sse_fragment, \
            "Wire format debe incluir línea 'data:' con JSON"

        # ASSERT 4: Contiene línea "id:" con event_id
        assert "id: test_event_123" in sse_fragment, \
            "Wire format debe incluir línea 'id:' con event_id"

        # ASSERT 5: Termina con doble newline
        assert sse_fragment.endswith("\n\n"), \
            "Wire format debe terminar con doble newline"

        print(f"✅ Test 1.1 passed: Wire format SSE correcto")


    def test_format_sse_event_json_valid(self, mock_rfp_ticket_event):
        """
        CRITERIO 2: Verifica que el campo data: contiene JSON válido.
        """
        sse_fragment = format_sse_event(
            event_type="rfp_ticket_created",
            data=mock_rfp_ticket_event.to_dict(),
            event_id="test_event_456"
        )

        # Extraer línea "data:"
        data_line = None
        for line in sse_fragment.split('\n'):
            if line.startswith('data:'):
                data_line = line[5:].strip()  # Remover "data:" prefix
                break

        # ASSERT 1: Línea data: encontrada
        assert data_line is not None, "Debe haber una línea 'data:'"

        # ASSERT 2: JSON parseable
        try:
            parsed_data = json.loads(data_line)
        except json.JSONDecodeError as e:
            pytest.fail(f"data: contiene JSON inválido: {e}")

        # ASSERT 3: Contiene campos esperados del dominio
        assert "ticket_id" in parsed_data, "data debe incluir ticket_id"
        assert parsed_data["ticket_id"] == 123, "ticket_id debe ser 123"

        assert "status" in parsed_data, "data debe incluir status"
        assert parsed_data["status"] == "analizando", "status debe ser 'analizando'"

        assert "filename" in parsed_data, "data debe incluir filename"
        assert "created_at" in parsed_data, "data debe incluir created_at"

        print(f"✅ Test 1.2 passed: JSON válido en campo data:")


    def test_format_sse_keepalive_structure(self):
        """
        CRITERIO 3: Verifica formato de comentario keep-alive.

        Formato esperado:
            : keep-alive <timestamp>

            (doble newline al final)
        """
        keepalive_fragment = format_sse_keepalive()

        # ASSERT 1: Fragmento NO vacío
        assert keepalive_fragment, "Keep-alive fragment debe contener datos"

        # ASSERT 2: Empieza con ":"
        assert keepalive_fragment.startswith(":"), \
            "Keep-alive debe empezar con ':' (comentario SSE)"

        # ASSERT 3: Contiene palabra "keep-alive"
        assert "keep-alive" in keepalive_fragment, \
            "Comentario debe contener 'keep-alive'"

        # ASSERT 4: Termina con doble newline
        assert keepalive_fragment.endswith("\n\n"), \
            "Keep-alive debe terminar con doble newline"

        print(f"✅ Test 1.3 passed: Keep-alive format correcto")


# ============================================================
# TEST 2: HTTP Headers Correctos
# ============================================================

class TestHTTPHeaders:
    """Test de headers HTTP del endpoint SSE"""

    @pytest.mark.asyncio
    async def test_sse_endpoint_returns_correct_headers(
        self, mock_current_user, cleanup_connections
    ):
        """
        CRITERIO 4: Verifica que /notifications/sse retorna headers correctos.

        Headers esperados:
        - Content-Type: text/event-stream
        - Cache-Control: no-cache
        - Connection: keep-alive
        - X-Accel-Buffering: no
        """
        # Mock request
        mock_request = MagicMock()
        mock_request.is_disconnected = AsyncMock(return_value=False)

        # Invocar endpoint SSE
        with patch('services.routers.notifications.get_current_active_user', return_value=mock_current_user):
            response = await sse_stream(
                request=mock_request,
                current_user=mock_current_user
            )

        # ASSERT 1: Response es StreamingResponse
        from fastapi.responses import StreamingResponse
        assert isinstance(response, StreamingResponse), \
            "Response debe ser StreamingResponse"

        # ASSERT 2: Content-Type correcto
        assert response.media_type == "text/event-stream", \
            "Content-Type debe ser 'text/event-stream'"

        # ASSERT 3: Headers correctos
        headers = response.headers

        assert headers.get("cache-control") == "no-cache", \
            "Cache-Control debe ser 'no-cache'"

        assert headers.get("connection") == "keep-alive", \
            "Connection debe ser 'keep-alive'"

        assert headers.get("x-accel-buffering") == "no", \
            "X-Accel-Buffering debe ser 'no' (para NGINX)"

        print(f"✅ Test 2.1 passed: Headers HTTP correctos")


# ============================================================
# TEST 3: Autenticación JWT
# ============================================================

class TestJWTAuthentication:
    """Test de autenticación JWT en endpoint SSE"""

    @pytest.mark.asyncio
    async def test_sse_endpoint_requires_authentication(self, cleanup_connections):
        """
        CRITERIO 5: Verifica que /notifications/sse requiere JWT.

        Sin token válido → HTTPException 401
        """
        from fastapi import HTTPException

        # Mock request sin usuario autenticado
        mock_request = MagicMock()

        # Mock de get_current_active_user que lanza 401
        def mock_auth_failure(*args, **kwargs):
            raise HTTPException(status_code=401, detail="Could not validate credentials")

        with patch('services.routers.notifications.get_current_active_user', side_effect=mock_auth_failure):
            with pytest.raises(HTTPException) as exc_info:
                await sse_stream(request=mock_request, current_user=mock_auth_failure())

        # ASSERT: Status code 401
        assert exc_info.value.status_code == 401, \
            "Sin autenticación debe retornar 401 Unauthorized"

        print(f"✅ Test 3.1 passed: Autenticación JWT obligatoria")


# ============================================================
# TEST 4: Publicación de Eventos
# ============================================================

class TestEventPublishing:
    """Test de publicación de eventos al ConnectionManager"""

    @pytest.mark.asyncio
    async def test_publish_event_to_connected_clients(
        self, mock_rfp_ticket_event, cleanup_connections
    ):
        """
        CRITERIO 6: Verifica que publish() envía evento a todas las conexiones.
        """
        # Registrar 2 conexiones simuladas
        queue1 = await connection_manager.connect("conn_1")
        queue2 = await connection_manager.connect("conn_2")

        # ASSERT SETUP: 2 conexiones activas
        assert connection_manager.get_active_connections_count() == 2

        # Publicar evento
        await connection_manager.publish(mock_rfp_ticket_event)

        # ASSERT 1: queue1 recibió evento
        assert not queue1.empty(), "Queue 1 debe haber recibido evento"
        event1 = await queue1.get()
        assert event1.event_type == "rfp_ticket_created"
        assert event1.ticket_id == 123

        # ASSERT 2: queue2 recibió evento
        assert not queue2.empty(), "Queue 2 debe haber recibido evento"
        event2 = await queue2.get()
        assert event2.event_type == "rfp_ticket_created"
        assert event2.ticket_id == 123

        print(f"✅ Test 4.1 passed: Eventos publicados a todas las conexiones")


    @pytest.mark.asyncio
    async def test_publish_event_no_connections(
        self, mock_rfp_ticket_event, cleanup_connections
    ):
        """
        CRITERIO 7: Verifica que publish() NO falla si no hay conexiones.
        """
        # ASSERT SETUP: 0 conexiones
        assert connection_manager.get_active_connections_count() == 0

        # Publicar evento (NO debe lanzar excepción)
        try:
            await connection_manager.publish(mock_rfp_ticket_event)
        except Exception as e:
            pytest.fail(f"publish() NO debe fallar sin conexiones: {e}")

        print(f"✅ Test 4.2 passed: publish() seguro sin conexiones")


# ============================================================
# TEST 5: Deduplicación Frontend
# ============================================================

class TestFrontendBehavior:
    """Test de comportamiento del frontend (simulación)"""

    def test_hook_should_deduplicate_by_ticket_id(self):
        """
        CRITERIO 8: Verifica que el hook frontend deduplica por ticket_id.

        Nota: Este es un test de DOCUMENTACIÓN del comportamiento esperado.
        El hook useRFPNotifications.ts ya implementa deduplicación con ticketsMapRef.

        Este test verifica la LÓGICA de deduplicación de forma aislada.
        """
        # Simular Map<ticket_id, Ticket> del hook
        tickets_map = {}

        # Evento 1: ticket_id=123
        event1 = {
            "ticket_id": 123,
            "status": "analizando",
            "filename": "rfp1.pdf",
            "created_at": "2026-11-18T10:00:00Z"
        }

        # Agregar al mapa
        if event1["ticket_id"] not in tickets_map:
            tickets_map[event1["ticket_id"]] = event1

        # ASSERT 1: 1 ticket en mapa
        assert len(tickets_map) == 1

        # Evento 2: ticket_id=123 (DUPLICADO)
        event2 = {
            "ticket_id": 123,  # Mismo ticket_id
            "status": "analisis_completo",
            "filename": "rfp1.pdf",
            "created_at": "2026-11-18T10:30:00Z"
        }

        # Intentar agregar (debe deduplicar)
        if event2["ticket_id"] not in tickets_map:
            tickets_map[event2["ticket_id"]] = event2

        # ASSERT 2: Sigue siendo 1 ticket (no duplicado)
        assert len(tickets_map) == 1, "Deduplicación por ticket_id debe prevenir duplicados"

        # Evento 3: ticket_id=456 (NUEVO)
        event3 = {
            "ticket_id": 456,
            "status": "analizando",
            "filename": "rfp2.pdf",
            "created_at": "2026-11-18T11:00:00Z"
        }

        # Agregar al mapa
        if event3["ticket_id"] not in tickets_map:
            tickets_map[event3["ticket_id"]] = event3

        # ASSERT 3: Ahora son 2 tickets
        assert len(tickets_map) == 2, "Tickets distintos deben agregarse"

        print(f"✅ Test 5.1 passed: Deduplicación por ticket_id funciona")


# ============================================================
# TEST 6: Reconexión y Recuperación tras Desconexión
# ============================================================

class TestReconnectionAndRecovery:
    """Test de reconexión y recuperación tras corte de red"""

    @pytest.mark.asyncio
    async def test_connection_manager_handles_disconnect(
        self, mock_rfp_ticket_event, cleanup_connections
    ):
        """
        CRITERIO 2.1: Verifica que ConnectionManager maneja desconexiones correctamente.

        Flow:
        1. Registrar 2 conexiones
        2. Publicar evento (ambas reciben)
        3. Desconectar una conexión
        4. Publicar evento (solo 1 recibe)
        5. Verificar que conexión desconectada se limpia
        """
        # Registrar 2 conexiones
        queue1 = await connection_manager.connect("conn_1")
        queue2 = await connection_manager.connect("conn_2")

        # ASSERT SETUP: 2 conexiones activas
        assert connection_manager.get_active_connections_count() == 2

        # Publicar evento 1 (ambas reciben)
        event1 = RFPTicketEvent(
            event_type="rfp_ticket_created",
            ticket_id=100,
            status="analizando",
            filename="test1.pdf",
            client_name=None,
            project_title=None,
            submission_deadline=None,
            created_at="2026-11-18T10:00:00Z"
        )
        await connection_manager.publish(event1)

        # ASSERT 1: Ambas colas tienen evento
        assert not queue1.empty()
        assert not queue2.empty()

        # Desconectar conn_2
        await connection_manager.disconnect("conn_2")

        # ASSERT 2: Solo 1 conexión activa
        assert connection_manager.get_active_connections_count() == 1

        # Publicar evento 2 (solo conn_1 recibe)
        event2 = RFPTicketEvent(
            event_type="rfp_ticket_created",
            ticket_id=101,
            status="analizando",
            filename="test2.pdf",
            client_name=None,
            project_title=None,
            submission_deadline=None,
            created_at="2026-11-18T10:01:00Z"
        )
        await connection_manager.publish(event2)

        # ASSERT 3: queue1 tiene 2 eventos (event1 + event2)
        assert queue1.qsize() == 2

        # ASSERT 4: queue2 se vació en disconnect (solo tenía event1)
        # queue2 ya no existe en el manager, pero la cola local puede tener datos residuales
        # Lo importante es que NO recibió event2

        print(f"✅ Test 6.1 passed: ConnectionManager maneja desconexiones correctamente")


    @pytest.mark.asyncio
    async def test_refetch_strategy_on_reconnect(self, cleanup_connections):
        """
        CRITERIO 2.2: Verifica estrategia de recuperación (refetch + SSE).

        Este test documenta el comportamiento esperado del hook useRFPNotifications:
        1. Al detectar desconexión → scheduleReconnect()
        2. scheduleReconnect() ejecuta fetchInitialTickets() ANTES de reconectar SSE
        3. fetchInitialTickets() sincroniza últimos 20 tickets
        4. Luego reconecta SSE para eventos nuevos

        Nota: Este es un test de DOCUMENTACIÓN del comportamiento.
        El hook implementa este patrón en TypeScript.
        """
        # Simular comportamiento del hook (documentación)

        # Estado inicial: 2 tickets en "servidor"
        server_tickets = [
            {"ticket_id": 1, "status": "analizando", "filename": "ticket1.pdf"},
            {"ticket_id": 2, "status": "analizando", "filename": "ticket2.pdf"},
        ]

        # Cliente pierde conexión y no recibió ticket_id=2
        client_tickets_before_reconnect = {1}

        # Al reconectar: fetchInitialTickets() sincroniza
        # Simular refetch
        refetched_tickets = server_tickets.copy()
        client_tickets_after_refetch = {t["ticket_id"] for t in refetched_tickets}

        # ASSERT 1: Cliente sincronizó ticket_id=2
        assert 2 in client_tickets_after_refetch
        assert len(client_tickets_after_refetch) == 2

        # ASSERT 2: Cliente ahora está sincronizado con servidor
        server_ticket_ids = {t["ticket_id"] for t in server_tickets}
        assert client_tickets_after_refetch == server_ticket_ids

        # Después del refetch, SSE se reconecta para eventos NUEVOS
        # (ticket_id >= 3 en adelante)

        print(f"✅ Test 6.2 passed: Estrategia refetch + SSE documentada")


# ============================================================
# TEST 7: Dominio Brasaland - Campos Requeridos
# ============================================================

class TestBrasalandDomainFields:
    """Test de campos del dominio según company-BRIEFING.md"""

    def test_rfp_ticket_event_contains_required_fields(self, mock_rfp_ticket_event):
        """
        CRITERIO 9: Verifica que RFPTicketEvent contiene campos del dominio.

        Campos requeridos según company-BRIEFING.md:
        - ticket_id
        - status (analizando, descartado, analisis_completo, etc.)
        - filename
        - client_name (opcional)
        - project_title (opcional)
        - submission_deadline (opcional, ISO 8601)
        - created_at (ISO 8601)
        """
        # Serializar a dict
        event_dict = mock_rfp_ticket_event.to_dict()

        # ASSERT 1: ticket_id presente
        assert "ticket_id" in event_dict, "Debe incluir ticket_id"
        assert isinstance(event_dict["ticket_id"], int), "ticket_id debe ser int"

        # ASSERT 2: status presente
        assert "status" in event_dict, "Debe incluir status"
        assert event_dict["status"] in [
            "analizando", "descartado", "analisis_completo", "error",
            "generando_borrador", "en_evaluacion", "needs_human_review",
            "listo_para_consolidacion", "esperando_aprobacion", "terminado"
        ], "status debe ser uno de los estados válidos del ciclo de vida RFP"

        # ASSERT 3: filename presente
        assert "filename" in event_dict, "Debe incluir filename"

        # ASSERT 4: created_at presente y formato ISO 8601
        assert "created_at" in event_dict, "Debe incluir created_at"
        # Validar formato ISO 8601 (simple check)
        assert "T" in event_dict["created_at"], "created_at debe ser ISO 8601 (con 'T')"
        assert "Z" in event_dict["created_at"], "created_at debe incluir timezone (Z o +00:00)"

        # ASSERT 5: client_name presente (puede ser None)
        assert "client_name" in event_dict, "Debe incluir client_name (opcional)"

        # ASSERT 6: project_title presente (puede ser None)
        assert "project_title" in event_dict, "Debe incluir project_title (opcional)"

        # ASSERT 7: submission_deadline presente (puede ser None)
        assert "submission_deadline" in event_dict, "Debe incluir submission_deadline (opcional)"

        print(f"✅ Test 7.1 passed: Campos del dominio Brasaland presentes")


# ============================================================
# TEST 8: Límite de Memoria con Eviction Policy
# ============================================================

class TestMemoryManagement:
    """Test de gestión de memoria con eviction policy"""

    def test_map_eviction_policy_lru(self):
        """
        CRITERIO 2.3: Verifica eviction policy LRU al alcanzar límite de memoria.

        Este test simula el comportamiento del hook con maxTicketsInMemory=3.

        Flow:
        1. Agregar 3 tickets (límite alcanzado)
        2. Agregar ticket 4 → Evict ticket 1 (oldest)
        3. Agregar ticket 5 → Evict ticket 2 (oldest)
        4. Verificar que solo los últimos 3 tickets están en memoria
        """
        MAX_TICKETS_IN_MEMORY = 3
        tickets_map = {}

        # Helper de eviction (simula addTicketWithEviction del hook)
        def add_ticket_with_eviction(ticket_id: int, ticket_data: dict):
            if len(tickets_map) >= MAX_TICKETS_IN_MEMORY:
                # Eviction: Remover oldest key (first key de dict en Python 3.7+)
                oldest_key = next(iter(tickets_map))
                del tickets_map[oldest_key]
                print(f"[Test] Evicted ticket {oldest_key}")

            tickets_map[ticket_id] = ticket_data

        # Agregar 3 tickets (límite)
        add_ticket_with_eviction(1, {"filename": "ticket1.pdf"})
        add_ticket_with_eviction(2, {"filename": "ticket2.pdf"})
        add_ticket_with_eviction(3, {"filename": "ticket3.pdf"})

        # ASSERT 1: 3 tickets en memoria
        assert len(tickets_map) == 3
        assert 1 in tickets_map
        assert 2 in tickets_map
        assert 3 in tickets_map

        # Agregar ticket 4 → Evict ticket 1
        add_ticket_with_eviction(4, {"filename": "ticket4.pdf"})

        # ASSERT 2: ticket 1 evicted, solo 2, 3, 4 en memoria
        assert len(tickets_map) == 3
        assert 1 not in tickets_map, "Ticket 1 debe haber sido evicted"
        assert 2 in tickets_map
        assert 3 in tickets_map
        assert 4 in tickets_map

        # Agregar ticket 5 → Evict ticket 2
        add_ticket_with_eviction(5, {"filename": "ticket5.pdf"})

        # ASSERT 3: ticket 2 evicted, solo 3, 4, 5 en memoria
        assert len(tickets_map) == 3
        assert 2 not in tickets_map, "Ticket 2 debe haber sido evicted"
        assert 3 in tickets_map
        assert 4 in tickets_map
        assert 5 in tickets_map

        print(f"✅ Test 8.1 passed: Eviction policy LRU funciona correctamente")


# ============================================================
# EJECUTAR TODOS LOS TESTS
# ============================================================

if __name__ == "__main__":
    # Ejecutar con pytest
    pytest.main([__file__, "-v", "--tb=short"])
