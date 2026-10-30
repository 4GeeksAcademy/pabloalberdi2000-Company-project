"""
Fase 1: Preparación e Indexación Vectorial

Script de setup idempotente para indexar la base de conocimiento de Brasaland.

Funcionalidades:
- Carga de documentos desde docs/company-knowledge-base/
- Chunking semántico autocontenido
- Generación de embeddings con modelo dedicado
- Indexación en Qdrant con metadatos completos
- Idempotencia (recrear colección o IDs deterministas)

Ejecución:
    python data/process/setup_knowledge_base.py
"""

import hashlib
import os
from pathlib import Path
from typing import List, Dict, Any
import sys

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain.text_splitter import RecursiveCharacterTextSplitter
import openai

# Cargar variables de entorno
load_dotenv()

# ============================================================
# CONFIGURACIÓN
# ============================================================

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Nombre de colección basado en empresa (company-BRIEFING.md)
COLLECTION_NAME = "brasaland_knowledge_base"

# Modelo de embeddings (dedicado, independiente del modelo de chat)
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

# Parámetros de chunking
CHUNK_SIZE = 800          # Tokens aproximados
CHUNK_OVERLAP = 150       # Overlap para mantener contexto
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]  # Priorizar separación semántica

# Directorio de documentos
DOCS_DIR = PROJECT_ROOT / "docs" / "company-knowledge-base"

# ============================================================
# FUNCIONES DE UTILIDAD
# ============================================================

def generate_deterministic_id(text: str, source: str, chunk_index: int) -> str:
    """
    Genera ID determinista para idempotencia.

    Mismo texto + mismo source + mismo índice = mismo ID
    """
    unique_string = f"{source}_{chunk_index}_{text[:100]}"
    return hashlib.sha256(unique_string.encode()).hexdigest()


def load_documents() -> List[Dict[str, Any]]:
    """
    Carga todos los documentos .md desde docs/company-knowledge-base/.

    Returns:
        Lista de diccionarios con 'content' y 'metadata'
    """
    docs = []

    if not DOCS_DIR.exists():
        raise FileNotFoundError(f"Directorio no encontrado: {DOCS_DIR}")

    md_files = list(DOCS_DIR.glob("*.md"))

    if not md_files:
        raise ValueError(f"No se encontraron archivos .md en {DOCS_DIR}")

    print(f"📂 Encontrados {len(md_files)} documentos en {DOCS_DIR}")

    for file_path in sorted(md_files):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Metadatos básicos
        metadata = {
            "source_document": file_path.name,
            "company": "Brasaland",
            "language": "es",
            "file_path": str(file_path.relative_to(PROJECT_ROOT))
        }

        # Detectar sección del documento por nombre
        if "overview" in file_path.name.lower():
            metadata["section"] = "Información General"
        elif "department" in file_path.name.lower():
            metadata["section"] = "Departamentos y Operaciones"
        elif "technical" in file_path.name.lower():
            metadata["section"] = "Sistemas Técnicos"
        elif "procedure" in file_path.name.lower() or "polic" in file_path.name.lower():
            metadata["section"] = "Procedimientos y Políticas"
        else:
            metadata["section"] = "Documentación General"

        docs.append({
            "content": content,
            "metadata": metadata
        })

        print(f"  ✅ Cargado: {file_path.name} ({len(content)} caracteres)")

    return docs


