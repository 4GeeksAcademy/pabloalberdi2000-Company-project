"""
FastAPI Router - RFP Intake Endpoints

Endpoints para sistema de recepción y análisis de RFPs:
- POST /rfp/upload: Subida de PDF con procesamiento asíncrono (202 Accepted)
- GET /rfp/tickets/{ticket_id}: Consulta de estado y resultados
- GET /rfp/tickets: Listado de tickets

CRÍTICO:
- Modo ticket: Upload → 202 Accepted → Background task
- Persistencia en PostgreSQL/Supabase (NO TinyDB)
- Pipeline asíncrono en background
"""

import os
import shutil
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from services.models.rfp import (
    RFPTicket,
    RFPMetadata,
    DepartmentSection,
    RFPSynthesis,
    RFPTicketStatus,
    create_rfp_ticket
)
from data.pipelines.rfp_intake.ingest import process_rfp_document
from data.pipelines.rfp_intake.graph import execute_rfp_pipeline
from services.notifications import connection_manager, RFPTicketEvent

# Router
router = APIRouter(prefix="/rfp", tags=["RFP Intake"])

# Directorios
RAW_PDF_DIR = "data/raw/rfp_pdfs"
os.makedirs(RAW_PDF_DIR, exist_ok=True)


# ============================================================
# DEPENDENCY: DB SESSION
# ============================================================

def get_db():
    """
    Dependency para obtener sesión de BD.

    TODO: Implementar con SQLModel/Supabase engine real.
    Por ahora, placeholder para la estructura.
    """
    # from services.database import SessionLocal
    # db = SessionLocal()
    # try:
    #     yield db
    # finally:
    #     db.close()

    # Placeholder
    raise NotImplementedError("DB session dependency pendiente de configurar")


# ============================================================
# BACKGROUND TASK
# ============================================================

def background_rfp_pipeline(
    ticket_id: int,
    pdf_path: str,
    db_session
):
    """
    Tarea en background: Ejecuta pipeline completo de RFP.

    Args:
        ticket_id: ID del ticket en BD
        pdf_path: Ruta del PDF original
        db_session: Sesión de BD

    Flow:
    1. Ingest: PDF → Markdown + métricas
    2. Graph: Classifier → Orchestrator → Workers → Synthesizer
    3. Persist: Actualizar ticket, metadata, sections, synthesis
    """
    print(f"\n🔄 Background task iniciada para ticket {ticket_id}")

    try:
        # 1. Procesamiento de ingesta
        print(f"📄 Ingesta: Convirtiendo PDF a Markdown...")
        ingest_result = process_rfp_document(pdf_path)

        # 2. Actualizar metadata con métricas
        ticket = db_session.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} no encontrado")

        ticket.markdown_path = ingest_result["markdown_path"]

        # Crear metadata
        metadata = RFPMetadata(
            ticket_id=ticket_id,
            flesch_reading_ease=ingest_result["readability_metrics"]["flesch_reading_ease"],
            flesch_kincaid_grade=ingest_result["readability_metrics"]["flesch_kincaid_grade"],
            gunning_fog=ingest_result["readability_metrics"]["gunning_fog"],
            smog_index=ingest_result["readability_metrics"]["smog_index"],
            estimated_tokens=ingest_result["token_estimation"]["estimated_tokens"],
            estimated_cost_usd=ingest_result["token_estimation"]["estimated_cost_usd"],
            created_at=datetime.utcnow()
        )
        db_session.add(metadata)
        db_session.commit()

        # 3. Ejecutar grafo multi-agente
        print(f"🤖 Grafo: Ejecutando pipeline multi-agente...")
        pipeline_result = execute_rfp_pipeline(
            ticket_id=ticket_id,
            markdown_path=ingest_result["markdown_path"],
            markdown_content=ingest_result["markdown_content"],
            db_session=db_session
        )

        print(f"✅ Background task completada para ticket {ticket_id}")
        print(f"   Estado final: {pipeline_result.get('status')}")

    except Exception as e:
        print(f"❌ Error en background task: {e}")

        # Actualizar ticket con error
        try:
            ticket = db_session.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()
            if ticket:
                ticket.status = RFPTicketStatus.ERROR
                ticket.error_message = str(e)
                ticket.updated_at = datetime.utcnow()
                db_session.commit()
        except Exception as persist_error:
            print(f"❌ Error persistiendo error: {persist_error}")


# ============================================================
# ENDPOINTS
# ============================================================

