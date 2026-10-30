"""
Fase 3: Endpoint de API para Sistema RAG

Router FastAPI para consultas a la base de conocimiento de Brasaland.

Endpoints:
    POST /knowledge/query - Consulta RAG
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
import sys
from pathlib import Path

# Importar funciones RAG desde data/pipelines
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from data.pipelines.rag_query import query as rag_query
except ImportError:
    rag_query = None

# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/knowledge",
    tags=["Knowledge Base"],
    responses={404: {"description": "Not found"}},
)

# ============================================================
# SCHEMAS
# ============================================================

class QueryRequest(BaseModel):
    """Request body para consulta RAG"""
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Pregunta sobre la base de conocimiento de Brasaland",
        examples=["¿Cuántos locales tiene Brasaland?"]
    )

class QueryResponse(BaseModel):
    """Response body para consulta RAG"""
    answer: str = Field(
        ...,
        description="Respuesta generada por el sistema RAG"
    )
    question: str = Field(
        ...,
        description="Pregunta original del usuario"
    )

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    message: str
    qdrant_configured: bool
    openai_configured: bool

# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check del sistema RAG.

    Verifica que las dependencias estén configuradas.
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    qdrant_configured = bool(os.getenv("QDRANT_URL"))
    openai_configured = bool(os.getenv("OPENAI_API_KEY"))

    if not rag_query:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sistema RAG no disponible. Verificar dependencias."
        )

    if not qdrant_configured or not openai_configured:
        return HealthResponse(
            status="unhealthy",
            message="Configuración incompleta",
            qdrant_configured=qdrant_configured,
            openai_configured=openai_configured
        )

    return HealthResponse(
        status="healthy",
        message="Sistema RAG operativo",
        qdrant_configured=qdrant_configured,
        openai_configured=openai_configured
    )


@router.post("/query", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def query_knowledge_base(request: QueryRequest):
    """
    Consulta RAG end-to-end.

    Flujo:
    1. Recibe pregunta del usuario
    2. Llama a query() desde data/pipelines/rag_query.py
    3. Devuelve respuesta generada

    CRÍTICO: Nunca devuelve chunks crudos, solo respuestas generadas por LLM.

    Args:
        request: QueryRequest con pregunta

    Returns:
        QueryResponse con respuesta generada

    Raises:
        HTTPException 503: Si el sistema RAG no está disponible
        HTTPException 500: Si hay error durante la consulta
    """
    if not rag_query:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sistema RAG no disponible. Verificar instalación de dependencias."
        )

    try:
        # Ejecutar consulta RAG
        answer = rag_query(request.question)

        return QueryResponse(
            answer=answer,
            question=request.question
        )

    except ValueError as e:
        # Errores de configuración (API keys, etc.)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error de configuración: {str(e)}"
        )

    except Exception as e:
        # Errores generales
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante consulta RAG: {str(e)}"
        )
