"""
FastAPI Router - RFP Generation Endpoints (Parte 2)

Endpoints para generación y evaluación iterativa de propuestas RFP:
- POST /rfp/generation/start: Inicia generación para ticket con status=analisis_completo
- GET /rfp/generation/{ticket_id}/status: Consulta estado de generación
- GET /rfp/generation/{ticket_id}/drafts: Obtiene borradores generados
- POST /rfp/generation/{ticket_id}/approve: Aprueba borradores manualmente

CRÍTICO:
- Consume handoff de Parte 1 (NO re-parsea PDF)
- Procesamiento asíncrono con 202 Accepted
- Límite de iteraciones: 3
- NUNCA descarta ticket: conserva último borrador
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from pydantic import BaseModel

from services.models.rfp import (
    RFPTicket,
    RFPSynthesis,
    DepartmentSection,
    RFPTicketStatus
)
from services.models.rfp_eval import (
    DraftSection,
    EvaluationRecord,
    GenerationFeedback,
    create_draft_section,
    create_evaluation_record
)
from data.pipelines.rfp_generation.graph import execute_rfp_generation_pipeline


# Router
router = APIRouter(prefix="/rfp/generation", tags=["RFP Generation"])


# ============================================================
# DEPENDENCY: DB SESSION
# ============================================================

def get_db():
    """
    Dependency para obtener sesión de BD.

    TODO: Implementar con SQLModel/Supabase engine real.
    """
    raise NotImplementedError("DB session dependency pendiente de configurar")


# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================

class GenerationStartRequest(BaseModel):
    """Request para iniciar generación de propuesta"""
    ticket_id: int
    max_iterations: int = 3  # Límite de iteraciones (default: 3)


class GenerationStatusResponse(BaseModel):
    """Response con estado de generación"""
    ticket_id: int
    status: str  # generando_borrador, en_evaluacion, needs_human_review, listo_para_consolidacion
    current_iteration: int
    max_iterations: int
    sections_generated: int
    sections_approved: int
    message: str


class DraftSectionResponse(BaseModel):
    """Response con borrador de sección"""
    department: str
    iteration_number: int
    technical_content: str
    economic_content: str
    assumptions: List[str]
    clarifications_needed: List[str]
    is_final: bool
    passed_evaluation: bool
    evaluation_summary: Optional[Dict[str, Any]] = None


# ============================================================
# BACKGROUND TASK
# ============================================================

def background_generation_pipeline(
    ticket_id: int,
    max_iterations: int,
    db_session
):
    """
    Tarea en background: Ejecuta pipeline completo de generación y evaluación.

    Args:
        ticket_id: ID del ticket con status=analisis_completo
        max_iterations: Límite de iteraciones
        db_session: Sesión de BD

    Flow:
    1. Verificar que ticket esté en analisis_completo
    2. Actualizar status a generando_borrador
    3. Ejecutar pipeline (coordinator → generators → evaluators → loop)
    4. Actualizar status final (listo_para_consolidacion o needs_human_review)
    """
    print(f"\n🔄 Background generation task iniciada para ticket {ticket_id}")

    try:
        # 1. Verificar estado del ticket
        ticket = db_session.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} no encontrado")

        if ticket.status != RFPTicketStatus.ANALISIS_COMPLETO:
            raise ValueError(
                f"Ticket debe estar en 'analisis_completo'. Estado actual: {ticket.status}"
            )

        # 2. Actualizar status a generando_borrador
        ticket.status = RFPTicketStatus.GENERANDO_BORRADOR
        ticket.updated_at = datetime.utcnow()
        db_session.commit()

        print(f"✅ Ticket {ticket_id} actualizado a 'generando_borrador'")

        # 3. Ejecutar pipeline
        print(f"🤖 Ejecutando pipeline de generación y evaluación...")
        result = execute_rfp_generation_pipeline(
            ticket_id=ticket_id,
            max_iterations=max_iterations,
            db_session=db_session
        )

        # 4. Actualizar status final
        if result["status"] == "approved":
            ticket.status = RFPTicketStatus.LISTO_PARA_CONSOLIDACION
            print(f"✅ Todas las secciones aprobadas → listo_para_consolidacion")
        else:
            ticket.status = RFPTicketStatus.NEEDS_HUMAN_REVIEW
            print(f"⚠️  Requiere revisión humana → needs_human_review")

        ticket.updated_at = datetime.utcnow()
        db_session.commit()

        print(f"✅ Background generation task completada para ticket {ticket_id}")
        print(f"   Resultado: {result['status']}")
        print(f"   Secciones aprobadas: {result['sections_approved']}/{result['total_sections']}")

    except Exception as e:
        print(f"❌ Error en background generation task: {e}")

        # Actualizar ticket con error
        try:
            ticket = db_session.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()
            if ticket:
                ticket.status = RFPTicketStatus.ERROR
                ticket.error_message = f"Error en generación: {str(e)}"
                ticket.updated_at = datetime.utcnow()
                db_session.commit()
        except Exception as persist_error:
            print(f"❌ Error persistiendo error: {persist_error}")


# ============================================================
# ENDPOINTS
# ============================================================

@router.post("/start", status_code=202)
async def start_generation(
    request: GenerationStartRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Inicia generación de propuesta para ticket con status=analisis_completo.

    **Flow:**
    1. Verificar que ticket esté en analisis_completo
    2. Lanzar pipeline en background
    3. Retornar 202 Accepted

    **Args:**
    - ticket_id: ID del ticket
    - max_iterations: Límite de iteraciones (default: 3)

    **Returns:**
    ```json
    {
      "ticket_id": 123,
      "status": "generando_borrador",
      "message": "Generación iniciada. Use GET /rfp/generation/{ticket_id}/status para consultar progreso.",
      "max_iterations": 3
    }
    ```

    **Status Code:** 202 Accepted
    """
    ticket_id = request.ticket_id
    max_iterations = request.max_iterations

    # Verificar que ticket existe y está en estado correcto
    ticket = db.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} no encontrado")

    if ticket.status != RFPTicketStatus.ANALISIS_COMPLETO:
        raise HTTPException(
            400,
            f"Ticket debe estar en 'analisis_completo'. Estado actual: {ticket.status.value}"
        )

    # Lanzar background task
    background_tasks.add_task(
        background_generation_pipeline,
        ticket_id=ticket_id,
        max_iterations=max_iterations,
        db_session=db
    )

    print(f"🔄 Background generation task encolada para ticket {ticket_id}")

    # Respuesta 202 Accepted
    return {
        "ticket_id": ticket_id,
        "status": "generando_borrador",
        "message": f"Generación iniciada. Use GET /rfp/generation/{ticket_id}/status para consultar progreso.",
        "max_iterations": max_iterations
    }


