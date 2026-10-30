"""
Fase 2: Pipeline de Recuperación y Generación (RAG)

Pipeline modular para responder preguntas sobre la base de conocimiento de Brasaland.

Funcionalidades:
- retrieve(): Recuperación de chunks relevantes desde Qdrant
- generate_answer(): Generación de respuesta con LLM
- query(): Orquestación end-to-end (único punto de entrada público)

Ejecución:
    python data/pipelines/rag_query.py "¿Cuántos locales tiene Brasaland?"
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import openai

# Cargar variables de entorno
load_dotenv()

# ============================================================
# CONFIGURACIÓN
# ============================================================

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

COLLECTION_NAME = "brasaland_knowledge_base"

# Modelos (separados: embeddings != chat)
EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"  # Modelo de generación

# Parámetros de recuperación
DEFAULT_K = 5                # Número de chunks a recuperar
DEFAULT_MIN_SCORE = 0.7      # Umbral de similitud (0-1 para Cosine)

# ============================================================
# FUNCIONES CORE
# ============================================================

def embed(text: str) -> List[float]:
    """
    Genera embedding para texto usando OpenAI.

    CRÍTICO: Misma función que en setup_knowledge_base.py

    Args:
        text: Texto a embeber

    Returns:
        Vector de embeddings (1536 dimensiones)
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY no configurada en .env")

    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )

    return response.data[0].embedding


def retrieve(
    query: str,
    *,
    k: int = DEFAULT_K,
    min_score: float = DEFAULT_MIN_SCORE
) -> List[Dict[str, Any]]:
    """
    Recupera chunks relevantes desde Qdrant.

    Flujo:
    1. Embebe la consulta
    2. Busca los k vecinos más cercanos en Qdrant
    3. Filtra por similitud >= min_score
    4. Devuelve solo payloads (metadatos + texto)

    Args:
        query: Pregunta del usuario
        k: Número máximo de chunks a recuperar
        min_score: Umbral mínimo de similitud (0-1)

    Returns:
        Lista de payloads con metadatos y texto
    """
    # 1. Embebe query
    query_vector = embed(query)

    # 2. Conectar a Qdrant
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    # 3. Buscar vecinos más cercanos
    search_result = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=k,
        score_threshold=min_score  # Qdrant filtra por score automáticamente
    )

    # 4. Extraer payloads limpios
    contexts = []

    for scored_point in search_result:
        payload = scored_point.payload
        payload["similarity_score"] = scored_point.score  # Agregar score para debugging
        contexts.append(payload)

    print(f"🔍 Recuperados {len(contexts)} chunks (k={k}, min_score={min_score})")

    for idx, ctx in enumerate(contexts):
        print(f"  [{idx+1}] {ctx['source_document']} (score: {ctx['similarity_score']:.3f})")

    return contexts


def generate_answer(question: str, context: List[Dict[str, Any]]) -> str:
    """
    Genera respuesta usando LLM a partir del contexto recuperado.

    CRÍTICO: La respuesta siempre es generada por el LLM, nunca chunks crudos.

    Prompt engineering:
    - Inyecta contexto recuperado
    - Instruye tono y audiencia según Brasaland
    - Maneja caso de contexto vacío (no alucinar)

    Args:
        question: Pregunta del usuario
        context: Lista de chunks recuperados con metadatos

    Returns:
        Respuesta generada por el LLM
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY no configurada en .env")

    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    # Construir contexto para el prompt
    if not context:
        context_text = "No se encontró información relevante en la base de conocimiento."
    else:
        context_parts = []
        for idx, chunk in enumerate(context):
            source = chunk.get("source_document", "Desconocido")
            section = chunk.get("section", "")
            text = chunk.get("text", "")

            context_parts.append(f"[Fuente {idx+1}: {source} - {section}]\n{text}")

        context_text = "\n\n---\n\n".join(context_parts)

    # Prompt del sistema con tono y audiencia de Brasaland
    system_prompt = """Eres un asistente experto en Brasaland, una cadena de restaurantes de cocina a la brasa con 14 locales en Colombia y Estados Unidos.

Tu objetivo es responder preguntas sobre la empresa utilizando únicamente la información proporcionada en el contexto.

Directrices:
1. Responde SOLO con información del contexto proporcionado
2. Si no hay información relevante, responde honestamente: "No tengo información suficiente para responder esa pregunta"
3. NO inventes datos, números, nombres ni fechas
4. Usa un tono profesional pero cercano
5. Si la respuesta requiere datos de múltiples fuentes, sintetiza la información de forma coherente
6. Indica las fuentes cuando sea relevante (ej: "Según el documento de Operaciones...")
7. Si la pregunta tiene múltiples partes, responde cada una claramente

Audiencia: Empleados de Brasaland, gerentes, personal de operaciones y dirección ejecutiva."""

    # Prompt del usuario
    user_prompt = f"""Contexto de la base de conocimiento de Brasaland:

{context_text}

---

Pregunta del usuario: {question}

Por favor, responde basándote únicamente en el contexto proporcionado."""

    # Llamada al LLM
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,  # Baja temperatura para respuestas más deterministas
        max_tokens=500
    )

    answer = response.choices[0].message.content

    return answer


def query(question: str) -> str:
    """
    Punto de entrada público para RAG end-to-end.

    Orquesta retrieve() → generate_answer()

    Args:
        question: Pregunta del usuario

    Returns:
        Respuesta generada
    """
    print(f"\n❓ Pregunta: {question}\n")

    # 1. Recuperar contexto
    contexts = retrieve(question)

    # 2. Generar respuesta
    print(f"\n🤖 Generando respuesta...")
    answer = generate_answer(question, contexts)

    print(f"\n✅ Respuesta:\n{answer}\n")

    return answer


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    # Ejemplos de consultas
    sample_questions = [
        "¿Cuántos locales tiene Brasaland y en qué países?",
        "¿Quién es el CEO de Brasaland?",
        "¿Cuáles son los horarios de apertura en Colombia?",
        "¿Qué sistemas técnicos tiene implementados Brasaland Digital?",
        "¿Cuál es la política de vacaciones en Estados Unidos?"
    ]

    if len(sys.argv) > 1:
        # Consulta desde argumentos
        question = " ".join(sys.argv[1:])
        query(question)
    else:
        # Demo con preguntas de ejemplo
        print("🎯 Demo de sistema RAG - Brasaland Knowledge Base\n")
        print("=" * 70)

        for idx, q in enumerate(sample_questions, 1):
            print(f"\n[Pregunta {idx}/{len(sample_questions)}]")
            print("=" * 70)
            query(q)

            if idx < len(sample_questions):
                input("\nPresiona Enter para continuar...")