@router.post("/upload", status_code=202)
async def upload_rfp(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Sube PDF de RFP y lanza pipeline asíncrono.

    **Flow:**
    1. Validar archivo (PDF, tamaño < 10MB)
    2. Guardar en data/raw/rfp_pdfs/
    3. Crear ticket con status=analizando
    4. Agregar background_task para ejecutar pipeline
    5. Retornar 202 Accepted con ticket_id

    **Args:**
    - file: Archivo PDF de la RFP

    **Returns:**
    ```json
    {
      "ticket_id": 123,
      "filename": "client_rfp.pdf",
      "status": "analizando",
      "message": "RFP recibida. Análisis en progreso.",
      "created_at": "2024-10-30T12:00:00Z"
    }
    ```

    **Status Code:** 202 Accepted (procesamiento asíncrono)
    """
    # Validación de archivo
    if not file.filename:
        raise HTTPException(400, "Filename requerido")

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Solo se aceptan archivos PDF")

    # Validación de tamaño (< 10MB)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset

    if file_size > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(400, f"Archivo muy grande ({file_size / 1024 / 1024:.2f} MB). Máximo: 10MB")

    # Generar nombre único para evitar colisiones
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(RAW_PDF_DIR, safe_filename)

    # Guardar PDF
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"✅ PDF guardado: {file_path}")

    except Exception as e:
        raise HTTPException(500, f"Error guardando archivo: {str(e)}")

    # Crear ticket en BD
    try:
        ticket = create_rfp_ticket(
            filename=file.filename,
            file_path=file_path
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        print(f"✅ Ticket creado: {ticket.id}")

        # 🔔 PUBLICAR EVENTO SSE: Notificar creación de ticket
        event = RFPTicketEvent(
            event_type="rfp_ticket_created",
            ticket_id=ticket.id,
            status=ticket.status.value,
            filename=ticket.filename,
            client_name=None,  # Se actualiza cuando se extraiga metadata
            created_at=ticket.created_at.isoformat()
        )

        # Publicar a todos los clientes SSE conectados
        asyncio.create_task(connection_manager.publish(event))
        print(f"🔔 Evento SSE publicado: rfp_ticket_created (ticket {ticket.id})")

    except Exception as e:
        # Limpiar archivo si falla la creación del ticket
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(500, f"Error creando ticket: {str(e)}")

    # Agregar tarea en background
    background_tasks.add_task(
        background_rfp_pipeline,
        ticket_id=ticket.id,
        pdf_path=file_path,
        db_session=db
    )

    print(f"🔄 Background task encolada para ticket {ticket.id}")

    # Respuesta 202 Accepted
    return {
        "ticket_id": ticket.id,
        "filename": ticket.filename,
        "status": ticket.status.value,
        "message": "RFP recibida. Análisis en progreso. Use GET /rfp/tickets/{ticket_id} para consultar el estado.",
        "created_at": ticket.created_at.isoformat()
    }


@router.get("/tickets/{ticket_id}")
def get_rfp_ticket(
    ticket_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Consulta estado y resultados de un ticket de RFP.

    **Args:**
    - ticket_id: ID del ticket

    **Returns (status=analisis_completo):**
    ```json
    {
      "ticket_id": 123,
      "filename": "client_rfp.pdf",
      "status": "analisis_completo",
      "created_at": "2024-10-30T12:00:00Z",
      "updated_at": "2024-10-30T12:02:30Z",
      "is_valid_rfp": true,
      "classifier_confidence": 0.92,
      "metadata": {
        "client_name": "Acme Corp",
        "submission_deadline": "2024-12-15",
        "flesch_reading_ease": 50.2,
        "estimated_tokens": 5000,
        "estimated_cost_usd": 0.02
      },
      "sections": [
        {
          "department": "operaciones",
          "section_title": "Gestión de Inventarios",
          "key_aspects": {
            "requirements": ["..."],
            "missing_data": ["presupuesto específico"],
            "estimated_effort": "alto"
          }
        }
      ],
      "synthesis": {
        "executive_summary": "...",
        "involved_departments": ["operaciones", "tecnologia", "marketing"],
        "critical_dependencies": ["..."],
        "identified_risks": [...]
      }
    }
    ```

    **Returns (status=analizando):**
    ```json
    {
      "ticket_id": 123,
      "status": "analizando",
      "message": "Análisis en progreso. Por favor intente nuevamente en unos momentos."
    }
    ```
    """
    # Buscar ticket
    ticket = db.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} no encontrado")

    # Respuesta base
    response = {
        "ticket_id": ticket.id,
        "filename": ticket.filename,
        "status": ticket.status.value,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat()
    }

    # Si está en proceso, retornar mensaje
    if ticket.status == RFPTicketStatus.ANALIZANDO:
        response["message"] = "Análisis en progreso. Por favor intente nuevamente en unos momentos."
        return response

    # Si fue descartado
    if ticket.status == RFPTicketStatus.DESCARTADO:
        response["is_valid_rfp"] = False
        response["rejection_reason"] = ticket.rejection_reason
        response["classifier_confidence"] = ticket.classifier_confidence
        return response

    # Si hubo error
    if ticket.status == RFPTicketStatus.ERROR:
        response["error_message"] = ticket.error_message
        return response

    # Si completó: agregar todos los detalles
    response["is_valid_rfp"] = ticket.is_valid_rfp
    response["classifier_confidence"] = ticket.classifier_confidence

    # Metadata
    if ticket.metadata:
        response["metadata"] = {
            "client_name": ticket.metadata.client_name,
            "project_title": ticket.metadata.project_title,
            "submission_deadline": ticket.metadata.submission_deadline.isoformat() if ticket.metadata.submission_deadline else None,
            "budget_range": ticket.metadata.budget_range,
            "flesch_reading_ease": ticket.metadata.flesch_reading_ease,
            "flesch_kincaid_grade": ticket.metadata.flesch_kincaid_grade,
            "gunning_fog": ticket.metadata.gunning_fog,
            "estimated_tokens": ticket.metadata.estimated_tokens,
            "estimated_cost_usd": ticket.metadata.estimated_cost_usd
        }

    # Secciones por departamento
    if ticket.sections:
        response["sections"] = [
            {
                "department": section.department.value,
                "section_title": section.section_title,
                "key_aspects": section.key_aspects,
                "processed_at": section.processed_at.isoformat(),
                "worker_confidence": section.worker_confidence
            }
            for section in ticket.sections
        ]

    # Síntesis
    synthesis = db.query(RFPSynthesis).filter(RFPSynthesis.ticket_id == ticket_id).first()
    if synthesis:
        response["synthesis"] = {
            "executive_summary": synthesis.executive_summary,
            "involved_departments": synthesis.involved_departments,
            "critical_dependencies": synthesis.critical_dependencies,
            "identified_risks": synthesis.identified_risks,
            "missing_critical_data": synthesis.missing_critical_data,
            "recommended_workstreams": synthesis.recommended_workstreams,
            "synthesis_confidence": synthesis.synthesis_confidence,
            "synthesized_at": synthesis.synthesized_at.isoformat()
        }

    return response


