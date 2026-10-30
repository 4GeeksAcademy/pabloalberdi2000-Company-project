"""
Test Suite - LangGraph RAG State Machine

Tests unitarios para validar el grafo de estados del sistema RAG.

Ejecutar:
    pytest tests/pipelines/test_rag_graph.py -v
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_retrieve():
    """Mock de retrieve() para tests sin Qdrant"""
    with patch("data.pipelines.rag_graph.retrieve") as mock:
        # Contexto válido por default
        mock.return_value = [
            {
                "text": "Brasaland tiene 14 locales en total.",
                "source_document": "01-company-overview.md",
                "section": "Información General",
                "similarity_score": 0.92
            }
        ]
        yield mock


@pytest.fixture
def mock_generate_answer():
    """Mock de generate_answer() para tests sin OpenAI"""
    with patch("data.pipelines.rag_graph.generate_answer") as mock:
        mock.return_value = "Esta es una respuesta mock del LLM"
        yield mock


@pytest.fixture
def sample_state():
    """Estado de ejemplo para tests"""
    return {
        "question": "¿Cuántos locales tiene Brasaland?",
        "context": None,
        "answer": None,
        "error": None,
        "metadata": {}
    }


# ============================================================
# TESTS DE NODOS
# ============================================================

def test_retrieve_node_success(mock_retrieve, sample_state):
    """
    Test: retrieve_node ejecuta retrieve() y actualiza estado correctamente.
    """
    from data.pipelines.rag_graph import retrieve_node

    result = retrieve_node(sample_state)

    # Verificar que retrieve fue llamado
    mock_retrieve.assert_called_once_with(sample_state["question"])

    # Verificar estado actualizado
    assert result["context"] is not None
    assert len(result["context"]) > 0
    assert result["error"] is None

    # Verificar metadata
    assert "num_chunks_retrieved" in result["metadata"]
    assert result["metadata"]["num_chunks_retrieved"] == 1


def test_retrieve_node_no_context(mock_retrieve, sample_state):
    """
    Test: retrieve_node maneja caso sin contexto (lista vacía).
    """
    from data.pipelines.rag_graph import retrieve_node

    # Mock devuelve lista vacía
    mock_retrieve.return_value = []

    result = retrieve_node(sample_state)

    # Verificar estado
    assert result["context"] == []
    assert result["error"] is None
    assert result["metadata"]["num_chunks_retrieved"] == 0


def test_retrieve_node_handles_error(mock_retrieve, sample_state):
    """
    Test: retrieve_node captura errores de retrieve().
    """
    from data.pipelines.rag_graph import retrieve_node

    # Mock lanza excepción
    mock_retrieve.side_effect = Exception("Qdrant connection failed")

    result = retrieve_node(sample_state)

    # Verificar manejo de error
    assert result["context"] is None
    assert result["error"] is not None
    assert "Error en retrieve" in result["error"]
    assert result["metadata"]["error_stage"] == "retrieve"


def test_generate_node_success(mock_generate_answer, sample_state):
    """
    Test: generate_node ejecuta generate_answer() correctamente.
    """
    from data.pipelines.rag_graph import generate_node

    # Agregar contexto al estado
    sample_state["context"] = [{"text": "test", "source_document": "test.md", "similarity_score": 0.9}]

    result = generate_node(sample_state)

    # Verificar que generate_answer fue llamado
    mock_generate_answer.assert_called_once_with(
        sample_state["question"],
        sample_state["context"]
    )

    # Verificar estado actualizado
    assert result["answer"] is not None
    assert result["error"] is None
    assert result["metadata"]["context_used"] is True


def test_generate_node_handles_error(mock_generate_answer, sample_state):
    """
    Test: generate_node captura errores de generate_answer().
    """
    from data.pipelines.rag_graph import generate_node

    sample_state["context"] = [{"text": "test"}]

    # Mock lanza excepción
    mock_generate_answer.side_effect = Exception("OpenAI API error")

    result = generate_node(sample_state)

    # Verificar manejo de error
    assert result["answer"] is None
    assert result["error"] is not None
    assert "Error en generate" in result["error"]


def test_handle_no_context_node(sample_state):
    """
    Test: handle_no_context_node genera respuesta honesta sin alucinar.
    """
    from data.pipelines.rag_graph import handle_no_context_node

    result = handle_no_context_node(sample_state)

    # Verificar respuesta honesta
    assert result["answer"] is not None
    assert "No tengo información suficiente" in result["answer"]
    assert result["context"] == []
    assert result["metadata"]["context_used"] is False


def test_error_node(sample_state):
    """
    Test: error_node maneja errores y genera respuesta apropiada.
    """
    from data.pipelines.rag_graph import error_node

    sample_state["error"] = "Test error message"

    result = error_node(sample_state)

    # Verificar manejo de error
    assert result["answer"] is not None
    assert "error al procesar" in result["answer"].lower()
    assert result["error"] == "Test error message"
    assert result["metadata"]["handled_error"] is True


# ============================================================
# TESTS DE ROUTING
# ============================================================

def test_should_generate_with_context():
    """
    Test: should_generate decide "generate" cuando hay contexto.
    """
    from data.pipelines.rag_graph import should_generate

    state = {
        "question": "test",
        "context": [{"text": "chunk"}],
        "answer": None,
        "error": None,
        "metadata": {}
    }

    decision = should_generate(state)
    assert decision == "generate"


def test_should_generate_without_context():
    """
    Test: should_generate decide "no_context" cuando no hay contexto.
    """
    from data.pipelines.rag_graph import should_generate

    state = {
        "question": "test",
        "context": [],
        "answer": None,
        "error": None,
        "metadata": {}
    }

    decision = should_generate(state)
    assert decision == "no_context"


def test_should_generate_with_error():
    """
    Test: should_generate decide "error" cuando hay error.
    """
    from data.pipelines.rag_graph import should_generate

    state = {
        "question": "test",
        "context": None,
        "answer": None,
        "error": "Test error",
        "metadata": {}
    }

    decision = should_generate(state)
    assert decision == "error"


# ============================================================
# TESTS DE INTEGRACIÓN (Grafo Completo)
# ============================================================

def test_graph_full_flow_with_context(mock_retrieve, mock_generate_answer):
    """
    Test: Flujo completo del grafo con contexto válido.

    Flujo: START → retrieve → generate → END
    """
    from data.pipelines.rag_graph import build_rag_graph

    graph = build_rag_graph()

    initial_state = {
        "question": "¿Cuántos locales tiene Brasaland?",
        "context": None,
        "answer": None,
        "error": None,
        "metadata": {}
    }

    final_state = graph.invoke(initial_state)

    # Verificar flujo ejecutado
    mock_retrieve.assert_called_once()
    mock_generate_answer.assert_called_once()

    # Verificar estado final
    assert final_state["answer"] is not None
    assert final_state["error"] is None
    assert final_state["context"] is not None


def test_graph_full_flow_without_context(mock_retrieve, mock_generate_answer):
    """
    Test: Flujo completo del grafo sin contexto.

    Flujo: START → retrieve → no_context → END
    """
    from data.pipelines.rag_graph import build_rag_graph

    # Mock devuelve lista vacía
    mock_retrieve.return_value = []

    graph = build_rag_graph()

    initial_state = {
        "question": "Pregunta sin respuesta",
        "context": None,
        "answer": None,
        "error": None,
        "metadata": {}
    }

    final_state = graph.invoke(initial_state)

    # Verificar flujo ejecutado
    mock_retrieve.assert_called_once()
    mock_generate_answer.assert_not_called()  # No debe llamar a generate

    # Verificar estado final (respuesta honesta)
    assert final_state["answer"] is not None
    assert "No tengo información" in final_state["answer"]
    assert final_state["metadata"]["context_used"] is False


def test_graph_handles_retrieve_error(mock_retrieve, mock_generate_answer):
    """
    Test: Grafo maneja errores en retrieve.

    Flujo: START → retrieve (error) → error → END
    """
    from data.pipelines.rag_graph import build_rag_graph

    # Mock lanza excepción
    mock_retrieve.side_effect = Exception("Connection error")

    graph = build_rag_graph()

    initial_state = {
        "question": "Test question",
        "context": None,
        "answer": None,
        "error": None,
        "metadata": {}
    }

    final_state = graph.invoke(initial_state)

    # Verificar que no llamó a generate
    mock_generate_answer.assert_not_called()

    # Verificar manejo de error
    assert final_state["answer"] is not None
    assert "error" in final_state["answer"].lower()


# ============================================================
# TESTS DE ESTADO (TypedDict)
# ============================================================

def test_state_schema_minimal():
    """
    Test: RAGState contiene únicamente campos mínimos necesarios.

    CRÍTICO: Prohibido arrastrar historial completo sin justificación.
    """
    from data.pipelines.rag_graph import RAGState

    # Verificar campos del schema
    required_fields = {"question", "context", "answer", "error", "metadata"}

    # RAGState es TypedDict, verificar anotaciones
    annotations = RAGState.__annotations__

    assert set(annotations.keys()) == required_fields

    # Verificar que NO hay campos adicionales innecesarios
    prohibited_fields = {"history", "messages", "full_conversation"}
    assert not any(field in annotations for field in prohibited_fields)


def test_state_metadata_accumulator():
    """
    Test: metadata usa Annotated con add para acumulación.
    """
    from data.pipelines.rag_graph import RAGState

    annotations = RAGState.__annotations__

    # Verificar que metadata está anotado
    assert "metadata" in annotations


# ============================================================
# TESTS DE REUTILIZACIÓN (No Duplicación)
# ============================================================

def test_graph_reuses_retrieve_function():
    """
    Test: Grafo reutiliza retrieve() de rag_query.py sin duplicar.
    """
    from data.pipelines.rag_graph import retrieve_node
    from data.pipelines.rag_query import retrieve

    # Verificar que retrieve_node importa retrieve
    import inspect
    source = inspect.getsource(retrieve_node)

    assert "retrieve(" in source
    assert "from data.pipelines.rag_query import retrieve" in open(
        PROJECT_ROOT / "data" / "pipelines" / "rag_graph.py"
    ).read()


def test_graph_reuses_generate_answer_function():
    """
    Test: Grafo reutiliza generate_answer() de rag_query.py sin duplicar.
    """
    from data.pipelines.rag_graph import generate_node

    import inspect
    source = inspect.getsource(generate_node)

    assert "generate_answer(" in source
    assert "from data.pipelines.rag_query import" in open(
        PROJECT_ROOT / "data" / "pipelines" / "rag_graph.py"
    ).read()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
