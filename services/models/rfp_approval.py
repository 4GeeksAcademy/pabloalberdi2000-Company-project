"""
RFP Approval Models - Parte 3

Modelos para Human-in-the-Loop, aprobaciones departamentales,
arbitraje de conflictos y documento final consolidado.
"""

from sqlmodel import SQLModel, Field, Column, Enum as SQLEnum, JSON
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum as PyEnum


# ============================================================
# ENUMS
# ============================================================

class ApprovalStatus(str, PyEnum):
    """Estados de aprobación por departamento"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class ConflictSeverity(str, PyEnum):
    """Severidad de conflictos entre departamentos"""
    LOW = "low"  # Conflicto menor, no bloqueante
    MEDIUM = "medium"  # Requiere atención, puede proceder con nota
    HIGH = "high"  # Bloqueante, requiere arbitraje inmediato
    CRITICAL = "critical"  # Deadlock total, requiere arbitraje de CEO


class HumanApprovalDecision(str, PyEnum):
    """Decisión humana al reanudar desde checkpoint"""
    APPROVE = "aprobar"
    REJECT = "rechazar"
    REQUEST_CHANGES = "solicitar_cambios"


class ArbitrationDecision(str, PyEnum):
    """Decisión de arbitraje sobre conflictos"""
    APPROVE_VERSION_A = "aprobar_version_a"
    APPROVE_VERSION_B = "aprobar_version_b"
    MERGE_BOTH = "merge_both"
    REQUEST_REWRITE = "request_rewrite"
    ESCALATE_TO_CEO = "escalate_to_ceo"


# ============================================================
# TABLA: DEPARTMENT_APPROVAL
# ============================================================

class DepartmentApproval(SQLModel, table=True):
    """
    Tabla de aprobaciones por departamento (Parte 3)

    Registra cada interrupción HITL y la decisión humana asociada.
    """
    __tablename__ = "department_approvals"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="rfp_tickets.id", index=True)
    department: str = Field(index=True)  # DepartmentType como string

    # Referencia a borrador
    draft_section_id: int = Field(foreign_key="draft_sections.id")

    # Estado de aprobación
    status: str = Field(
        sa_column=Column(
            SQLEnum(ApprovalStatus, native_enum=False),
            nullable=False,
            default=ApprovalStatus.PENDING.value
        )
    )

    # Responsable humano (según company-BRIEFING.md)
    reviewer_name: str  # ej: "Felipe Guerrero", "Nicolás Park"
    reviewer_role: str  # ej: "Director Operaciones", "CTO"

    # Checkpoint metadata
    checkpoint_thread_id: str  # rfp-{ticket_id}:{department}
    interrupted_at: Optional[datetime] = None
    resumed_at: Optional[datetime] = None

    # Decisión humana
    human_decision: Optional[str] = Field(
        default=None,
        sa_column=Column(
            SQLEnum(HumanApprovalDecision, native_enum=False),
            nullable=True
        )
    )
    human_feedback: Optional[str] = None  # Comentarios del aprobador

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": 123,
                "department": "operaciones",
                "draft_section_id": 456,
                "status": "pending",
                "reviewer_name": "Felipe Guerrero",
                "reviewer_role": "Director Operaciones",
                "checkpoint_thread_id": "rfp-123:operaciones",
                "human_decision": None,
                "human_feedback": None
            }
        }


# ============================================================
# TABLA: CONFLICT_RECORD
# ============================================================

class ConflictRecord(SQLModel, table=True):
    """
    Registro de conflictos entre departamentos

    Detectados por Conflict Detector Node cuando hay desacuerdos
    en plazos, costos o dependencias.
    """
    __tablename__ = "conflict_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="rfp_tickets.id", index=True)

    # Departamentos involucrados
    department_a: str
    department_b: str

    # Tipo de conflicto
    conflict_type: str  # "deadline", "budget", "dependency", "scope"
    severity: str = Field(
        sa_column=Column(
            SQLEnum(ConflictSeverity, native_enum=False),
            nullable=False
        )
    )

    # Detalles del conflicto
    conflict_description: str
    department_a_position: str  # Postura del departamento A
    department_b_position: str  # Postura del departamento B

    # Arbitraje
    requires_arbitration: bool = True
    arbitrator_name: Optional[str] = None  # "Mariana Restrepo" si severity=CRITICAL
    arbitration_decision: Optional[str] = Field(
        default=None,
        sa_column=Column(
            SQLEnum(ArbitrationDecision, native_enum=False),
            nullable=True
        )
    )
    arbitration_rationale: Optional[str] = None

    # Estado
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": 123,
                "department_a": "tecnologia",
                "department_b": "operaciones",
                "conflict_type": "deadline",
                "severity": "high",
                "conflict_description": "Tecnología estima 90 días, Operaciones requiere 60 días",
                "department_a_position": "90 días con stack Next.js + FastAPI",
                "department_b_position": "60 días según deadline RFP original",
                "requires_arbitration": True,
                "is_resolved": False
            }
        }


# ============================================================
# TABLA: FINAL_DOCUMENT
# ============================================================

class FinalDocument(SQLModel, table=True):
    """
    Documento final consolidado (Parte 3 output)

    Generado por Ultimate Document Synthesizer después de todas las
    aprobaciones y resolución de conflictos.
    """
    __tablename__ = "final_documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="rfp_tickets.id", unique=True, index=True)

    # Contenido consolidado
    executive_summary: str  # Resumen ejecutivo (1 página)
    full_proposal_markdown: str  # Propuesta completa en Markdown
    full_proposal_html: Optional[str] = None  # HTML renderizado

    # Secciones aprobadas por departamento
    approved_sections: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    # {
    #   "operaciones": {"technical": "...", "economic": "...", "approved_by": "Felipe Guerrero"},
    #   "tecnologia": {...}
    # }

    # Metadatos financieros consolidados
    total_estimated_cost_usd: Optional[float] = None
    total_person_days: Optional[int] = None
    estimated_delivery_date: Optional[str] = None  # ISO 8601

    # Control de versiones
    version: int = 1
    is_latest: bool = True

    # Export metadata
    exported_to_pdf: bool = False
    pdf_path: Optional[str] = None
    exported_to_word: bool = False
    word_path: Optional[str] = None

    # Trazabilidad
    generated_by_agent: str = "Ultimate Document Synthesizer"
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Firma digital (opcional)
    signed_by: Optional[str] = None  # "Mariana Restrepo, CEO"
    signed_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": 123,
                "executive_summary": "Propuesta completa para dashboard operacional...",
                "full_proposal_markdown": "# Propuesta Técnica y Económica\n\n## 1. Operaciones...",
                "approved_sections": {
                    "operaciones": {
                        "technical": "Dashboard real-time...",
                        "economic": "40 person-days, USD $24,000",
                        "approved_by": "Felipe Guerrero"
                    }
                },
                "total_estimated_cost_usd": 120000.0,
                "total_person_days": 180,
                "estimated_delivery_date": "2027-03-15",
                "version": 1,
                "is_latest": True,
                "exported_to_pdf": True,
                "pdf_path": "data/exports/rfp_123_final_v1.pdf"
            }
        }


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def create_department_approval(
    ticket_id: int,
    department: str,
    draft_section_id: int,
    reviewer_name: str,
    reviewer_role: str
) -> DepartmentApproval:
    """Factory para crear registro de aprobación pendiente"""
    return DepartmentApproval(
        ticket_id=ticket_id,
        department=department,
        draft_section_id=draft_section_id,
        status=ApprovalStatus.PENDING,
        reviewer_name=reviewer_name,
        reviewer_role=reviewer_role,
        checkpoint_thread_id=f"rfp-{ticket_id}:{department}",
        interrupted_at=datetime.utcnow()
    )


def create_conflict_record(
    ticket_id: int,
    dept_a: str,
    dept_b: str,
    conflict_type: str,
    severity: ConflictSeverity,
    description: str,
    position_a: str,
    position_b: str
) -> ConflictRecord:
    """Factory para crear registro de conflicto"""
    return ConflictRecord(
        ticket_id=ticket_id,
        department_a=dept_a,
        department_b=dept_b,
        conflict_type=conflict_type,
        severity=severity.value,
        conflict_description=description,
        department_a_position=position_a,
        department_b_position=position_b,
        requires_arbitration=(severity in [ConflictSeverity.HIGH, ConflictSeverity.CRITICAL]),
        arbitrator_name="Mariana Restrepo" if severity == ConflictSeverity.CRITICAL else None
    )