@router.get("/{ticket_id}/status")
def get_generation_status(
    ticket_id: int,
    db: Session = Depends(get_db)
) -> GenerationStatusResponse:
    """
    Consulta estado de generación de propuesta.

    **Returns:**
    ```json
    {
      "ticket_id": 123,
      "status": "en_evaluacion",
      "current_iteration": 2,
      "max_iterations": 3,
      "sections_generated": 3,
      "sections_approved": 2,
      "message": "Generación en progreso. Iteración 2/3."
    }
    ```
    """
    # Buscar ticket
    ticket = db.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} no encontrado")

    # Contar secciones generadas
    drafts = db.query(DraftSection).filter(DraftSection.ticket_id == ticket_id).all()
    sections_generated = len(drafts)
    sections_approved = sum(1 for d in drafts if d.passed_evaluation)

    # Determinar iteración actual (máximo de todas las secciones)
    current_iteration = max([d.iteration_number for d in drafts], default=0)
    max_iterations = max([d.max_iterations for d in drafts], default=3)

    # Mensaje según estado
    if ticket.status == RFPTicketStatus.GENERANDO_BORRADOR:
        message = f"Generando borradores. Iteración {current_iteration}/{max_iterations}."
    elif ticket.status == RFPTicketStatus.EN_EVALUACION:
        message = f"Evaluando secciones generadas. Iteración {current_iteration}/{max_iterations}."
    elif ticket.status == RFPTicketStatus.NEEDS_HUMAN_REVIEW:
        message = f"Requiere revisión humana. Límite de iteraciones alcanzado ({max_iterations})."
    elif ticket.status == RFPTicketStatus.LISTO_PARA_CONSOLIDACION:
        message = f"✅ Todas las secciones aprobadas ({sections_approved}/{sections_generated})."
    else:
        message = f"Estado: {ticket.status.value}"

    return GenerationStatusResponse(
        ticket_id=ticket_id,
        status=ticket.status.value,
        current_iteration=current_iteration,
        max_iterations=max_iterations,
        sections_generated=sections_generated,
        sections_approved=sections_approved,
        message=message
    )


