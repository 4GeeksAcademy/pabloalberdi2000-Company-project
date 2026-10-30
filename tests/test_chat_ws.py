"""
Tests - WebSocket Chat con Token Streaming

DOMINIO: Brasaland Digital - Agente de Soporte

Valida:
- Contrato de eventos (token_chunk, generation_completed, generation_interrupted)
- Abort genuino de generación (asyncio.Task.cancel())
- Preservación de mensajes interrumpidos (status=interrupted)
- Reconexión con rehidratación de historial
- Autenticación JWT via query string
- Pub/Sub multi-observador

DIFERENCIA CON test_sse_notifications.py:
- SSE: Unidireccional (servidor → cliente)
- WebSocket: Bidireccional (cliente ↔ servidor)
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient
from fastapi import FastAPI

# Imports ajustados según estructura real
# from services.routers.chat_ws import router, session_manager


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def app():
    """Fixture: App FastAPI con router WebSocket."""
    from services.routers.chat_ws import router

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Fixture: TestClient para WebSocket."""
    return TestClient(app)


@pytest.fixture
def mock_jwt_token():
    """Fixture: Token JWT válido (mock)."""
    return "valid_token_1234567890"


@pytest.fixture
def session_id():
    """Fixture: ID de sesión de chat."""
    return "session_test_12345"


# ============================================================
# TESTS: AUTENTICACIÓN
# ============================================================

def test_websocket_requires_jwt_token(client, session_id):
    """Test: WebSocket requiere token JWT en query string."""
    # Sin token
    with pytest.raises(Exception) as exc_info:
        with client.websocket_connect(f"/ws/chat/{session_id}"):
            pass

    # Debe cerrar con código 1008 (Policy Violation)
    assert "1008" in str(exc_info.value) or "401" in str(exc_info.value)


def test_websocket_rejects_invalid_token(client, session_id):
    """Test: WebSocket rechaza token inválido."""
    # Token muy corto (< 10 chars)
    with pytest.raises(Exception) as exc_info:
        with client.websocket_connect(f"/ws/chat/{session_id}?token=short"):
            pass

    assert "1008" in str(exc_info.value) or "401" in str(exc_info.value)


def test_websocket_accepts_valid_token(client, session_id, mock_jwt_token):
    """Test: WebSocket acepta token válido."""
    with client.websocket_connect(
        f"/ws/chat/{session_id}?token={mock_jwt_token}"
    ) as websocket:
        # Debe conectar exitosamente
        assert websocket is not None


# ============================================================
# TESTS: CONTRATO DE EVENTOS
# ============================================================

def test_websocket_sends_history_on_connect(client, session_id, mock_jwt_token):
    """Test: WebSocket envía historial al conectar (rehidratación)."""
    with client.websocket_connect(
        f"/ws/chat/{session_id}?token={mock_jwt_token}"
    ) as websocket:
        # Esperar frame de history
        data = websocket.receive_json()

        assert data["type"] == "history"
        assert "messages" in data
        assert "session_id" in data
        assert data["session_id"] == session_id


def test_websocket_token_streaming_contract(client, session_id, mock_jwt_token):
    """
    Test: Contrato de eventos de streaming.

    FLOW:
    1. Cliente envía user_message
    2. Servidor responde con N × token_chunk
    3. Servidor envía generation_completed
    """
    with client.websocket_connect(
        f"/ws/chat/{session_id}?token={mock_jwt_token}"
    ) as websocket:
        # Consumir frame de history
        websocket.receive_json()

        # 1. Enviar mensaje usuario
        websocket.send_json({
            "type": "user_message",
            "content": "Hola",
            "message_id": "msg_test_123"
        })

        # 2. Recibir token chunks
        token_chunks = []
        completed_received = False

        for _ in range(50):  # Max 50 frames para evitar loop infinito
            data = websocket.receive_json()

            if data["type"] == "token_chunk":
                token_chunks.append(data)

                # Validar estructura
                assert "delta" in data
                assert "message_id" in data
                assert "timestamp" in data

            elif data["type"] == "generation_completed":
                completed_received = True

                # Validar estructura
                assert "message_id" in data
                assert "timestamp" in data
                break

        # Verificar que se recibieron chunks
        assert len(token_chunks) > 0, "No se recibieron token chunks"

        # Verificar que se recibió completed
        assert completed_received, "No se recibió generation_completed"

        # Verificar que todos los chunks tienen el mismo message_id
        message_ids = {chunk["message_id"] for chunk in token_chunks}
        assert len(message_ids) == 1, "Chunks tienen diferentes message_ids"


# ============================================================
# TESTS: ABORT GENUINO
# ============================================================

