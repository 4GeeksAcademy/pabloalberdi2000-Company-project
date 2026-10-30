"""
FastAPI Router - RFP Approval Endpoints (Parte 3)

Endpoints para aprobación humana y consolidación final:
- POST /rfp/approval/start: Inicia proceso de aprobación
- POST /rfp/approval/{ticket_id}/approve/{department}: Aprueba departamento
- POST /rfp/approval/{ticket_id}/reject/{department}: Rechaza departamento
- POST /rfp/approval/{ticket_id}/arbitrate: Resuelve conflictos (CEO)
- GET /rfp/approval/{ticket_id}/status: Consulta estado de aprobaciones
- GET /rfp/approval/{ticket_id}/final-document: Descarga documento final

CRÍTICO:
- Human-in-the-Loop con checkpointing PostgreSQL
- Thread IDs namespaced: rfp-{ticket_id}:{department}
- Reanudación limpia desde checkpoint
- NO reinicia grafo desde cero
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Response
from fastapi.responses import FileResponse, JSONResponse
from sqlmodel import Session, select
from pydantic import BaseModel

from services.models.rfp import (
    RFPTicket,
    RFPTicketStatus
)
from services.models.rfp_eval import DraftSection
from services.models.rfp_approval import (
    DepartmentApproval,
    ConflictRecord,
    FinalDocument,
    ApprovalStatus,
    HumanApprovalDecision,
    ArbitrationDecision,
    create_department_approval
)
from data.pipelines.rfp_approval.graph import (
    execute_rfp_approval_pipeline,
    resume_with_approval,
    resume_with_arbitration
)

# Router
router = APIRouter(prefix="/rfp/approval", tags=["RFP Approval"])


# ============================================================
# DEPENDENCY: DB SESSION
# ============================================================

def get_db():
    """
    Dependency para obtener sesión de BD.

    TODO: Implementar con SQLModel/Supabase engine real.
    """
    raise NotImplementedError("DB session dependency pendiente de configurar")


def get_checkpointer():
    """
    Dependency para obtener checkpointer PostgreSQL.

    TODO: Implementar con PostgresSaver real.
    """
    from langgraph.checkpoint.memory import MemorySaver

    # TODO: Reemplazar con PostgresSaver
    # from langgraph.checkpoint.postgres import PostgresSaver
    # from psycopg import Connection
    #
    # db_url = os.getenv("DATABASE_URL")
    # conn = Connection.connect(db_url)
    # checkpointer = PostgresSaver(conn)

    # Por ahora, MemorySaver (no persistente)
    checkpointer = MemorySaver()
    return checkpointer


# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================

class ApprovalStartRequest(BaseModel):
    """Request para iniciar aprobación"""
    ticket_id: int


class ApproveRequest(BaseModel):
    """Request para aprobar departamento"""
    approved: bool
    reviewer_name: str
    reviewer_role: str
    comments: Optional[str] = None
    changes_requested: List[str] = []


class ArbitrateRequest(BaseModel):
    """Request para arbitrar conflicto"""
    conflict_id: int
    arbitrator_name: str  # Mariana Restrepo
    resolution: str       # accept_dept_A, accept_dept_B, hybrid, regenerate
    resolution_notes: str
    affected_departments: List[str]


class ApprovalStatusResponse(BaseModel):
    """Response con estado de aprobaciones"""
    ticket_id: int
    status: str  # esperando_aprobación, terminado
    total_departments: int
    approved_departments: int
    pending_departments: List[str]
    conflicts: List[Dict[str, Any]]
    message: str


# ============================================================
# BACKGROUND TASK
# ============================================================

def background_approval_pipeline(
    ticket_id: int,
    checkpointer,
    db_session
):
    """
    Tarea en background: Inicia pipeline de aprobación.

    El pipeline se pausará en la primera interrupción HITL.
    """
    print(f"\n🔄 Background approval task iniciada para ticket {ticket_id}")

    try:
        # Verificar estado del ticket
        ticket = db_session.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} no encontrado")

        valid_statuses = [
            RFPTicketStatus.LISTO_PARA_CONSOLIDACION,
            RFPTicketStatus.NEEDS_HUMAN_REVIEW
        ]

        if ticket.status not in valid_statuses:
            raise ValueError(
                f"Ticket debe estar en 'listo_para_consolidacion' o 'needs_human_review'. "
                f"Estado actual: {ticket.status}"
            )

        # Actualizar status a esperando_aprobación
        ticket.status = RFPTicketStatus.ESPERANDO_APROBACION
        ticket.updated_at = datetime.utcnow()
        db_session.commit()

        print(f"✅ Ticket {ticket_id} actualizado a 'esperando_aprobacion'")

        # Ejecutar pipeline (se pausará en primera HITL)
        result = execute_rfp_approval_pipeline(
            ticket_id=ticket_id,
            db_session=db_session,
            checkpointer=checkpointer
        )

        print(f"✅ Background approval task completada")
        print(f"   Resultado: {result['status']}")

    except Exception as e:
        print(f"❌ Error en background approval task: {e}")

        try:
            ticket = db_session.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()
            if ticket:
                ticket.status = RFPTicketStatus.ERROR
                ticket.error_message = f"Error en aprobación: {str(e)}"
                ticket.updated_at = datetime.utcnow()
                db_session.commit()
        except Exception as persist_error:
            print(f"❌ Error persistiendo error: {persist_error}")


# ============================================================
# ENDPOINTS
# ============================================================

@router.post("/start", status_code=202)
async def start_approval(
    request: ApprovalStartRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    checkpointer = Depends(get_checkpointer),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Inicia proceso de aprobación para ticket listo para consolidación.

    **Flow:**
    1. Verificar que ticket esté en listo_para_consolidacion o needs_human_review
    2. Lanzar pipeline en background
    3. Pipeline se pausará en primera aprobación HITL
    4. Retornar 202 Accepted

    **Returns:**
    ```json
    {
      "ticket_id": 123,
      "status": "esperando_aprobacion",
      "message": "Proceso de aprobación iniciado. Se pausará para revisión humana."
    }
    ```
    """
    ticket_id = request.ticket_id

    # Verificar ticket
    ticket = db.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} no encontrado")

    valid_statuses = [
        RFPTicketStatus.LISTO_PARA_CONSOLIDACION,
        RFPTicketStatus.NEEDS_HUMAN_REVIEW
    ]

    if ticket.status not in valid_statuses:
        raise HTTPException(
            400,
            f"Ticket debe estar en 'listo_para_consolidacion' o 'needs_human_review'. "
            f"Estado actual: {ticket.status.value}"
        )

    # Lanzar background task
    background_tasks.add_task(
        background_approval_pipeline,
        ticket_id=ticket_id,
        checkpointer=checkpointer,
        db_session=db
    )

    print(f"🔄 Background approval task encolada para ticket {ticket_id}")

    return {
        "ticket_id": ticket_id,
        "status": "esperando_aprobacion",
        "message": "Proceso de aprobación iniciado. Se pausará para revisión humana por departamento."
    }