def chunk_documents(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Divide documentos en chunks semánticos autocontenidos.

    Estrategia:
    - RecursiveCharacterTextSplitter con separadores semánticos
    - No partir oraciones ni reglas operativas por la mitad
    - Overlap para mantener contexto entre chunks

    Args:
        docs: Lista de documentos con content y metadata

    Returns:
        Lista de chunks con metadata extendido
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=SEPARATORS,
        is_separator_regex=False
    )

    all_chunks = []

    print(f"\n🔪 Iniciando chunking (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")

    for doc_idx, doc in enumerate(docs):
        content = doc["content"]
        metadata = doc["metadata"]

        # Dividir en chunks
        text_chunks = text_splitter.split_text(content)

        print(f"  📄 {metadata['source_document']}: {len(text_chunks)} chunks")

        # Crear chunks con metadata completo
        for chunk_idx, chunk_text in enumerate(text_chunks):
            chunk = {
                "text": chunk_text,
                "metadata": {
                    **metadata,  # Heredar metadata del documento
                    "chunk_index": chunk_idx,
                    "total_chunks": len(text_chunks),
                    "chunk_id": generate_deterministic_id(
                        chunk_text,
                        metadata["source_document"],
                        chunk_idx
                    )
                }
            }
            all_chunks.append(chunk)

    print(f"✅ Total de chunks generados: {len(all_chunks)}")
    return all_chunks


def embed(text: str) -> List[float]:
    """
    Genera embedding para un texto usando OpenAI.

    CRÍTICO: Esta función se reutiliza tanto en indexación como en consulta.

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


def setup() -> None:
    """
    Pipeline completo de setup idempotente:
    1. Cargar documentos
    2. Chunkear
    3. Generar embeddings
    4. Indexar en Qdrant (recrear colección)
    """
    print("🚀 Iniciando setup de base de conocimiento de Brasaland\n")
    print(f"📍 Configuración:")
    print(f"  - Qdrant URL: {QDRANT_URL}")
    print(f"  - Colección: {COLLECTION_NAME}")
    print(f"  - Modelo embeddings: {EMBEDDING_MODEL}")
    print(f"  - Dimensión: {EMBEDDING_DIMENSION}")
    print(f"  - Directorio docs: {DOCS_DIR}\n")

    # 1. Cargar documentos
    docs = load_documents()

    # 2. Chunkear
    chunks = chunk_documents(docs)

    # 3. Conectar a Qdrant
    print(f"\n🔌 Conectando a Qdrant en {QDRANT_URL}...")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    # 4. Recrear colección (idempotencia)
    print(f"♻️  Recreando colección '{COLLECTION_NAME}' (idempotencia)...")

    # Eliminar si existe
    collections = client.get_collections().collections
    if any(col.name == COLLECTION_NAME for col in collections):
        client.delete_collection(collection_name=COLLECTION_NAME)
        print(f"  ✅ Colección anterior eliminada")

    # Crear nueva colección
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EMBEDDING_DIMENSION,
            distance=Distance.COSINE  # Métrica de similitud
        )
    )
    print(f"  ✅ Colección '{COLLECTION_NAME}' creada")

    # 5. Generar embeddings e indexar
    print(f"\n🔢 Generando embeddings e indexando {len(chunks)} chunks...")

    points = []

    for idx, chunk in enumerate(chunks):
        # Generar embedding
        vector = embed(chunk["text"])

        # Crear punto para Qdrant
        point = PointStruct(
            id=chunk["metadata"]["chunk_id"],  # ID determinista
            vector=vector,
            payload={
                **chunk["metadata"],
                "text": chunk["text"]  # Texto completo para contexto en el prompt
            }
        )

        points.append(point)

        # Mostrar progreso cada 10 chunks
        if (idx + 1) % 10 == 0:
            print(f"  Progreso: {idx + 1}/{len(chunks)} chunks procesados...")

    # Insertar todos los puntos
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )

    print(f"✅ {len(points)} puntos indexados en Qdrant")

    # 6. Verificación
    collection_info = client.get_collection(collection_name=COLLECTION_NAME)
    print(f"\n📊 Verificación final:")
    print(f"  - Puntos en colección: {collection_info.points_count}")
    print(f"  - Dimensión de vectores: {collection_info.config.params.vectors.size}")
    print(f"  - Métrica de distancia: {collection_info.config.params.vectors.distance}")

    print(f"\n✅ Setup completado exitosamente!")
    print(f"🎯 Próximo paso: Ejecutar query desde data/pipelines/rag_query.py")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    try:
        setup()
    except Exception as e:
        print(f"\n❌ Error durante setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
