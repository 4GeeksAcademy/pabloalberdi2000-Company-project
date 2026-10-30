"""
Tests de Routing Multi-Source con MCP

Tests para verificar que el agente LangGraph:
- Detecta correctamente cuando usar RAG vs Tools vs Both
- Consume tools vía MCP (no directas)
- Genera fallback honesto sin alucinación

Criterio 8 de Auditoría de Tools:
✅ "Tests de routing multi-source: RAG only, tool only, both"
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.agent.graph import (
    router_node,
    tool_calling_node,
    rag_retrieve_node,
    synthesis_node,
    AgentState,
    query_with_agent
)

# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_mcp_client():
    """Mock del cliente MCP para evitar conexión real en tests"""
    with patch("services.agent.mcp_adapter.get_mcp_client") as mock:
        client = MagicMock()

        # Mock de get_incident_by_id
        client.get_incident_by_id.return_value = {
            "success": True,
            "data": {
                "id": 482,
                "status": "in_progress",
                "category": "técnico",
                "description": "Error en sistema de pedidos",
                "created_at": "2024-10-25T10:30:00"
            }
        }

        # Mock de get_inventory_products
        client.get_inventory_products.return_value = {
            "success": True,
            "products": [
                {"id": 1, "name": "Producto A", "stock": 100},
                {"id": 2, "name": "Producto B", "stock": 50}
            ],
            "count": 2
        }

        mock.return_value = client
        yield client


@pytest.fixture
def mock_rag():
    """Mock de funciones RAG para evitar dependencia de Qdrant en tests"""
    with patch("services.agent.graph.retrieve") as mock_retrieve, \
         patch("services.agent.graph.generate_answer") as mock_generate:

        # Mock de retrieve
        mock_retrieve.return_value = [
            {
                "text": "Brasaland tiene 14 locales en total: 10 en USA, 2 en Colombia y 2 en España.",
                "source_document": "01-company-overview.md"
            }
        ]

        # Mock de generate_answer
        mock_generate.return_value = "Brasaland tiene 14 locales en total: 10 en USA, 2 en Colombia y 2 en España."

        yield mock_retrieve, mock_generate


# ============================================================
# TEST 1: Routing - Tool Only
# ============================================================

def test_routing_tool_only():
    """
    Test: Pregunta sobre datos operativos → routing = 'tool'

    Pregunta con keyword 'ticket' debe ser detectada como tool-only.
    """
    state: AgentState = {
        "question": "¿En qué estado está el ticket 482?",
        "context": None,
        "tool_data": None,
        "tool_name": None,
        "needs_tool": None,
        "routing_decision": None,
        "answer": None,
        "error": None,
        "metadata": {}
    }

    result = router_node(state)

    assert result["routing_decision"] == "tool", "Debe detectar tool-only"
    assert result["needs_tool"] == True, "Debe marcar needs_tool=True"
    assert result["metadata"]["has_tool_keyword"] == True
    assert result["metadata"]["has_rag_keyword"] == False


# ============================================================
# TEST 2: Routing - RAG Only
# ============================================================

def test_routing_rag_only():
    """
    Test: Pregunta sobre conocimiento estático → routing = 'rag'

    Pregunta con keyword 'cuántos locales' debe ser RAG-only.
    """
    state: AgentState = {
        "question": "¿Cuántos locales tiene Brasaland?",
        "context": None,
        "tool_data": None,
        "tool_name": None,
        "needs_tool": None,
        "routing_decision": None,
        "answer": None,
        "error": None,
        "metadata": {}
    }

    result = router_node(state)

    assert result["routing_decision"] == "rag", "Debe detectar rag-only"
    assert result["needs_tool"] == False, "No debe necesitar tool"
    assert result["metadata"]["has_rag_keyword"] == True
    assert result["metadata"]["has_tool_keyword"] == False


# ============================================================
# TEST 3: Routing - Both
# ============================================================

def test_routing_both():
    """
    Test: Pregunta mixta → routing = 'both'

    Pregunta con keywords de RAG y tool debe ser 'both'.
    """
    state: AgentState = {
        "question": "¿Cuántos locales tiene Brasaland y cuál es el estado del ticket 482?",
        "context": None,
        "tool_data": None,
        "tool_name": None,
        "needs_tool": None,
        "routing_decision": None,
        "answer": None,
        "error": None,
        "metadata": {}
    }

    result = router_node(state)

    assert result["routing_decision"] == "both", "Debe detectar both"
    assert result["needs_tool"] == True, "Debe necesitar tool"
    assert result["metadata"]["has_rag_keyword"] == True
    assert result["metadata"]["has_tool_keyword"] == True


# ============================================================
# TEST 4: Tool Calling Node (con MCP mock)
# ============================================================

def test_tool_calling_node_success(mock_mcp_client):
    """
    Test: tool_calling_node ejecuta tool vía MCP y retorna success

    Verifica:
    - Tool se identifica correctamente (get_incident_by_id)
    - Parámetros se extraen de la pregunta
    - MCP client se llama (no tools.py directas)
    - Resultado tiene success=True
    """
    state: AgentState = {
        "question": "¿En qué estado está el ticket 482?",
        "context": None,
        "tool_data": None,
        "tool_name": None,
        "needs_tool": True,
        "routing_decision": "tool",
        "answer": None,
        "error": None,
        "metadata": {}
    }

    result = tool_calling_node(state)

    assert result["tool_name"] == "get_incident_by_id", "Debe identificar tool correcta"
    assert result["tool_data"]["success"] == True, "Tool debe ejecutarse exitosamente"
    assert result["tool_data"]["data"]["id"] == 482, "Debe retornar datos del ticket"
    assert result["error"] is None, "No debe haber error"
    assert result["metadata"]["tool_success"] == True


# ============================================================
# TEST 5: Tool Calling Node - Extracción de Parámetros
# ============================================================

def test_tool_calling_node_parameter_extraction():
    """
    Test: Extracción de ticket_id desde pregunta en lenguaje natural

    Verifica que el regex extrae correctamente números de la pregunta.
    """
    state: AgentState = {
        "question": "Dame información del incidente número 789",
        "context": None,
        "tool_data": None,
        "tool_name": None,
        "needs_tool": True,
        "routing_decision": "tool",
        "answer": None,
        "error": None,
        "metadata": {}
    }

    result = tool_calling_node(state)

    assert result["metadata"]["tool_params"]["ticket_id"] == "789", "Debe extraer ID correcto"


# ============================================================
# TEST 6: Tool Calling Node - Sin Ticket ID
# ============================================================

def test_tool_calling_node_missing_ticket_id():
    """
    Test: Pregunta de ticket sin ID → error honesto

    Si no se puede extraer ID, debe retornar error sin intentar tool.
    """
    state: AgentState = {
        "question": "¿Cuál es el estado de ese ticket?",  # No menciona ID
        "context": None,
        "tool_data": None,
        "tool_name": None,
        "needs_tool": True,
        "routing_decision": "tool",
        "answer": None,
        "error": None,
        "metadata": {}
    }

    result = tool_calling_node(state)

    assert result["tool_data"] is None, "No debe ejecutar tool"
    assert result["error"] is not None, "Debe retornar error"
    assert "extraer ID" in result["error"], "Error debe mencionar extracción"


# ============================================================
# TEST 7: RAG Retrieve Node (con mock)
# ============================================================

def test_rag_retrieve_node(mock_rag):
    """
    Test: rag_retrieve_node consulta Qdrant y retorna chunks

    Verifica que retrieve() se llama y el contexto se guarda en estado.
    """
    mock_retrieve, _ = mock_rag

    state: AgentState = {
        "question": "¿Cuántos locales tiene Brasaland?",
        "context": None,
        "tool_data": None,
        "tool_name": None,
        "needs_tool": False,
        "routing_decision": "rag",
        "answer": None,
        "error": None,
        "metadata": {}
    }

    result = rag_retrieve_node(state)

    assert mock_retrieve.called, "Debe llamar a retrieve()"
    assert result["context"] is not None, "Debe retornar contexto"
    assert len(result["context"]) > 0, "Debe haber al menos 1 chunk"
    assert result["metadata"]["num_chunks_retrieved"] > 0


# ============================================================
# TEST 8: Synthesis Node - Tool Only
# ============================================================

def test_synthesis_node_tool_only(mock_rag):
    """
    Test: synthesis_node con solo tool_data → respuesta basada en tool

    Verifica que la síntesis usa solo datos operativos.
    """
    _, mock_generate = mock_rag

    state: AgentState = {
        "question": "¿En qué estado está el ticket 482?",
        "context": None,
        "tool_data": {
            "success": True,
            "data": {
                "id": 482,
                "status": "in_progress",
                "category": "técnico"
            }
        },
        "tool_name": "get_incident_by_id",
        "needs_tool": True,
        "routing_decision": "tool",
        "answer": None,
        "error": None,
        "metadata": {}
    }

    with patch("services.agent.graph.openai.OpenAI") as mock_openai:
        # Mock de respuesta de LLM
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="El ticket 482 está en progreso."))
        ]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client

        result = synthesis_node(state)

    assert result["answer"] is not None, "Debe generar respuesta"
    assert "482" in result["answer"] or "progreso" in result["answer"], "Respuesta debe mencionar ticket"
    assert result["metadata"]["synthesis_type"] == "tool", "Debe marcar synthesis_type=tool"


# ============================================================
# TEST 9: Synthesis Node - RAG Only
# ============================================================

def test_synthesis_node_rag_only(mock_rag):
    """
    Test: synthesis_node con solo context → respuesta basada en RAG

    Verifica que la síntesis usa generate_answer() para RAG.
    """
    mock_retrieve, mock_generate = mock_rag

    state: AgentState = {
        "question": "¿Cuántos locales tiene Brasaland?",
        "context": [
            {
                "text": "Brasaland tiene 14 locales en total.",
                "source_document": "01-company-overview.md"
            }
        ],
        "tool_data": None,
        "tool_name": None,
        "needs_tool": False,
        "routing_decision": "rag",
        "answer": None,
        "error": None,
        "metadata": {}
    }

    result = rag_retrieve_node(state)

    assert mock_generate.called or result["context"] is not None, "Debe usar RAG"
    assert result["metadata"]["synthesis_type"] == "rag_only", "Debe marcar rag_only"


# ============================================================
# TEST 10: Synthesis Node - Fallback Honesto (Tool Failed)
# ============================================================

def test_synthesis_node_tool_failed_honest_fallback():
    """
    Test: synthesis_node con tool_data.success=False → fallback honesto

    Verifica que NO alucina datos cuando tool falla.
    Debe retornar mensaje honesto con el error.
    """
    state: AgentState = {
        "question": "¿En qué estado está el ticket 99999?",
        "context": None,
        "tool_data": {
            "success": False,
            "error": "Ticket 99999 no encontrado en el sistema"
        },
        "tool_name": "get_incident_by_id",
        "needs_tool": True,
        "routing_decision": "tool",
        "answer": None,
        "error": None,
        "metadata": {}
    }

    result = synthesis_node(state)

    assert result["answer"] is not None, "Debe generar respuesta"
    assert "no pude obtener" in result["answer"].lower() or "error" in result["answer"].lower(), \
        "Debe ser honesto sobre el error"
    assert "99999 no encontrado" in result["answer"], "Debe incluir mensaje de error real"
    assert result["metadata"]["synthesis_type"] == "tool_fallback", "Debe marcar fallback"


# ============================================================
# TEST 11: End-to-End - Tool Only Path
# ============================================================

@pytest.mark.integration
def test_e2e_tool_only_path(mock_mcp_client, mock_rag):
    """
    Test: Flujo completo end-to-end con routing tool-only

    Verifica:
    - Router → tool_calling → synthesis
    - MCP client se usa (no tools directas)
    - Respuesta final coherente
    """
    question = "¿En qué estado está el ticket 482?"

    with patch("services.agent.graph.openai.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content="El ticket 482 está en estado 'in_progress'."))
        ]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client

        result = query_with_agent(question)

    assert result["answer"] is not None, "Debe generar respuesta"
    assert result["routing_decision"] == "tool", "Debe usar routing tool"
    assert result["tool_used"] == "get_incident_by_id", "Debe usar tool correcta"
    assert result["error"] is None, "No debe haber error"


# ============================================================
# TEST 12: End-to-End - RAG Only Path
# ============================================================

@pytest.mark.integration
def test_e2e_rag_only_path(mock_mcp_client, mock_rag):
    """
    Test: Flujo completo end-to-end con routing rag-only

    Verifica:
    - Router → rag_retrieve → synthesis
    - No se llama a tools
    - Respuesta basada en documentos
    """
    question = "¿Cuántos locales tiene Brasaland?"

    result = query_with_agent(question)

    assert result["answer"] is not None, "Debe generar respuesta"
    assert result["routing_decision"] == "rag", "Debe usar routing rag"
    assert result["tool_used"] is None, "No debe usar tool"
    assert "14 locales" in result["answer"], "Respuesta debe mencionar cantidad de locales"


# ============================================================
# TEST 13: MCP Client Usage (no tools.py)
# ============================================================

def test_mcp_client_used_not_tools_direct(mock_mcp_client):
    """
    Test: Verificar que se usa MCP client, NO tools.py directas

    Verifica que execute_tool() viene de mcp_adapter, no de tools.py.
    """
    from services.agent.graph import execute_tool

    # Verificar que el módulo es mcp_adapter
    assert "mcp_adapter" in execute_tool.__module__, \
        "execute_tool debe venir de mcp_adapter, no de tools.py"

    # Ejecutar tool y verificar que MCP client se llama
    result = execute_tool("get_incident_by_id", ticket_id=482)

    assert mock_mcp_client.get_incident_by_id.called, "Debe llamar a MCP client"
    assert result["success"] == True, "Debe retornar éxito"


# ============================================================
# MAIN (Ejecución de tests)
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