@router.get("/tickets")
def list_rfp_tickets(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Lista tickets de RFP con paginación y filtros.

    **Query Parameters:**
    - status: Filtrar por estado (analizando, descartado, analisis_completo, error)
    - limit: Número máximo de resultados (default: 50, max: 100)
    - offset: Offset para paginación (default: 0)

    **Returns:**
    ```json
    {
      "tickets": [
        {
          "ticket_id": 123,
          "filename": "client_rfp.pdf",
          "status": "analisis_completo",
          "created_at": "2024-10-30T12:00:00Z",
          "client_name": "Acme Corp"
        }
      ],
      "total": 150,
      "limit": 50,
      "offset": 0
    }
    ```
    """
    # Validar limit
    if limit > 100:
        limit = 100

    # Query base
    query = select(RFPTicket)

    # Filtro por status
    if status:
        try:
            status_enum = RFPTicketStatus(status)
            query = query.where(RFPTicket.status == status_enum)
        except ValueError:
            raise HTTPException(400, f"Status inválido: {status}. Válidos: analizando, descartado, analisis_completo, error")

    # Ordenar por fecha de creación (más recientes primero)
    query = query.order_by(RFPTicket.created_at.desc())

    # Contar total
    count_query = select(RFPTicket)
    if status:
        count_query = count_query.where(RFPTicket.status == status_enum)
    total = len(db.exec(count_query).all())

    # Aplicar paginación
    query = query.offset(offset).limit(limit)
    tickets = db.exec(query).all()

    # Formatear respuesta
    tickets_list = []
    for ticket in tickets:
        ticket_data = {
            "ticket_id": ticket.id,
            "filename": ticket.filename,
            "status": ticket.status.value,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat()
        }

        # Agregar client_name si existe
        if ticket.metadata and ticket.metadata.client_name:
            ticket_data["client_name"] = ticket.metadata.client_name

        tickets_list.append(ticket_data)

    return {
        "tickets": tickets_list,
        "total": total,
        "limit": limit,
        "offset": offset
    }
