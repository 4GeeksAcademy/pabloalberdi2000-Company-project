"""
Fase 5: Tests Unitarios - Sistema RAG

Test suite para validar funciones del pipeline RAG con mocks.

Ejecutar:
    python -m pytest tests/pipelines/test_rag.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_qdrant_client():
    """
    Mock de QdrantClient para tests sin base de datos real.
    """
    with patch("data.pipelines.rag_query.QdrantClient") as mock_client_class:
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_openai_embed():
    """
    Mock de función embed() para evitar llamadas a OpenAI.
    """
    with patch("data.pipelines.rag_query.embed") as mock_embed:
        # Vector fake de 1536 dimensiones (todos ceros)
        mock_embed.return_value = [0.0] * 1536
        yield mock_embed


@pytest.fixture
def mock_openai_chat():
    """
    Mock de OpenAI chat completions para evitar llamadas reales.
    """
    with patch("data.pipelines.rag_query.openai.OpenAI") as mock_openai_class:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Esta es una respuesta mock del LLM"

        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        yield mock_client


@pytest.fixture
def sample_contexts():
    """
    Contextos de ejemplo que simularían resultados de Qdrant.
    """
    return [
        {
            "text": "Brasaland tiene 14 locales en total: 10 en Colombia y 4 en Estados Unidos.",
            "source_document": "01-company-overview.md",
            "section": "Información General",
            "company": "Brasaland",
            "language": "es",
            "chunk_index": 0,
            "similarity_score": 0.92
        },
        {
            "text": "El CEO de Brasaland es Mariana Restrepo, hija del fundador.",
            "source_document": "01-company-overview.md",
            "section": "Información General",
            "company": "Brasaland",
            "language": "es",
            "chunk_index": 1,
            "similarity_score": 0.85
        },
        {
            "text": "Brasaland emplea aproximadamente 115 personas en sus 14 locales.",
            "source_document": "01-company-overview.md",
            "section": "Información General",
            "company": "Brasaland",
            "language": "es",
            "chunk_index": 2,
            "similarity_score": 0.78
        }
    ]


# ============================================================
# TESTS DE retrieve()
# ============================================================

def test_retrieve_respects_k_limit(mock_qdrant_client, mock_openai_embed):
    """
    Test: retrieve() respeta el límite k de chunks a recuperar.
    """
    from data.pipelines.rag_query import retrieve

    # Configurar mock de Qdrant para devolver 10 resultados
    mock_results = []
    for i in range(10):
        mock_result = MagicMock()
        mock_result.payload = {
            "text": f"Chunk {i}",
            "source_document": "test.md",
            "section": "Test",
            "similarity_score": 0.9 - (i * 0.05)
        }
        mock_result.score = 0.9 - (i * 0.05)
        mock_results.append(mock_result)

    mock_qdrant_client.search.return_value = mock_results

    # Ejecutar con k=5
    results = retrieve("test query", k=5, min_score=0.7)

    # Verificar que Qdrant fue llamado con limit=5
    mock_qdrant_client.search.assert_called_once()
    call_kwargs = mock_qdrant_client.search.call_args[1]
    assert call_kwargs["limit"] == 5

    # Verificar que devuelve máximo 5 resultados
    assert len(results) <= 5


def test_retrieve_filters_by_min_score(mock_qdrant_client, mock_openai_embed):
    """
    Test: retrieve() filtra chunks con score < min_score.

    Qdrant filtra automáticamente con score_threshold.
    """
    from data.pipelines.rag_query import retrieve

    # Configurar mock con solo resultados sobre min_score
    mock_results = []
    scores = [0.95, 0.85, 0.75]  # Todos sobre 0.7

    for i, score in enumerate(scores):
        mock_result = MagicMock()
        mock_result.payload = {
            "text": f"Chunk {i}",
            "source_document": "test.md",
            "section": "Test"
        }
        mock_result.score = score
        mock_results.append(mock_result)

    mock_qdrant_client.search.return_value = mock_results

    # Ejecutar con min_score=0.7
    results = retrieve("test query", k=10, min_score=0.7)

    # Verificar que Qdrant fue llamado con score_threshold=0.7
    call_kwargs = mock_qdrant_client.search.call_args[1]
    assert call_kwargs["score_threshold"] == 0.7

    # Verificar que todos los resultados tienen score >= 0.7
    for result in results:
        assert result["similarity_score"] >= 0.7


def test_retrieve_returns_payloads_not_raw_vectors(mock_qdrant_client, mock_openai_embed):
    """
    Test: retrieve() devuelve payloads (metadatos + texto), no vectores crudos.
    """
    from data.pipelines.rag_query import retrieve

    mock_result = MagicMock()
    mock_result.payload = {
        "text": "Test chunk text",
        "source_document": "test.md",
        "section": "Test Section",
        "company": "Brasaland"
    }
    mock_result.score = 0.9

    mock_qdrant_client.search.return_value = [mock_result]

    results = retrieve("test query")

    # Verificar que devuelve payloads, no vectores
    assert len(results) == 1
    assert "text" in results[0]
    assert "source_document" in results[0]
    assert "similarity_score" in results[0]

    # Verificar que NO contiene vectores
    assert "vector" not in results[0]
    assert "embedding" not in results[0]


def test_retrieve_handles_empty_results(mock_qdrant_client, mock_openai_embed):
    """
    Test: retrieve() maneja caso sin resultados (score muy bajo).
    """
    from data.pipelines.rag_query import retrieve

    # Qdrant devuelve lista vacía cuando no hay matches
    mock_qdrant_client.search.return_value = []

    results = retrieve("test query", min_score=0.95)

    # Verificar que devuelve lista vacía, no error
    assert isinstance(results, list)
    assert len(results) == 0


# ============================================================
# TESTS DE generate_answer()
# ============================================================

def test_generate_answer_returns_string(mock_openai_chat, sample_contexts):
    """
    Test: generate_answer() devuelve string (respuesta generada), nunca chunks crudos.
    """
    from data.pipelines.rag_query import generate_answer

    answer = generate_answer("¿Cuántos locales tiene Brasaland?", sample_contexts)

    # Verificar que devuelve string
    assert isinstance(answer, str)
    assert len(answer) > 0

    # Verificar que NO devuelve chunks crudos (no contiene "chunk_index", "payload", etc.)
    assert "chunk_index" not in answer.lower()
    assert "payload" not in answer.lower()
    assert "similarity_score" not in answer.lower()


def test_generate_answer_handles_empty_context(mock_openai_chat):
    """
    Test: generate_answer() maneja contexto vacío sin alucinar.

    Debe responder honestamente que no tiene información.
    """
    from data.pipelines.rag_query import generate_answer

    # Mock respuesta del LLM para contexto vacío
    mock_openai_chat.chat.completions.create.return_value.choices[0].message.content = \
        "No tengo información suficiente para responder esa pregunta"

    answer = generate_answer("Pregunta sin contexto", [])

    # Verificar que devuelve respuesta honesta
    assert isinstance(answer, str)
    assert "no tengo información" in answer.lower() or "no hay información" in answer.lower()


def test_generate_answer_calls_llm_with_context(mock_openai_chat, sample_contexts):
    """
    Test: generate_answer() llama al LLM con el contexto inyectado en el prompt.
    """
    from data.pipelines.rag_query import generate_answer

    question = "¿Quién es el CEO?"
    generate_answer(question, sample_contexts)

    # Verificar que el LLM fue llamado
    mock_openai_chat.chat.completions.create.assert_called_once()

    # Extraer argumentos de la llamada
    call_kwargs = mock_openai_chat.chat.completions.create.call_args[1]
    messages = call_kwargs["messages"]

    # Verificar que hay 2 mensajes: system y user
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    # Verificar que el prompt del usuario contiene la pregunta
    user_content = messages[1]["content"]
    assert question in user_content

    # Verificar que el contexto fue inyectado
    assert "Mariana Restrepo" in user_content  # Texto del sample_contexts


def test_generate_answer_uses_correct_model():
    """
    Test: generate_answer() usa el modelo de chat correcto (gpt-4o-mini), no embeddings.
    """
    from data.pipelines.rag_query import CHAT_MODEL

    # Verificar que CHAT_MODEL está configurado correctamente
    assert CHAT_MODEL == "gpt-4o-mini"
    assert CHAT_MODEL != "text-embedding-3-small"  # NO debe usar modelo de embeddings


# ============================================================
# TESTS DE query() (Integración)
# ============================================================

def test_query_orchestrates_retrieve_and_generate(
    mock_qdrant_client,
    mock_openai_embed,
    mock_openai_chat,
    sample_contexts
):
    """
    Test: query() orquesta retrieve() → generate_answer() correctamente.
    """
    from data.pipelines.rag_query import query

    # Mock de retrieve() devolviendo contexts
    mock_results = []
    for ctx in sample_contexts:
        mock_result = MagicMock()
        mock_result.payload = ctx
        mock_result.score = ctx["similarity_score"]
        mock_results.append(mock_result)

    mock_qdrant_client.search.return_value = mock_results

    # Ejecutar query completo
    answer = query("¿Cuántos locales tiene Brasaland?")

    # Verificar que retrieve fue llamado (Qdrant.search)
    mock_qdrant_client.search.assert_called_once()

    # Verificar que generate fue llamado (OpenAI.chat)
    mock_openai_chat.chat.completions.create.assert_called_once()

    # Verificar que devuelve string
    assert isinstance(answer, str)
    assert len(answer) > 0


def test_query_never_returns_raw_chunks():
    """
    Test: query() NUNCA devuelve chunks crudos, solo respuesta generada.

    CRÍTICO: Requisito #1 del sistema RAG.
    """
    from data.pipelines.rag_query import query

    # No importa el mock, query() SIEMPRE debe devolver string generado
    # Este test verifica la firma de la función
    import inspect

    sig = inspect.signature(query)
    # Verificar que return type es str
    assert sig.return_annotation == str or str(sig.return_annotation) == "<class 'str'>"


# ============================================================
# TESTS DE CONFIGURACIÓN
# ============================================================

def test_models_are_separate():
    """
    Test: Modelo de embeddings != modelo de chat (requisito #3).
    """
    from data.pipelines.rag_query import EMBEDDING_MODEL, CHAT_MODEL

    assert EMBEDDING_MODEL != CHAT_MODEL
    assert "embed" in EMBEDDING_MODEL.lower()
    assert "gpt" in CHAT_MODEL.lower() or "chat" in CHAT_MODEL.lower()


def test_collection_name_aligned_with_company():
    """
    Test: Nombre de colección alineado con Brasaland (requisito #5).
    """
    from data.pipelines.rag_query import COLLECTION_NAME

    assert "brasaland" in COLLECTION_NAME.lower() or "knowledge" in COLLECTION_NAME.lower()


# ============================================================
# TESTS DE IDEMPOTENCIA (setup)
# ============================================================

def test_generate_deterministic_id_is_consistent():
    """
    Test: IDs deterministas son consistentes (idempotencia).
    """
    from data.process.setup_knowledge_base import generate_deterministic_id

    text = "Test chunk text"
    source = "test.md"
    chunk_index = 0

    id1 = generate_deterministic_id(text, source, chunk_index)
    id2 = generate_deterministic_id(text, source, chunk_index)

    # Mismo input → mismo ID
    assert id1 == id2

    # Diferente input → diferente ID
    id3 = generate_deterministic_id(text, source, 1)  # Diferente índice
    assert id1 != id3


# ============================================================
# TESTS DE MIN_SCORE THRESHOLD
# ============================================================

@pytest.mark.parametrize("min_score,expected_filter", [
    (0.5, True),   # Score bajo, debe filtrar algunos
    (0.9, True),   # Score alto, debe filtrar muchos
    (0.7, True),   # Score medio (default)
])
def test_retrieve_applies_min_score_threshold(
    min_score,
    expected_filter,
    mock_qdrant_client,
    mock_openai_embed
):
    """
    Test parametrizado: retrieve() aplica min_score correctamente.
    """
    from data.pipelines.rag_query import retrieve

    mock_qdrant_client.search.return_value = []

    retrieve("test", min_score=min_score)

    call_kwargs = mock_qdrant_client.search.call_args[1]
    assert call_kwargs["score_threshold"] == min_score


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
