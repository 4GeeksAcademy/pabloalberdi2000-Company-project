"""
SQLModel Models - RFP Evaluation & Draft System (Parte 2)

CRÍTICO:
- EvaluationResult con 3 dimensiones (readability, relevance, compliance)
- DraftSection con iterations_count y feedback_history
- Estado del ticket: generando_borrador, en_evaluación, needs_human_review
"""

from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================
# EVALUATION SCHEMAS (Pydantic - No persisten directamente)
# ============================================================

class ReadabilityScore(BaseModel):
    """Score de legibilidad con py-readability-metrics"""
    pass_: bool
    flesch_reading_ease: float
    flesch_kincaid_grade: float
    gunning_fog: float
    target_flesch: float = 60.0  # Umbral mínimo
    details: str  # Explicación legible para humanos


class RelevanceScore(BaseModel):
    """Score de pertinencia vs. key_aspects de Parte 1"""
    pass_: bool
    covered_aspects: List[str]  # Aspectos cubiertos
    missing_aspects: List[str]  # Aspectos NO cubiertos
    coverage_percentage: float  # 0.0 - 1.0


class ComplianceScore(BaseModel):
    """Score de cumplimiento con políticas corporativas"""
    pass_: bool
    checked_rules: List[str]  # IDs de reglas verificadas
    violations: List[str]  # Violaciones detectadas
    severity: str  # "blocker", "warning", "info"


class EvaluationResult(BaseModel):
    """Resultado consolidado de evaluación de una sección"""
    section_id: str  # ID único de la sección
    department: str  # Departamento (operaciones, compras, etc.)
    iteration: int  # Número de iteración (1-based)

    # Scores por dimensión
    readability: ReadabilityScore
    relevance: RelevanceScore
    compliance: ComplianceScore

    # Decisión final
    overall_pass: bool  # True si TODAS las dimensiones pasan

    # Feedback accionable para el generador
    feedback_for_generator: str  # Texto concreto para re-generación

    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# DATABASE MODELS (SQLModel - Persisten en PostgreSQL)
# ============================================================

class DraftSection(SQLModel, table=True):
    """
    Borrador de sección generado por un departamento.

    Tabla: draft_sections

    Ciclo de vida:
    1. Generator crea borrador (iteration=1)
    2. Evaluators analizan → EvaluationRecord
    3. Si falla → Generator re-genera (iteration+=1)
    4. Si pasa O max_iterations → Persist final
    """
    __tablename__ = "draft_sections"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Relación con RFP original
    ticket_id: int = Field(foreign_key="rfp_tickets.id")
    department: str  # DepartmentType.value

    # Contenido generado
    technical_content: str = Field(description="Sección técnica redactada")
    economic_content: str = Field(description="Sección económica redactada")

    # Metadata de generación
    assumptions: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Suposiciones hechas durante generación"
    )
    clarifications_needed: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Datos faltantes identificados"
    )

    # Control de iteraciones
    iteration_number: int = Field(default=1, description="Iteración actual (1-based)")
    max_iterations: int = Field(default=3, description="Límite de intentos")

    # Estado
    is_final: bool = Field(default=False, description="¿Es la versión final?")
    passed_evaluation: bool = Field(default=False, description="¿Pasó todas las evaluaciones?")

    # Trazabilidad
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relaciones
    evaluations: List["EvaluationRecord"] = Relationship(back_populates="draft_section")


class EvaluationRecord(SQLModel, table=True):
    """
    Registro de evaluación de una sección borrador.

    Tabla: evaluation_records

    Almacena el resultado estructurado de los 3 evaluadores.
    """
    __tablename__ = "evaluation_records"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Relación con borrador
    draft_section_id: int = Field(foreign_key="draft_sections.id")

    # Iteración evaluada
    iteration: int = Field(description="Iteración evaluada (1-based)")

    # Resultado JSON estructurado (EvaluationResult serializado)
    evaluation_data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="EvaluationResult completo en JSON"
    )

    # Decisión
    overall_pass: bool
    feedback_summary: str  # Resumen para generador

    # Scores individuales (desnormalizados para queries rápidas)
    readability_pass: bool = Field(default=False)
    readability_score: float = Field(default=0.0, description="Flesch Reading Ease")

    relevance_pass: bool = Field(default=False)
    relevance_coverage: float = Field(default=0.0, description="Coverage percentage")

    compliance_pass: bool = Field(default=False)
    compliance_severity: str = Field(default="unknown", description="blocker|warning|info")

    # Metadata
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relaciones
    draft_section: Optional[DraftSection] = Relationship(back_populates="evaluations")


class GenerationFeedback(SQLModel, table=True):
    """
    Historial de feedback entre evaluadores y generadores.

    Tabla: generation_feedback

    Permite rastrear qué cambios se solicitaron y cómo evolucionó el borrador.
    """
    __tablename__ = "generation_feedback"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Relación
    draft_section_id: int = Field(foreign_key="draft_sections.id")
    iteration: int  # Iteración que produjo este feedback

    # Feedback estructurado por dimensión
    readability_feedback: Optional[str] = Field(default=None)
    relevance_feedback: Optional[str] = Field(default=None)
    compliance_feedback: Optional[str] = Field(default=None)

    # Feedback consolidado
    full_feedback: str = Field(description="Feedback completo para el generador")

    # Acciones tomadas
    action_taken: str = Field(description="regenerated|human_review|approved")

    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def create_draft_section(
    ticket_id: int,
    department: str,
    technical_content: str,
    economic_content: str,
    assumptions: List[str] = None,
    clarifications_needed: List[str] = None,
    iteration_number: int = 1,
    max_iterations: int = 3
) -> DraftSection:
    """
    Factory function para crear DraftSection.
    """
    return DraftSection(
        ticket_id=ticket_id,
        department=department,
        technical_content=technical_content,
        economic_content=economic_content,
        assumptions=assumptions or [],
        clarifications_needed=clarifications_needed or [],
        iteration_number=iteration_number,
        max_iterations=max_iterations,
        is_final=False,
        passed_evaluation=False
    )


def create_evaluation_record(
    draft_section_id: int,
    evaluation_result: EvaluationResult
) -> EvaluationRecord:
    """
    Factory function para crear EvaluationRecord desde EvaluationResult.
    """
    return EvaluationRecord(
        draft_section_id=draft_section_id,
        iteration=evaluation_result.iteration,
        evaluation_data=evaluation_result.model_dump(),  # Serializar Pydantic model
        overall_pass=evaluation_result.overall_pass,
        feedback_summary=evaluation_result.feedback_for_generator,
        readability_pass=evaluation_result.readability.pass_,
        readability_score=evaluation_result.readability.flesch_reading_ease,
        relevance_pass=evaluation_result.relevance.pass_,
        relevance_coverage=evaluation_result.relevance.coverage_percentage,
        compliance_pass=evaluation_result.compliance.pass_,
        compliance_severity=evaluation_result.compliance.severity
    )
