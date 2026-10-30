"""
Endpoint de API para Sistema RAG con LangGraph

Router FastAPI que expone el flujo RAG modelado como grafo de estados.

Endpoints:
    POST /knowledge-graph/query - Consulta RAG con trazabilidad de estados
    GET /knowledge-graph/structure - Estructura del grafo
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import sys
from pathlib import Path

# Importar grafo RAG desde data/pipelines
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from data.pipelines.rag_graph import query_with_graph, build_rag_graph
except ImportError:
    query_with_graph = None
    build_rag_graph = None

# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/knowledge-graph",
    tags=["Knowledge Base - Graph"],
    responses={404: {"description": "Not found"}},
)

# ============================================================
# SCHEMAS
# ============================================================

class GraphQueryRequest(BaseModel):
    """Request body para consulta RAG con grafo"""
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Pregunta sobre la base de conocimiento de Brasaland",
        examples=["¿Cuántos locales tiene Brasaland?"]
    )

class GraphQueryResponse(BaseModel):
    """Response body para consulta RAG con grafo (incluye metadata de traza)"""
    answer: str = Field(
        ...,
        description="Respuesta generada por el sistema RAG"
    )
    question: str = Field(
        ...,
        description="Pregunta original del usuario"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata de observabilidad (chunks recuperados, scores, etc.)"
    )
    error: Optional[str] = Field(
        None,
        description="Mensaje de error si ocurrió alguno"
    )

class GraphStructureResponse(BaseModel):
    """Response con estructura del grafo"""
    nodes: list[str]
    edges: list[Dict[str, str]]
    description: str

# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/health")
async def health_check():
    """
    Health check del sistema RAG Graph.
    """
    if not query_with_graph or not build_rag_graph:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sistema RAG Graph no disponible. Verificar instalación de LangGraph."
        )

    return {
        "status": "healthy",
        "message": "Sistema RAG Graph operativo",
        "langgraph_available": True
    }


@router.post("/query", response_model=GraphQueryResponse, status_code=status.HTTP_200_OK)
async def query_knowledge_base_graph(request: GraphQueryRequest):
    """
    Consulta RAG con grafo de estados explícito.

    Ventajas sobre /knowledge/query:
    - Trazabilidad completa de decisiones
    - Metadata de observabilidad granular
    - Auditoría de transiciones de estado
    - Base para futuras capacidades (re-ranking, routing)

    Flujo:
    1. Recibe pregunta del usuario
    2. Ejecuta grafo LangGraph (retrieve → router → generate/no_context)
    3. Devuelve respuesta + metadata de traza

    Args:
        request: GraphQueryRequest con pregunta

    Returns:
        GraphQueryResponse con respuesta, metadata y traza

    Raises:
        HTTPException 503: Si LangGraph no está disponible
        HTTPException 500: Si hay error durante la consulta
    """
    if not query_with_graph:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sistema RAG Graph no disponible. Verificar instalación de LangGraph."
        )

    try:
        # Ejecutar consulta con grafo
        result = query_with_graph(request.question)

        return GraphQueryResponse(
            answer=result["answer"],
            question=result["question"],
            metadata=result.get("metadata", {}),
            error=result.get("error")
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
            detail=f"Error durante consulta RAG Graph: {str(e)}"
        )


@router.get("/structure", response_model=GraphStructureResponse)
async def get_graph_structure():
    """
    Obtiene la estructura del grafo de estados.

    Útil para:
    - Visualización en UI
    - Debugging
    - Documentación automática

    Returns:
        Estructura del grafo con nodos y edges
    """
    if not build_rag_graph:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sistema RAG Graph no disponible."
        )

    return GraphStructureResponse(
        nodes=[
            "retrieve",
            "generate",
            "no_context",
            "error"
        ],
        edges=[
            {"from": "START", "to": "retrieve"},
            {"from": "retrieve", "to": "generate", "condition": "context_not_empty"},
            {"from": "retrieve", "to": "no_context", "condition": "context_empty"},
            {"from": "retrieve", "to": "error", "condition": "error_occurred"},
            {"from": "generate", "to": "END"},
            {"from": "no_context", "to": "END"},
            {"from": "error", "to": "END"}
        ],
        description=(
            "Grafo de estados para flujo RAG:\n"
            "1. retrieve: Recupera chunks relevantes\n"
            "2. Router: Decide transición según contexto\n"
            "3. generate: Genera respuesta con LLM (si hay contexto)\n"
            "4. no_context: Respuesta honesta (si no hay contexto)\n"
            "5. error: Manejo de errores"
        )
    )