@router.get("/{ticket_id}/drafts")
def get_drafts(
    ticket_id: int,
    include_evaluations: bool = True,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Obtiene borradores generados para un ticket.

    **Query Parameters:**
    - include_evaluations: Incluir resultados de evaluación (default: true)

    **Returns:**
    ```json
    {
      "ticket_id": 123,
      "total_sections": 3,
      "sections": [
        {
          "department": "operaciones",
          "iteration_number": 2,
          "technical_content": "...",
          "economic_content": "...",
          "is_final": true,
          "passed_evaluation": true,
          "evaluation_summary": {
            "overall_pass": true,
            "readability_pass": true,
            "relevance_pass": true,
            "compliance_pass": true
          }
        }
      ]
    }
    ```
    """
    # Buscar ticket
    ticket = db.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} no encontrado")

    # Obtener borradores
    drafts = db.query(DraftSection).filter(
        DraftSection.ticket_id == ticket_id
    ).order_by(DraftSection.department, DraftSection.iteration_number.desc()).all()

    # Agrupar por departamento (solo la versión más reciente)
    latest_drafts = {}
    for draft in drafts:
        if draft.department not in latest_drafts:
            latest_drafts[draft.department] = draft

    # Formatear respuesta
    sections = []
    for dept, draft in latest_drafts.items():
        section_data = DraftSectionResponse(
            department=draft.department,
            iteration_number=draft.iteration_number,
            technical_content=draft.technical_content,
            economic_content=draft.economic_content,
            assumptions=draft.assumptions,
            clarifications_needed=draft.clarifications_needed,
            is_final=draft.is_final,
            passed_evaluation=draft.passed_evaluation
        )

        # Incluir evaluación si se solicita
        if include_evaluations:
            eval_record = db.query(EvaluationRecord).filter(
                EvaluationRecord.draft_section_id == draft.id
            ).order_by(EvaluationRecord.evaluated_at.desc()).first()

            if eval_record:
                section_data.evaluation_summary = {
                    "overall_pass": eval_record.overall_pass,
                    "readability_pass": eval_record.readability_pass,
                    "readability_score": eval_record.readability_score,
                    "relevance_pass": eval_record.relevance_pass,
                    "relevance_coverage": eval_record.relevance_coverage,
                    "compliance_pass": eval_record.compliance_pass,
                    "compliance_severity": eval_record.compliance_severity,
                    "feedback": eval_record.feedback_summary
                }

        sections.append(section_data)

    return {
        "ticket_id": ticket_id,
        "status": ticket.status.value,
        "total_sections": len(sections),
        "sections": [s.model_dump() for s in sections]
    }


@router.post("/{ticket_id}/approve")
def approve_drafts(
    ticket_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Aprueba manualmente los borradores y marca ticket como listo_para_consolidacion.

    **Use Case:**
    - Ticket en estado needs_human_review
    - Humano revisó y aprobó los borradores
    - Sistema debe avanzar a Parte 3

    **Returns:**
    ```json
    {
      "ticket_id": 123,
      "status": "listo_para_consolidacion",
      "message": "Borradores aprobados manualmente. Listo para Parte 3."
    }
    ```
    """
    # Buscar ticket
    ticket = db.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} no encontrado")

    if ticket.status != RFPTicketStatus.NEEDS_HUMAN_REVIEW:
        raise HTTPException(
            400,
            f"Ticket debe estar en 'needs_human_review'. Estado actual: {ticket.status.value}"
        )

    # Marcar todos los borradores como finales y aprobados
    drafts = db.query(DraftSection).filter(DraftSection.ticket_id == ticket_id).all()

    for draft in drafts:
        draft.is_final = True
        draft.passed_evaluation = True  # Aprobación manual
        draft.updated_at = datetime.utcnow()

    # Actualizar ticket
    ticket.status = RFPTicketStatus.LISTO_PARA_CONSOLIDACION
    ticket.updated_at = datetime.utcnow()

    db.commit()

    print(f"✅ Ticket {ticket_id} aprobado manualmente → listo_para_consolidacion")

    return {
        "ticket_id": ticket_id,
        "status": ticket.status.value,
        "message": "Borradores aprobados manualmente. Listo para Parte 3.",
        "sections_approved": len(drafts)
    }