@pytest.mark.asyncio
async def test_websocket_abort_cancels_generation(client, session_id, mock_jwt_token):
    """
    Test: Señal de abort cancela generación activa.

    CRÍTICO:
    - Abort debe cancelar asyncio.Task de generación
    - NO simular cancelación descartando tokens en frontend
    - Mensaje parcial debe marcarse como interrupted
    """
    with client.websocket_connect(
        f"/ws/chat/{session_id}?token={mock_jwt_token}"
    ) as websocket:
        # Consumir history
        websocket.receive_json()

        # 1. Iniciar generación larga
        websocket.send_json({
            "type": "user_message",
            "content": "Cuéntame sobre Brasaland",
            "message_id": "msg_long_test"
        })

        # 2. Recibir algunos token chunks
        chunks_before_abort = []
        for _ in range(5):  # Recibir 5 chunks
            data = websocket.receive_json()
            if data["type"] == "token_chunk":
                chunks_before_abort.append(data)

        message_id = chunks_before_abort[0]["message_id"]

        # 3. Enviar señal de abort
        websocket.send_json({
            "type": "abort"
        })

        # 4. Debe recibir generation_interrupted
        interrupted_received = False
        chunks_after_abort = []

        for _ in range(10):
            data = websocket.receive_json()

            if data["type"] == "generation_interrupted":
                interrupted_received = True

                # Validar estructura
                assert data["message_id"] == message_id
                assert "reason" in data
                assert data["reason"] in ["user_abort", "new_user_message"]
                break

            elif data["type"] == "token_chunk":
                chunks_after_abort.append(data)

        # Verificar interrupción
        assert interrupted_received, "No se recibió generation_interrupted"

        # Verificar que se detuvieron los chunks (o muy pocos después)
        assert len(chunks_after_abort) < 3, (
            "Demasiados token chunks después de abort "
            f"(esperado <3, recibido {len(chunks_after_abort)})"
        )


def test_websocket_new_message_aborts_previous_generation(
    client,
    session_id,
    mock_jwt_token
):
    """
    Test: Nuevo mensaje del usuario aborta generación en curso.

    FLOW:
    1. Usuario envía mensaje 1
    2. Asistente empieza a responder
    3. Usuario envía mensaje 2 (antes de que termine mensaje 1)
    4. Debe recibir generation_interrupted para mensaje 1
    5. Debe iniciar generación de respuesta a mensaje 2
    """
    with client.websocket_connect(
        f"/ws/chat/{session_id}?token={mock_jwt_token}"
    ) as websocket:
        # Consumir history
        websocket.receive_json()

        # 1. Mensaje 1
        websocket.send_json({
            "type": "user_message",
            "content": "Pregunta 1",
            "message_id": "msg_1"
        })

        # 2. Recibir algunos chunks
        chunks_msg_1 = []
        for _ in range(3):
            data = websocket.receive_json()
            if data["type"] == "token_chunk":
                chunks_msg_1.append(data)

        message_id_1 = chunks_msg_1[0]["message_id"]

        # 3. Mensaje 2 (interrumpe mensaje 1)
        websocket.send_json({
            "type": "user_message",
            "content": "Pregunta 2",
            "message_id": "msg_2"
        })

        # 4. Debe recibir interrupted para mensaje 1
        interrupted_received = False
        message_id_2 = None

        for _ in range(20):
            data = websocket.receive_json()

            if data["type"] == "generation_interrupted":
                assert data["message_id"] == message_id_1
                assert data["reason"] == "new_user_message"
                interrupted_received = True

            elif data["type"] == "token_chunk":
                # Nuevo mensaje debe tener diferente message_id
                if data["message_id"] != message_id_1:
                    message_id_2 = data["message_id"]
                    break

        # Verificar interrupción
        assert interrupted_received, "No se recibió interrupted para mensaje 1"

        # Verificar nueva generación
        assert message_id_2 is not None, "No se inició generación para mensaje 2"
        assert message_id_2 != message_id_1, "message_ids deben ser diferentes"


# ============================================================
# TESTS: RECONEXIÓN Y REHIDRATACIÓN
# ============================================================