@router.post("/{ticket_id}/approve/{department}")
async def approve_department(
    ticket_id: int,
    department: str,
    request: ApproveRequest,
    checkpointer = Depends(get_checkpointer),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Aprueba o rechaza sección de un departamento.

    **HITL**: Este endpoint reanuda el pipeline desde el checkpoint.

    **Args:**
    - ticket_id: ID del ticket
    - department: Departamento (operaciones, tecnologia, etc.)
    - approved: True para aprobar, False para rechazar
    - reviewer_name: Nombre del aprobador
    - comments: Comentarios opcionales

    **Returns:**
    ```json
    {
      "ticket_id": 123,
      "department": "operaciones",
      "approved": true,
      "reviewer": "Felipe Guerrero",
      "message": "Sección aprobada. Pipeline reanudado.",
      "next_pending": ["tecnologia", "marketing"]
    }
    ```
    """
    # Verificar ticket
    ticket = db.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} no encontrado")

    if ticket.status != RFPTicketStatus.ESPERANDO_APROBACION:
        raise HTTPException(
            400,
            f"Ticket debe estar en 'esperando_aprobacion'. Estado actual: {ticket.status.value}"
        )

    # Crear decisión de aprobación
    decision = HumanApprovalDecision(
        approved=request.approved,
        reviewer_name=request.reviewer_name,
        reviewer_role=request.reviewer_role,
        comments=request.comments,
        changes_requested=request.changes_requested
    )

    # Reanudar pipeline con aprobación
    try:
        result = resume_with_approval(
            ticket_id=ticket_id,
            department=department,
            approval_decision=decision,
            checkpointer=checkpointer,
            db_session=db
        )

        # Verificar si hay más aprobaciones pendientes
        # TODO: Query de DepartmentApproval pendientes
        next_pending = []  # Mock

        message = f"Sección {'aprobada' if request.approved else 'rechazada'}. "
        if next_pending:
            message += f"Pendientes: {', '.join(next_pending)}"
        else:
            message += "Todas las secciones aprobadas."

        return {
            "ticket_id": ticket_id,
            "department": department,
            "approved": request.approved,
            "reviewer": request.reviewer_name,
            "message": message,
            "next_pending": next_pending
        }

    except Exception as e:
        raise HTTPException(500, f"Error reanudando pipeline: {str(e)}")


@router.post("/{ticket_id}/arbitrate")
async def arbitrate_conflict(
    ticket_id: int,
    request: ArbitrateRequest,
    checkpointer = Depends(get_checkpointer),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Resuelve conflicto entre departamentos (CEO: Mariana Restrepo).

    **HITL Arbitraje**: Reanuda pipeline tras decisión de arbitraje.

    **Args:**
    - conflict_id: ID del conflicto
    - resolution: accept_dept_A, accept_dept_B, hybrid, regenerate
    - resolution_notes: Notas de la decisión

    **Returns:**
    ```json
    {
      "ticket_id": 123,
      "conflict_id": 1,
      "resolution": "hybrid",
      "arbitrator": "Mariana Restrepo",
      "message": "Conflicto resuelto. Pipeline continuará."
    }
    ```
    """
    # Verificar ticket
    ticket = db.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} no encontrado")

    # Crear decisión de arbitraje
    decision = ArbitrationDecision(
        conflict_id=request.conflict_id,
        arbitrator_name=request.arbitrator_name,
        resolution=request.resolution,
        resolution_notes=request.resolution_notes,
        affected_departments=request.affected_departments
    )

    # Reanudar pipeline con arbitraje
    try:
        result = resume_with_arbitration(
            ticket_id=ticket_id,
            arbitration_decision=decision,
            checkpointer=checkpointer,
            db_session=db
        )

        return {
            "ticket_id": ticket_id,
            "conflict_id": request.conflict_id,
            "resolution": request.resolution,
            "arbitrator": request.arbitrator_name,
            "message": "Conflicto resuelto. Pipeline continuará hacia consolidación final.",
            "completed": result.get("completed", False)
        }

    except Exception as e:
        raise HTTPException(500, f"Error reanudando pipeline: {str(e)}")


