"""
Memory Manager - Gestión de Memoria Persistente con Qdrant

Interfaz para leer/escribir memoria del agente en colección separada de RAG.

CRÍTICO:
- Colección `agent_memory` (NUNCA `*_knowledge`)
- Búsqueda semántica con embeddings
- Deduplicación y consolidación
- Auditoría completa de propuestas
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from dotenv import load_dotenv
import openai
import structlog

# Agregar raíz al path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.agent.memory.schemas import (
    MemoryEntry,
    MemoryProposalSchema,
    ProposalAuditLog,
    MemoryCategory,
    ProposalStatus
)

load_dotenv()

logger = structlog.get_logger()

# ============================================================
# CONFIGURACIÓN
# ============================================================

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# Colecciones (separadas de RAG)
MEMORY_COLLECTION = "agent_memory"  # ❌ NUNCA usar *_knowledge
AUDIT_COLLECTION = "memory_proposals_audit"

# ============================================================
# MEMORY MANAGER
# ============================================================

class MemoryManager:
    """
    Gestor de memoria persistente del agente.

    Responsabilidades:
    - Almacenar memorias aprobadas en Qdrant
    - Búsqueda semántica de memorias relevantes
    - Auditoría de propuestas (aprobadas, rechazadas, descartadas)
    - Deduplicación y consolidación
    """

    def __init__(
        self,
        qdrant_host: str = QDRANT_HOST,
        qdrant_port: int = QDRANT_PORT,
        openai_api_key: str = OPENAI_API_KEY
    ):
        """
        Inicializa Memory Manager.

        Args:
            qdrant_host: Host de Qdrant
            qdrant_port: Puerto de Qdrant
            openai_api_key: API key de OpenAI
        """
        self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.openai_client = openai.OpenAI(api_key=openai_api_key)

        # Inicializar colecciones si no existen
        self._ensure_collections()

        logger.info("memory_manager_initialized",
                   memory_collection=MEMORY_COLLECTION,
                   audit_collection=AUDIT_COLLECTION)

    def _ensure_collections(self):
        """Crea colecciones de memoria si no existen"""
        collections = [c.name for c in self.client.get_collections().collections]

        # Colección de memorias
        if MEMORY_COLLECTION not in collections:
            self.client.create_collection(
                collection_name=MEMORY_COLLECTION,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE
                )
            )
            logger.info("memory_collection_created", collection=MEMORY_COLLECTION)

        # Colección de auditoría (no necesita vectores, solo metadata)
        if AUDIT_COLLECTION not in collections:
            self.client.create_collection(
                collection_name=AUDIT_COLLECTION,
                vectors_config=VectorParams(
                    size=1,  # Dummy vector (no se usa para búsqueda)
                    distance=Distance.COSINE
                )
            )
            logger.info("audit_collection_created", collection=AUDIT_COLLECTION)

    def _embed(self, text: str) -> List[float]:
        """
        Genera embedding de texto.

        Args:
            text: Texto a embedder

        Returns:
            Vector de embedding
        """
        response = self.openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding

    def save_memory(
        self,
        memory_entry: MemoryEntry
    ) -> str:
        """
        Persiste una memoria aprobada en Qdrant.

        Args:
            memory_entry: Entrada de memoria validada y aprobada

        Returns:
            ID de la memoria persistida
        """
        # Generar embedding del contenido
        embedding = self._embed(memory_entry.content)

        # Preparar payload
        payload = {
            "id": memory_entry.id,
            "content": memory_entry.content,
            "category": memory_entry.category,
            "context": memory_entry.context,
            "created_at": memory_entry.created_at.isoformat(),
            "approved_by": memory_entry.approved_by,
            "proposal_id": memory_entry.proposal_id,
            "metadata": memory_entry.metadata
        }

        # Persistir en Qdrant
        point = PointStruct(
            id=memory_entry.id,
            vector=embedding,
            payload=payload
        )

        self.client.upsert(
            collection_name=MEMORY_COLLECTION,
            points=[point]
        )

        logger.info("memory_saved",
                   memory_id=memory_entry.id,
                   category=memory_entry.category,
                   approved_by=memory_entry.approved_by)

        return memory_entry.id

    def read_memories(
        self,
        query: str,
        category: Optional[MemoryCategory] = None,
        limit: int = 5,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Búsqueda semántica de memorias relevantes.

        Args:
            query: Query de búsqueda
            category: Filtrar por categoría (opcional)
            limit: Máximo de resultados
            min_score: Umbral de similitud mínima

        Returns:
            Lista de memorias relevantes
        """
        # Generar embedding de query
        query_embedding = self._embed(query)

        # Filtro por categoría (si se especifica)
        query_filter = None
        if category:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="category",
                        match=MatchValue(value=category)
                    )
                ]
            )

        # Búsqueda vectorial
        search_result = self.client.search(
            collection_name=MEMORY_COLLECTION,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=min_score,
            query_filter=query_filter
        )

        # Formatear resultados
        memories = []
        for scored_point in search_result:
            memory = {
                "id": scored_point.payload["id"],
                "content": scored_point.payload["content"],
                "category": scored_point.payload["category"],
                "context": scored_point.payload.get("context"),
                "created_at": scored_point.payload["created_at"],
                "score": scored_point.score
            }
            memories.append(memory)

        logger.info("memories_retrieved",
                   query=query[:50],
                   count=len(memories),
                   categories=[m["category"] for m in memories])

        return memories

    def delete_memory(self, memory_id: str) -> bool:
        """
        Elimina una memoria (consolidación/limpieza).

        Args:
            memory_id: ID de la memoria a eliminar

        Returns:
            True si se eliminó exitosamente
        """
        self.client.delete(
            collection_name=MEMORY_COLLECTION,
            points_selector=[memory_id]
        )

        logger.info("memory_deleted", memory_id=memory_id)
        return True

    def search_similar(
        self,
        content: str,
        threshold: float = 0.9
    ) -> List[Dict[str, Any]]:
        """
        Busca memorias muy similares (para deduplicación).

        Args:
            content: Contenido a comparar
            threshold: Umbral de similitud alta (default 0.9)

        Returns:
            Lista de memorias duplicadas
        """
        return self.read_memories(
            query=content,
            limit=3,
            min_score=threshold
        )

    def log_proposal(
        self,
        proposal_log: ProposalAuditLog
    ) -> str:
        """
        Registra propuesta en auditoría (trazabilidad).

        Args:
            proposal_log: Log de propuesta con decisión

        Returns:
            ID del log de auditoría
        """
        # Payload de auditoría (sin embedding relevante)
        payload = {
            "id": proposal_log.id,
            "proposal_content": proposal_log.proposal.content,
            "proposal_category": proposal_log.proposal.category,
            "proposal_reason": proposal_log.proposal.reason,
            "status": proposal_log.status,
            "proposed_at": proposal_log.proposed_at.isoformat(),
            "decided_at": proposal_log.decided_at.isoformat() if proposal_log.decided_at else None,
            "user_response": proposal_log.user_response,
            "decision_reason": proposal_log.decision_reason,
            "conversation_id": proposal_log.conversation_id,
            "agent_version": proposal_log.agent_version
        }

        # Persistir en colección de auditoría
        point = PointStruct(
            id=proposal_log.id,
            vector=[0.0],  # Dummy vector (no se busca semánticamente)
            payload=payload
        )

        self.client.upsert(
            collection_name=AUDIT_COLLECTION,
            points=[point]
        )

        logger.info("proposal_logged",
                   proposal_id=proposal_log.id,
                   status=proposal_log.status,
                   conversation_id=proposal_log.conversation_id)

        return proposal_log.id

    def get_pending_proposals(
        self,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Obtiene propuestas pendientes de una conversación.

        Args:
            conversation_id: ID de la conversación

        Returns:
            Lista de propuestas pendientes
        """
        # Buscar por filtro de conversación y status pending
        search_result = self.client.scroll(
            collection_name=AUDIT_COLLECTION,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="conversation_id",
                        match=MatchValue(value=conversation_id)
                    ),
                    FieldCondition(
                        key="status",
                        match=MatchValue(value=ProposalStatus.PENDING)
                    )
                ]
            ),
            limit=10
        )

        proposals = []
        for point in search_result[0]:
            proposals.append(point.payload)

        return proposals

    def consolidate_memories(
        self,
        similarity_threshold: float = 0.95
    ) -> int:
        """
        Consolida memorias duplicadas o muy similares.

        Args:
            similarity_threshold: Umbral de similitud para considerar duplicado

        Returns:
            Número de memorias consolidadas
        """
        # Obtener todas las memorias
        all_memories = self.client.scroll(
            collection_name=MEMORY_COLLECTION,
            limit=1000  # Ajustar según volumen esperado
        )[0]

        consolidated_count = 0
        checked_ids = set()

        for memory_point in all_memories:
            memory_id = memory_point.payload["id"]

            if memory_id in checked_ids:
                continue

            # Buscar similares
            similar = self.search_similar(
                content=memory_point.payload["content"],
                threshold=similarity_threshold
            )

            # Si hay duplicados (excluyendo el mismo)
            duplicates = [m for m in similar if m["id"] != memory_id]

            if duplicates:
                # Mantener el más reciente, eliminar otros
                for dup in duplicates[:-1]:  # Mantener último
                    self.delete_memory(dup["id"])
                    checked_ids.add(dup["id"])
                    consolidated_count += 1

                checked_ids.add(memory_id)

        logger.info("memories_consolidated", count=consolidated_count)
        return consolidated_count


# ============================================================
# HELPERS PÚBLICOS
# ============================================================

def create_memory_entry(
    content: str,
    category: MemoryCategory,
    approved_by: str,
    proposal_id: str,
    context: Optional[str] = None
) -> MemoryEntry:
    """
    Factory para crear MemoryEntry.

    Args:
        content: Contenido de la memoria
        category: Categoría
        approved_by: Usuario que aprobó
        proposal_id: ID de la propuesta original
        context: Contexto adicional

    Returns:
        MemoryEntry listo para persistir
    """
    return MemoryEntry(
        id=str(uuid.uuid4()),
        content=content,
        category=category,
        context=context,
        created_at=datetime.utcnow(),
        approved_by=approved_by,
        proposal_id=proposal_id,
        metadata={}
    )


def create_proposal_audit_log(
    proposal: MemoryProposalSchema,
    status: ProposalStatus,
    conversation_id: str,
    user_response: Optional[str] = None,
    decision_reason: Optional[str] = None
) -> ProposalAuditLog:
    """
    Factory para crear ProposalAuditLog.

    Args:
        proposal: Propuesta original
        status: Estado de la decisión
        conversation_id: ID de la conversación
        user_response: Respuesta del usuario
        decision_reason: Razón de la decisión

    Returns:
        ProposalAuditLog listo para log
    """
    now = datetime.utcnow()

    return ProposalAuditLog(
        id=str(uuid.uuid4()),
        proposal=proposal,
        status=status,
        proposed_at=now,
        decided_at=now if status != ProposalStatus.PENDING else None,
        user_response=user_response,
        decision_reason=decision_reason,
        conversation_id=conversation_id,
        agent_version="1.0.0"  # TODO: Obtener de config
    )


# Singleton global (lazy initialization)
_memory_manager_instance = None

def get_memory_manager() -> MemoryManager:
    """
    Obtiene instancia singleton de MemoryManager.

    Returns:
        MemoryManager global
    """
    global _memory_manager_instance

    if _memory_manager_instance is None:
        _memory_manager_instance = MemoryManager()

    return _memory_manager_instance