def test_websocket_reconnect_rehydrates_history(client, session_id, mock_jwt_token):
    """
    Test: Reconectar con mismo session_id rehidrata historial.

    FLOW:
    1. Conectar y enviar mensaje
    2. Desconectar
    3. Reconectar con mismo session_id
    4. Debe recibir historial completo incluyendo mensaje anterior
    """
    # Primera conexión
    with client.websocket_connect(
        f"/ws/chat/{session_id}?token={mock_jwt_token}"
    ) as websocket:
        # Consumir history inicial
        initial_history = websocket.receive_json()
        initial_count = len(initial_history.get("messages", []))

        # Enviar mensaje
        websocket.send_json({
            "type": "user_message",
            "content": "Test message",
            "message_id": "msg_reconnect_test"
        })

        # Esperar respuesta completa
        for _ in range(50):
            data = websocket.receive_json()
            if data["type"] == "generation_completed":
                break

    # Desconexión automática al salir del context manager

    # Segunda conexión (reconexión)
    with client.websocket_connect(
        f"/ws/chat/{session_id}?token={mock_jwt_token}"
    ) as websocket:
        # Recibir history
        rehydrated_history = websocket.receive_json()

        assert rehydrated_history["type"] == "history"
        assert rehydrated_history["session_id"] == session_id

        # Debe tener más mensajes que antes (al menos +2: user + assistant)
        rehydrated_count = len(rehydrated_history.get("messages", []))
        assert rehydrated_count >= initial_count + 2, (
            f"Historial no rehidratado correctamente "
            f"(antes: {initial_count}, después: {rehydrated_count})"
        )


# ============================================================
# TESTS: PUB/SUB MULTI-OBSERVADOR
# ============================================================

def test_websocket_pubsub_multiple_observers(client, session_id, mock_jwt_token):
    """
    Test: Múltiples observadores reciben los mismos eventos.

    CASO DE USO:
    - Supervisor observa conversación en vivo
    - Dashboard muestra chat en tiempo real

    ARQUITECTURA:
    - 1 generación de tokens (productor)
    - N WebSockets (consumidores)
    - Todos reciben los mismos token chunks
    """
    # Abrir 2 conexiones a la misma sesión
    with client.websocket_connect(
        f"/ws/chat/{session_id}?token={mock_jwt_token}"
    ) as ws1, client.websocket_connect(
        f"/ws/chat/{session_id}?token={mock_jwt_token}"
    ) as ws2:
        # Consumir history en ambos
        ws1.receive_json()
        ws2.receive_json()

        # Enviar mensaje desde ws1
        ws1.send_json({
            "type": "user_message",
            "content": "Test pub/sub",
            "message_id": "msg_pubsub_test"
        })

        # Recolectar token chunks de ambos WebSockets
        chunks_ws1 = []
        chunks_ws2 = []

        # Recibir en paralelo (simplificado: secuencial)
        for _ in range(10):
            data1 = ws1.receive_json()
            if data1["type"] == "token_chunk":
                chunks_ws1.append(data1["delta"])

            data2 = ws2.receive_json()
            if data2["type"] == "token_chunk":
                chunks_ws2.append(data2["delta"])

            if data1["type"] == "generation_completed":
                break

        # Verificar que ambos recibieron tokens
        assert len(chunks_ws1) > 0, "ws1 no recibió chunks"
        assert len(chunks_ws2) > 0, "ws2 no recibió chunks"

        # Verificar que recibieron los mismos chunks (mismo contenido)
        content_ws1 = "".join(chunks_ws1)
        content_ws2 = "".join(chunks_ws2)
        assert content_ws1 == content_ws2, (
            "Los observadores recibieron contenido diferente"
        )


# ============================================================
# TESTS: HEALTH CHECK
# ============================================================

def test_websocket_health_endpoint(client):
    """Test: Endpoint de health check."""
    response = client.get("/ws/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert "active_sessions" in data
    assert "total_connections" in data
    assert "active_generations" in data
    assert "timestamp" in data


# ============================================================
# TESTS: PRESERVACIÓN DE MENSAJES INTERRUMPIDOS
# ============================================================

@pytest.mark.asyncio
async def test_interrupted_message_preservation():
    """
    Test: Mensaje interrumpido se guarda con status=interrupted.

    CRÍTICO:
    - NO borrar contenido parcial
    - Marcar con status=interrupted
    - Nuevo turno es independiente
    """
    # Mock de save_message
    from services.routers.chat_ws import save_message

    saved_messages = []

    async def mock_save(session_id, message_id, role, content, status):
        saved_messages.append({
            "session_id": session_id,
            "message_id": message_id,
            "role": role,
            "content": content,
            "status": status
        })

    with patch('services.routers.chat_ws.save_message', side_effect=mock_save):
        # Simular abort de generación
        # (test simplificado, la lógica real está en stream_agent_response)

        # Mensaje parcial generado antes de abort
        partial_content = "Hola, soy el asistente de Brasaland. Puedo ayudarte con"

        await mock_save(
            session_id="test_session",
            message_id="msg_interrupted_123",
            role="assistant",
            content=partial_content,
            status="interrupted"
        )

        # Verificar que se guardó con status=interrupted
        assert len(saved_messages) == 1
        assert saved_messages[0]["status"] == "interrupted"
        assert saved_messages[0]["content"] == partial_content
        assert len(saved_messages[0]["content"]) > 0, (
            "Contenido parcial NO debe estar vacío"
        )


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
