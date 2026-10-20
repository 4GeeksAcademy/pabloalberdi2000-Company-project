from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, Dict
from datetime import date

from ..database import get_db
from ..models import Candidate, Note
from ..schemas import (
    CandidateCreate,
    CandidateUpdate,
    CandidateStatusUpdate,
    CandidateStageUpdate,
    CandidateResponse,
    NoteCreate,
    NoteResponse,
)
# Hito 4: Autenticación JWT
from ..auth.dependencies import get_current_active_user, require_manager_or_admin

router = APIRouter(
    prefix="",
    tags=["candidates"]
)


@router.get("/records", response_model=list[CandidateResponse])
async def list_candidates(
    status: Optional[str] = Query(None, description="Filter by status"),
    stage: Optional[str] = Query(None, description="Filter by stage"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)  # Hito 4: Protegido
):
    """
    List all candidates with optional filters.

    - **status**: Filter by candidate status (activo, archivado, contratado, rechazado)
    - **stage**: Filter by recruitment stage (aplicacion, revision, entrevista, oferta, finalizado)
    - **search**: Search by name or email (case-insensitive)
    """
    query = db.query(Candidate)

    if status:
        query = query.filter(Candidate.status == status)

    if stage:
        query = query.filter(Candidate.stage == stage)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Candidate.full_name.ilike(search_term),
                Candidate.email.ilike(search_term)
            )
        )

    candidates = query.order_by(Candidate.application_date.desc()).all()
    return candidates


@router.get("/records/{id}", response_model=CandidateResponse)
async def get_candidate(
    id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)  # Hito 4: Protegido
):
    """
    Get a candidate by ID.

    Returns full candidate information including all fields.
    """
    candidate = db.query(Candidate).filter(Candidate.id == id).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")

    return candidate


@router.post("/records", response_model=CandidateResponse, status_code=201)
async def create_candidate(
    candidate_data: CandidateCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new candidate.

    All required fields must be provided. Application date defaults to today if not specified.
    """
    # Check if email already exists
    existing_candidate = db.query(Candidate).filter(Candidate.email == candidate_data.email).first()
    if existing_candidate:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un candidato con el email {candidate_data.email}"
        )

    # Create candidate dict and set default application_date if not provided
    candidate_dict = candidate_data.model_dump()
    if candidate_dict.get('application_date') is None:
        candidate_dict['application_date'] = date.today()

    # Create new candidate
    db_candidate = Candidate(**candidate_dict)
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)

    return db_candidate


@router.put("/records/{id}", response_model=CandidateResponse)
async def update_candidate(
    id: int,
    candidate_data: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)  # Hito 4: Protegido
):
    """
    Update a candidate's information.

    All fields are optional. Only provided fields will be updated.
    """
    candidate = db.query(Candidate).filter(Candidate.id == id).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")

    # Check email uniqueness if email is being updated
    if candidate_data.email and candidate_data.email != candidate.email:
        existing = db.query(Candidate).filter(Candidate.email == candidate_data.email).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe un candidato con el email {candidate_data.email}"
            )

    # Update only provided fields
    update_data = candidate_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(candidate, field, value)

    db.commit()
    db.refresh(candidate)

    return candidate


@router.patch("/records/{id}/status")
async def update_candidate_status(
    id: int,
    status_data: CandidateStatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_manager_or_admin)  # Hito 4: Requiere manager/admin
):
    """
    Update only the candidate's status.

    Allowed statuses: activo, archivado, contratado, rechazado
    """
    candidate = db.query(Candidate).filter(Candidate.id == id).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")

    candidate.status = status_data.status
    db.commit()

    return {"message": "Estado actualizado exitosamente", "status": candidate.status}


@router.patch("/records/{id}/stage")
async def update_candidate_stage(
    id: int,
    stage_data: CandidateStageUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_manager_or_admin)  # Hito 4: Requiere manager/admin
):
    """
    Update only the candidate's recruitment stage.

    Allowed stages: aplicacion, revision, entrevista, oferta, finalizado
    """
    candidate = db.query(Candidate).filter(Candidate.id == id).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")

    candidate.stage = stage_data.stage
    db.commit()

    return {"message": "Etapa actualizada exitosamente", "stage": candidate.stage}


# ============ NOTES ENDPOINTS ============

@router.get("/records/{id}/notes", response_model=list[NoteResponse])
async def get_candidate_notes(
    id: int,
    db: Session = Depends(get_db)
):
    """
    Get all notes for a candidate.

    Returns notes ordered by creation date (most recent first).
    """
    # Verify candidate exists
    candidate = db.query(Candidate).filter(Candidate.id == id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")

    notes = db.query(Note).filter(Note.candidate_id == id).order_by(Note.created_at.desc()).all()
    return notes


@router.post("/records/{id}/notes", response_model=NoteResponse, status_code=201)
async def create_candidate_note(
    id: int,
    note_data: NoteCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)  # Hito 4: Protegido
):
    """
    Create a new note for a candidate.

    Notes are used to track interview feedback, impressions, and other observations.
    """
    # Verify candidate exists
    candidate = db.query(Candidate).filter(Candidate.id == id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")

    # Create note
    db_note = Note(
        candidate_id=id,
        content=note_data.content,
        author=note_data.author
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)

    return db_note


@router.delete("/records/{id}/notes/{note_id}", status_code=204)
async def delete_candidate_note(
    id: int,
    note_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)  # Hito 4: Protegido
):
    """
    Delete a note from a candidate.

    Permanently removes the note. This action cannot be undone.
    """
    # Verify candidate exists
    candidate = db.query(Candidate).filter(Candidate.id == id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidato no encontrado")

    # Find and delete note
    note = db.query(Note).filter(Note.id == note_id, Note.candidate_id == id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Nota no encontrada")

    db.delete(note)
    db.commit()

    return None
