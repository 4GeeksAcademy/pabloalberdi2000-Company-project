"""
Sistema de Memoria Persistente para Agente Brasaland

Módulo de memoria con Human-in-the-Loop y auto-evaluación.

CRÍTICO:
- Memoria separada de RAG (colección agent_memory)
- Propuestas requieren aprobación explícita
- Trazabilidad completa de decisiones
- Políticas negativas del briefing respetadas
"""

from .memory_manager import (
    MemoryManager,
    MemoryEntry,
    get_memory_manager,
    create_memory_entry,
    create_proposal_audit_log
)
from .schemas import (
    AgentStructuredResponse,
    MemoryProposalSchema,
    MemoryCategory,
    ProposalStatus
)
from .approval_handler import (
    process_approval,
    is_approval_response,
    discard_pending_proposals,
    classify_user_decision
)
from .maintenance import (
    get_memory_statistics,
    consolidate_duplicate_memories,
    expire_old_memories,
    run_daily_maintenance,
    get_memory_health_report
)

__all__ = [
    "MemoryManager",
    "MemoryEntry",
    "get_memory_manager",
    "create_memory_entry",
    "create_proposal_audit_log",
    "AgentStructuredResponse",
    "MemoryProposalSchema",
    "MemoryCategory",
    "ProposalStatus",
    "process_approval",
    "is_approval_response",
    "discard_pending_proposals",
    "classify_user_decision",
    "get_memory_statistics",
    "consolidate_duplicate_memories",
    "expire_old_memories",
    "run_daily_maintenance",
    "get_memory_health_report"
]
