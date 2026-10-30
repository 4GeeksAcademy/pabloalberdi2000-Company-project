"""
SQLModel Models - RFP Intake System

Modelos de base de datos para el sistema de recepción y análisis de RFPs.

CRÍTICO:
- Persistencia en PostgreSQL/Supabase (NO TinyDB, NO JSON planos)
- Estados del ticket: analizando, descartado, analisis_completo
- Métricas de legibilidad (Flesch-Kincaid, Gunning Fog)
- key_aspects estructurados por departamento en JSON
"""

from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================
# ENUMS
# ============================================================

class RFPTicketStatus(str, Enum):
    """Estados del ciclo de vida del ticket de RFP"""
    # Parte 1: Recepción y Análisis
    ANALIZANDO = "analizando"              # En procesamiento asíncrono
    DESCARTADO = "descartado"              # No es RFP válida
    ANALISIS_COMPLETO = "analisis_completo"  # Pipeline Parte 1 completo
    ERROR = "error"                        # Falló el procesamiento

    # Parte 2: Generación y Evaluación
    GENERANDO_BORRADOR = "generando_borrador"        # Generadores en acción
    EN_EVALUACION = "en_evaluacion"                  # Evaluadores analizando
    NEEDS_HUMAN_REVIEW = "needs_human_review"        # Requiere revisión manual
    LISTO_PARA_CONSOLIDACION = "listo_para_consolidacion"  # Handoff a Parte 3

    # Parte 3: Aprobación y Consolidación
    ESPERANDO_APROBACION = "esperando_aprobacion"    # HITL por departamento
    TERMINADO = "terminado"                          # Documento final generado


class DepartmentType(str, Enum):
    """
    Departamentos de Brasaland según company-BRIEFING.md

    De projectbrief.md:
    - Operaciones (Felipe Guerrero)
    - Compras (Lucía Fernández)
    - Marketing (Camila Ospina)
    - RRHH (Ashley Turner)
    - Formación (Jake Morrison)
    - Tecnología (Nicolás Park)
    - Dirección (Mariana Restrepo)
    """
    OPERACIONES = "operaciones"
    COMPRAS = "compras"
    MARKETING = "marketing"
    RRHH = "rrhh"
    FORMACION = "formacion"
    TECNOLOGIA = "tecnologia"
    DIRECCION = "direccion"
    ESPECIALES = "especiales"  # Requerimientos fuera de catálogo


# ============================================================
# MODELS
# ============================================================

class RFPTicket(SQLModel, table=True):
    """
    Ticket principal de RFP (Request for Proposal).

    Tabla: rfp_tickets

    Ciclo de vida:
    1. Upload → analizando (202 Accepted)
    2. Clasificación → analizando | descartado
    3. Pipeline → analisis_completo | error
    """
    __tablename__ = "rfp_tickets"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Identificación
    filename: str = Field(description="Nombre original del archivo PDF")
    file_path: str = Field(description="Ruta del PDF en data/raw/rfp_pdfs/")
    markdown_path: Optional[str] = Field(default=None, description="Ruta del Markdown convertido")

    # Estado y trazabilidad
    status: RFPTicketStatus = Field(default=RFPTicketStatus.ANALIZANDO)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Resultado del clasificador
    is_valid_rfp: Optional[bool] = Field(default=None, description="¿Es RFP válida?")
    classifier_confidence: Optional[float] = Field(default=None, description="Confianza del clasificador (0-1)")
    rejection_reason: Optional[str] = Field(default=None, description="Razón de descarte (si aplica)")

    # Logs de procesamiento
    processing_log: Optional[str] = Field(default=None, description="Log del pipeline asíncrono")
    error_message: Optional[str] = Field(default=None, description="Mensaje de error (si status=error)")

    # Relaciones
    metadata: Optional["RFPMetadata"] = Relationship(back_populates="ticket")
    sections: List["DepartmentSection"] = Relationship(back_populates="ticket")


