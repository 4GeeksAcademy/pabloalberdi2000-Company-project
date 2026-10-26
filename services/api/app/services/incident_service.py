"""
Incident Service - Business Logic Layer

Capa de lógica de negocio para gestión de incidencias.
Implementa máquina de estados, validaciones y operaciones CRUD.
"""
from typing import Optional, List, Tuple
from datetime import datetime
import uuid
from fastapi import HTTPException

from ..schemas.incident import (
    IncidentCreate,
    IncidentUpdate,
    IncidentStatusUpdate,
    IncidentResponse,
    IncidentSummary,
    Status
)
from ..tinydb_database import (
    get_incident_by_id,
    create_incident,
    update_incident,
    list_incidents,
    count_incidents,
    incidents_table
)


# ============================================================
# STATE MACHINE DEFINITION
# ============================================================

STATE_TRANSITIONS = {
    "open": ["in_progress", "discarded"],
    "in_progress": ["resolved", "discarded"],
    "resolved": [],      # Terminal state
    "discarded": []      # Terminal state
}


def validate_status_transition(current_status: Status, new_status: Status) -> bool:
    """
    Validar transición de estado según máquina de estados.

    Args:
        current_status: Estado actual
        new_status: Estado propuesto

    Returns:
        True si la transición es válida, False en caso contrario
    """
    allowed_transitions = STATE_TRANSITIONS.get(current_status, [])
    return new_status in allowed_transitions


# ============================================================
# CRUD OPERATIONS
# ============================================================

def create_new_incident(data: IncidentCreate) -> IncidentResponse:
    """
    Crear nueva incidencia (siempre inicia en estado 'open').

    Args:
        data: Datos de la incidencia

    Returns:
        Incidencia creada
    """
    now = datetime.utcnow().isoformat()

    incident_doc = {
        "id": str(uuid.uuid4()),
        "title": data.title,
        "description": data.description,
        "category": data.category,
        "status": "open",  # Siempre inicia como open
        "origin": data.origin,
        "branch": data.branch,
        "created_at": now,
        "updated_at": now,
    }

    created = create_incident(incident_doc)
    return IncidentResponse(**created)


def get_incident_by_uuid(incident_id: str) -> IncidentResponse:
    """
    Obtener incidencia por UUID.

    Args:
        incident_id: UUID de la incidencia

    Returns:
        Incidencia encontrada

    Raises:
        HTTPException: 404 si no se encuentra
    """
    incident = get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return IncidentResponse(**incident)


def update_incident_status(
    incident_id: str,
    status_data: IncidentStatusUpdate
) -> IncidentResponse:
    """
    Actualizar estado de incidencia con validación de máquina de estados.

    Args:
        incident_id: UUID de la incidencia
        status_data: Nuevo estado y satisfacción opcional

    Returns:
        Incidencia actualizada

    Raises:
        HTTPException: 400 si transición inválida, 404 si no existe
    """
    incident = get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    current_status = incident["status"]
    new_status = status_data.status

    # Validar transición de estado
    if not validate_status_transition(current_status, new_status):
        allowed = STATE_TRANSITIONS.get(current_status, [])
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from '{current_status}' to '{new_status}'. Allowed transitions: {allowed}"
        )

    update_data = {
        "status": new_status,
        "updated_at": datetime.utcnow().isoformat()
    }

    # Agregar satisfacción si se proporciona
    if status_data.satisfaction is not None:
        update_data["satisfaction"] = status_data.satisfaction

    updated = update_incident(incident_id, update_data)
    return IncidentResponse(**updated)


def update_incident_fields(
    incident_id: str,
    data: IncidentUpdate
) -> IncidentResponse:
    """
    Actualizar campos de incidencia (no status, no incidencias terminales).

    Args:
        incident_id: UUID de la incidencia
        data: Campos a actualizar

    Returns:
        Incidencia actualizada

    Raises:
        HTTPException: 400 si incidencia terminal, 404 si no existe
    """
    incident = get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # No permitir actualizar incidencias en estados terminales
    if incident["status"] in ["resolved", "discarded"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot update incidents in terminal states (resolved/discarded)"
        )

    update_data = {"updated_at": datetime.utcnow().isoformat()}

    if data.title is not None:
        update_data["title"] = data.title
    if data.description is not None:
        update_data["description"] = data.description
    if data.category is not None:
        update_data["category"] = data.category
    if data.branch is not None:
        update_data["branch"] = data.branch

    updated = update_incident(incident_id, update_data)
    return IncidentResponse(**updated)


def list_incidents_with_filters(
    status: Optional[Status] = None,
    origin: Optional[str] = None,
    branch: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Tuple[List[IncidentResponse], int]:
    """
    Listar incidencias con filtros opcionales y paginación.

    Args:
        status: Filtrar por estado
        origin: Filtrar por origen
        branch: Filtrar por sede
        category: Filtrar por categoría
        limit: Máximo de resultados
        offset: Offset para paginación

    Returns:
        Tupla (lista de incidencias, total)
    """
    filters = {}
    if status:
        filters["status"] = status
    if origin:
        filters["origin"] = origin
    if branch:
        filters["branch"] = branch
    if category:
        filters["category"] = category

    incidents = list_incidents(filters, limit, offset)
    total = count_incidents(filters)

    return [IncidentResponse(**inc) for inc in incidents], total


def get_incidents_summary() -> IncidentSummary:
    """
    Calcular métricas agregadas del sistema.

    Returns:
        Resumen con totales por estado, categoría, origen, sede y satisfacción promedio
    """
    all_incidents = incidents_table.all()
    total = len(all_incidents)

    # Inicializar contadores
    by_status = {}
    by_category = {}
    by_origin = {}
    by_branch = {}
    satisfaction_scores = []

    for incident in all_incidents:
        # Contar por estado
        status = incident["status"]
        by_status[status] = by_status.get(status, 0) + 1

        # Contar por categoría
        category = incident["category"]
        by_category[category] = by_category.get(category, 0) + 1

        # Contar por origen
        origin = incident["origin"]
        by_origin[origin] = by_origin.get(origin, 0) + 1

        # Contar por sede
        branch = incident["branch"]
        by_branch[branch] = by_branch.get(branch, 0) + 1

        # Recolectar puntuaciones de satisfacción (solo resueltos)
        if incident["status"] == "resolved" and "satisfaction" in incident:
            satisfaction_scores.append(incident["satisfaction"])

    # Calcular promedio de satisfacción
    avg_satisfaction = None
    if satisfaction_scores:
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores)

    return IncidentSummary(
        total_incidents=total,
        by_status=by_status,
        by_category=by_category,
        by_origin=by_origin,
        by_branch=by_branch,
        avg_satisfaction=avg_satisfaction
    )