@router.get("/{ticket_id}/status")
def get_approval_status(
    ticket_id: int,
    db: Session = Depends(get_db)
) -> ApprovalStatusResponse:
    """
    Consulta estado de aprobaciones.

    **Returns:**
    ```json
    {
      "ticket_id": 123,
      "status": "esperando_aprobacion",
      "total_departments": 3,
      "approved_departments": 2,
      "pending_departments": ["marketing"],
      "conflicts": [],
      "message": "Esperando aprobación de: marketing"
    }
    ```
    """
    # Buscar ticket
    ticket = db.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} no encontrado")

    # TODO: Query de DepartmentApproval
    # approvals = db.query(DepartmentApproval).filter(
    #     DepartmentApproval.ticket_id == ticket_id
    # ).all()

    # Mock de aprobaciones
    approvals = [
        {"department": "operaciones", "status": "approved"},
        {"department": "tecnologia", "status": "approved"},
        {"department": "marketing", "status": "pending"}
    ]

    total_departments = len(approvals)
    approved_departments = sum(1 for a in approvals if a["status"] == "approved")
    pending_departments = [a["department"] for a in approvals if a["status"] == "pending"]

    # TODO: Query de ConflictRecord
    conflicts = []  # Mock

    # Mensaje
    if ticket.status == RFPTicketStatus.TERMINADO:
        message = "✅ Todas las aprobaciones completadas. Documento final generado."
    elif pending_departments:
        message = f"Esperando aprobación de: {', '.join(pending_departments)}"
    elif conflicts:
        message = f"Requiere arbitraje: {len(conflicts)} conflictos detectados"
    else:
        message = "En proceso de consolidación final"

    return ApprovalStatusResponse(
        ticket_id=ticket_id,
        status=ticket.status.value,
        total_departments=total_departments,
        approved_departments=approved_departments,
        pending_departments=pending_departments,
        conflicts=conflicts,
        message=message
    )


@router.get("/{ticket_id}/final-document")
def get_final_document(
    ticket_id: int,
    format: str = "markdown",  # markdown, pdf, word
    db: Session = Depends(get_db)
):
    """
    Descarga documento final consolidado.

    **Query Parameters:**
    - format: markdown (default), pdf, word

    **Returns:**
    - FileResponse con documento en formato solicitado
    """
    # Buscar ticket
    ticket = db.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} no encontrado")

    if ticket.status != RFPTicketStatus.TERMINADO:
        raise HTTPException(
            400,
            f"Documento final solo disponible cuando ticket está en 'terminado'. "
            f"Estado actual: {ticket.status.value}"
        )

    # TODO: Query de FinalDocument
    # final_doc = db.query(FinalDocument).filter(
    #     FinalDocument.ticket_id == ticket_id
    # ).first()

    # Mock de rutas
    base_path = f"data/final_proposals/rfp_{ticket_id}_proposal"

    if format == "markdown":
        file_path = f"{base_path}.md"
        media_type = "text/markdown"
    elif format == "pdf":
        file_path = f"{base_path}.pdf"
        media_type = "application/pdf"
    elif format == "word":
        file_path = f"{base_path}.docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(400, f"Formato no soportado: {format}")

    # Verificar existencia
    if not os.path.exists(file_path):
        raise HTTPException(404, f"Archivo no encontrado: {file_path}")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=os.path.basename(file_path)
    )