class RFPMetadata(SQLModel, table=True):
    """
    Metadatos de negocio extraídos de la RFP.

    Tabla: rfp_metadata

    Incluye:
    - Datos del cliente (nombre, contacto)
    - Plazos y presupuesto
    - Métricas de legibilidad (py-readability-metrics)
    """
    __tablename__ = "rfp_metadata"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="rfp_tickets.id", unique=True)

    # Datos del cliente
    client_name: Optional[str] = Field(default=None, description="Nombre del cliente solicitante")
    client_contact: Optional[str] = Field(default=None, description="Email o teléfono de contacto")

    # Información de la RFP
    project_title: Optional[str] = Field(default=None, description="Título del proyecto")
    submission_deadline: Optional[datetime] = Field(default=None, description="Fecha límite de entrega")
    budget_range: Optional[str] = Field(default=None, description="Rango presupuestario estimado")

    # Métricas de legibilidad (py-readability-metrics)
    flesch_reading_ease: Optional[float] = Field(default=None, description="Flesch Reading Ease (0-100)")
    flesch_kincaid_grade: Optional[float] = Field(default=None, description="Flesch-Kincaid Grade Level")
    gunning_fog: Optional[float] = Field(default=None, description="Gunning Fog Index")
    smog_index: Optional[float] = Field(default=None, description="SMOG Index")

    # Estimaciones de costo
    estimated_tokens: Optional[int] = Field(default=None, description="Tokens estimados del documento")
    estimated_cost_usd: Optional[float] = Field(default=None, description="Costo estimado de procesamiento")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relación inversa
    ticket: Optional[RFPTicket] = Relationship(back_populates="metadata")


class DepartmentSection(SQLModel, table=True):
    """
    Sección analizada por un departamento específico.

    Tabla: department_sections

    Cada worker de departamento procesa su sección y extrae key_aspects.
    """
    __tablename__ = "department_sections"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="rfp_tickets.id")

    # Identificación del departamento
    department: DepartmentType = Field(description="Departamento responsable")
    section_title: Optional[str] = Field(default=None, description="Título de la sección en RFP")

    # Contenido procesado
    extracted_text: Optional[str] = Field(default=None, description="Texto relevante extraído")

    # Aspectos clave estructurados (JSON)
    key_aspects: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Aspectos clave estructurados por el worker"
    )
    # Estructura sugerida de key_aspects:
    # {
    #   "requirements": ["req1", "req2"],
    #   "constraints": ["constraint1"],
    #   "missing_data": ["dato faltante X"],
    #   "estimated_effort": "alto/medio/bajo",
    #   "blockers": ["bloqueador crítico Y"],
    #   "notes": "Observaciones adicionales"
    # }

    # Procesamiento
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    worker_confidence: Optional[float] = Field(default=None, description="Confianza del worker (0-1)")

    # Relación inversa
    ticket: Optional[RFPTicket] = Relationship(back_populates="sections")


# ============================================================
# SYNTHESIS RESULT (Resultado consolidado)
# ============================================================

class RFPSynthesis(SQLModel, table=True):
    """
    Resultado consolidado del análisis (síntesis de todos los workers).

    Tabla: rfp_synthesis

    Generado por el Synthesizer Agent tras consolidar todos los workers.
    """
    __tablename__ = "rfp_synthesis"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="rfp_tickets.id", unique=True)

    # Resumen ejecutivo para Ventas
    executive_summary: str = Field(description="Resumen ejecutivo del análisis")

    # Departamentos involucrados
    involved_departments: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Lista de departamentos que deben participar"
    )

    # Dependencias críticas detectadas
    critical_dependencies: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Dependencias críticas entre departamentos"
    )

    # Riesgos identificados
    identified_risks: List[Dict[str, str]] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Riesgos detectados con severidad"
    )
    # Estructura: [{"risk": "...", "severity": "alta/media/baja", "mitigation": "..."}]

    # Datos faltantes bloqueantes
    missing_critical_data: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Datos faltantes que bloquean la cotización"
    )

    # Workstreams recomendados
    recommended_workstreams: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Estructura de workstreams paralelos por departamento"
    )
    # Estructura: {
    #   "operaciones": {"lead": "Felipe Guerrero", "tasks": [...], "deadline": "..."},
    #   "tecnologia": {...}
    # }

    # Metadata de síntesis
    synthesis_confidence: float = Field(default=0.0, description="Confianza global del análisis")
    synthesized_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def create_rfp_ticket(
    filename: str,
    file_path: str,
    markdown_path: Optional[str] = None
) -> RFPTicket:
    """
    Factory para crear ticket de RFP.

    Args:
        filename: Nombre original del PDF
        file_path: Ruta del PDF guardado
        markdown_path: Ruta del Markdown convertido (opcional)

    Returns:
        RFPTicket con estado inicial 'analizando'
    """
    return RFPTicket(
        filename=filename,
        file_path=file_path,
        markdown_path=markdown_path,
        status=RFPTicketStatus.ANALIZANDO,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


def update_ticket_status(
    ticket: RFPTicket,
    new_status: RFPTicketStatus,
    error_message: Optional[str] = None
) -> RFPTicket:
    """
    Actualiza estado del ticket.

    Args:
        ticket: Ticket a actualizar
        new_status: Nuevo estado
        error_message: Mensaje de error (si aplica)

    Returns:
        Ticket actualizado
    """
    ticket.status = new_status
    ticket.updated_at = datetime.utcnow()

    if error_message:
        ticket.error_message = error_message

    return ticket
