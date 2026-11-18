"""
Tests de Persistencia - WebSocket Chat con TinyDB

OBJETIVO: Verificar que los mensajes se guardan y rehidratan correctamente

Ejecutar:
    pytest tests/test_chat_persistence.py -v
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime

# Agregar raíz al path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "services" / "api"))

from app.tinydb_database import (
    get_chat_history,
    save_chat_message,
    update_chat_message_status,
    get_chat_message_by_id,
    chat_messages_table
)


@pytest.fixture(autouse=True)
def cleanup_chat_messages():
    """Limpiar tabla de mensajes antes y después de cada test."""
    chat_messages_table.truncate()
    yield
    chat_messages_table.truncate()


# ============================================================
# TEST 1: Guardar Mensaje
# ============================================================

def test_save_chat_message():
    """Test: Guardar mensaje en TinyDB."""
    session_id = "session_test_1"
    message_id = "msg_test_001"

    # Guardar mensaje
    saved = save_chat_message(
        session_id=session_id,
        message_id=message_id,
        role="user",
        content="Hola, ¿cómo estás?",
        status="completed"
    )

    # ASSERT: Mensaje guardado tiene campos correctos
    assert saved["session_id"] == session_id
    assert saved["message_id"] == message_id
    assert saved["role"] == "user"
    assert saved["content"] == "Hola, ¿cómo estás?"
    assert saved["status"] == "completed"
    assert "created_at" in saved


# ============================================================
# TEST 2: Cargar Historial
# ============================================================

def test_get_chat_history():
    """Test: Cargar historial de chat ordenado por fecha."""
    session_id = "session_test_2"

    # Guardar 3 mensajes
    save_chat_message(session_id, "msg_1", "user", "Mensaje 1", "completed")
    save_chat_message(session_id, "msg_2", "assistant", "Respuesta 1", "completed")
    save_chat_message(session_id, "msg_3", "user", "Mensaje 2", "completed")

    # Cargar historial
    history = get_chat_history(session_id)

    # ASSERT: 3 mensajes cargados
    assert len(history) == 3

    # ASSERT: Orden cronológico
    assert history[0]["message_id"] == "msg_1"
    assert history[1]["message_id"] == "msg_2"
    assert history[2]["message_id"] == "msg_3"


# ============================================================
# TEST 3: Actualizar Status de Mensaje
# ============================================================

def test_update_chat_message_status():
    """Test: Actualizar status de mensaje (interrupted)."""
    session_id = "session_test_3"
    message_id = "msg_test_003"

    # Guardar mensaje en status=streaming
    save_chat_message(
        session_id=session_id,
        message_id=message_id,
        role="assistant",
        content="Respuesta parcial...",
        status="streaming"
    )

    # Actualizar a interrupted
    updated = update_chat_message_status(message_id, "interrupted")

    # ASSERT: Status actualizado
    assert updated is not None
    assert updated["status"] == "interrupted"
    assert "updated_at" in updated

    # ASSERT: Contenido preservado
    assert updated["content"] == "Respuesta parcial..."


# ============================================================
# TEST 4: Obtener Mensaje por ID
# ============================================================

def test_get_chat_message_by_id():
    """Test: Obtener mensaje específico por message_id."""
    session_id = "session_test_4"
    message_id = "msg_test_004"

    # Guardar mensaje
    save_chat_message(session_id, message_id, "user", "Test", "completed")

    # Obtener por ID
    message = get_chat_message_by_id(message_id)

    # ASSERT: Mensaje encontrado
    assert message is not None
    assert message["message_id"] == message_id
    assert message["content"] == "Test"


# ============================================================
# TEST 5: Historial de Sesión Vacía
# ============================================================

def test_get_chat_history_empty():
    """Test: Historial vacío retorna lista vacía."""
    history = get_chat_history("session_inexistente")

    # ASSERT: Lista vacía
    assert history == []


# ============================================================
# TEST 6: Actualizar Mensaje Inexistente
# ============================================================

def test_update_nonexistent_message():
    """Test: Actualizar mensaje que no existe retorna None."""
    updated = update_chat_message_status("msg_inexistente", "completed")

    # ASSERT: None si no existe
    assert updated is None


# ============================================================
# TEST 7: Múltiples Sesiones Aisladas
# ============================================================

def test_multiple_sessions_isolated():
    """Test: Mensajes de diferentes sesiones están aislados."""
    # Sesión 1
    save_chat_message("session_1", "msg_1_1", "user", "Hola 1", "completed")
    save_chat_message("session_1", "msg_1_2", "assistant", "Respuesta 1", "completed")

    # Sesión 2
    save_chat_message("session_2", "msg_2_1", "user", "Hola 2", "completed")

    # Cargar historial de cada sesión
    history_1 = get_chat_history("session_1")
    history_2 = get_chat_history("session_2")

    # ASSERT: Sesiones aisladas
    assert len(history_1) == 2
    assert len(history_2) == 1

    # ASSERT: Contenido correcto
    assert all(msg["session_id"] == "session_1" for msg in history_1)
    assert all(msg["session_id"] == "session_2" for msg in history_2)


# ============================================================
# TEST 8: Preservación de Mensaje Interrumpido
# ============================================================

def test_interrupted_message_preservation():
    """Test: Mensaje interrumpido preserva contenido parcial."""
    session_id = "session_test_8"
    message_id = "msg_test_008"

    partial_content = "Esta es una respuesta parcial que se interrum"

    # Guardar mensaje parcial
    save_chat_message(
        session_id=session_id,
        message_id=message_id,
        role="assistant",
        content=partial_content,
        status="streaming"
    )

    # Marcar como interrumpido
    update_chat_message_status(message_id, "interrupted")

    # Cargar historial
    history = get_chat_history(session_id)

    # ASSERT: Mensaje preservado con status=interrupted
    assert len(history) == 1
    assert history[0]["status"] == "interrupted"
    assert history[0]["content"] == partial_content  # ← Contenido parcial preservado


# ============================================================
# TEST 9: Simulación de Reconexión
# ============================================================

def test_reconnection_simulation():
    """Test: Simular reconexión y rehidratación."""
    session_id = "session_test_9"

    # PRIMERA CONEXIÓN: Enviar mensaje
    save_chat_message(session_id, "msg_9_1", "user", "Mensaje inicial", "completed")
    save_chat_message(session_id, "msg_9_2", "assistant", "Respuesta inicial", "completed")

    # Simular desconexión (no hacer nada)

    # SEGUNDA CONEXIÓN: Cargar historial (rehidratación)
    history = get_chat_history(session_id)

    # ASSERT: Historial completo recuperado
    assert len(history) == 2
    assert history[0]["content"] == "Mensaje inicial"
    assert history[1]["content"] == "Respuesta inicial"


# ============================================================
# TEST 10: Orden Cronológico con Timestamps Diferentes
# ============================================================

def test_chronological_order():
    """Test: Mensajes se ordenan cronológicamente por created_at."""
    session_id = "session_test_10"

    # Guardar mensajes con pequeños delays
    import time

    save_chat_message(session_id, "msg_10_1", "user", "Primero", "completed")
    time.sleep(0.01)

    save_chat_message(session_id, "msg_10_2", "assistant", "Segundo", "completed")
    time.sleep(0.01)

    save_chat_message(session_id, "msg_10_3", "user", "Tercero", "completed")

    # Cargar historial
    history = get_chat_history(session_id)

    # ASSERT: Orden cronológico preservado
    assert history[0]["content"] == "Primero"
    assert history[1]["content"] == "Segundo"
    assert history[2]["content"] == "Tercero"

    # ASSERT: Timestamps crecientes
    ts1 = history[0]["created_at"]
    ts2 = history[1]["created_at"]
    ts3 = history[2]["created_at"]

    assert ts1 <= ts2 <= ts3


# ============================================================
# EJECUTAR TODOS LOS TESTS
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
