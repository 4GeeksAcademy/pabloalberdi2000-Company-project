"""
Router de Incidencias Postventa - CRUD + Analysis
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from typing import Optional

from app.schemas.incident import (
    AnalysisResponse,  # Existing
    IncidentCreate,
    IncidentUpdate,
    IncidentStatusUpdate,
    IncidentResponse,
    IncidentListResponse,
    IncidentSummary,
    Status,
    Origin,
    Categoria,
    Branch
)
from app.services.incident_analyzer import analizar_csv  # Existing
from app.services.incident_service import (
    create_new_incident,
    get_incident_by_uuid,
    update_incident_fields,
    update_incident_status,
    list_incidents_with_filters,
    get_incidents_summary
)
from app.auth.dependencies import get_current_active_user


router = APIRouter(
    prefix="/incidents",
    tags=["incidents"]
)


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_incidents(
    file: UploadFile = File(...)
):
    """
    Analiza un archivo CSV de incidencias postventa.

    - **file**: Archivo CSV con incidencias (formato según BRIEFING_INCIDENCIAS.md)

    Retorna métricas completas:
    - Total de registros procesados
    - Registros válidos e inválidos
    - Métricas por categoría, estado y país
    - Índice de satisfacción promedio
    """
    # Validar tipo de archivo
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser un CSV (.csv)"
        )

    try:
        # Leer contenido del archivo
        contenido = await file.read()
        contenido_str = contenido.decode('utf-8')

        # Analizar CSV
        resultado = await analizar_csv(contenido_str)

        return resultado

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="El archivo debe estar codificado en UTF-8"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el archivo: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Endpoint de salud para verificar que el servicio está activo"""
    return {
        "status": "ok",
        "service": "Incidents API",
        "version": "2.0.0",
        "features": ["csv-analysis", "persistent-crud"]
    }


# ============================================================
# NEW CRUD ENDPOINTS (Fase 4 - Incident Management)
# ============================================================

@router.post("", response_model=IncidentResponse, status_code=201)
async def create_incident(
    data: IncidentCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Crear nueva incidencia (protegido, inicia en estado 'open').

    Requiere autenticación JWT.

    Args:
        - **title**: Título descriptivo (max 255 caracteres)
        - **description**: Descripción detallada (max 2000 caracteres)
        - **category**: Categoría según BRIEFING
        - **origin**: customer | branch | internal
        - **branch**: Sede o "central"

    Returns:
        Incidencia creada con UUID
    """
    try:
        return create_new_incident(data)
    except Exception as e:
        print(f"Error creating incident: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al crear la incidencia")


@router.get("", response_model=IncidentListResponse)
async def list_incidents_endpoint(
    status: Optional[Status] = Query(None, description="Filtrar por estado"),
    origin: Optional[Origin] = Query(None, description="Filtrar por origen"),
    branch: Optional[Branch] = Query(None, description="Filtrar por sede"),
    category: Optional[Categoria] = Query(None, description="Filtrar por categoría"),
    limit: int = Query(100, ge=1, le=500, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Listar incidencias con filtros opcionales (protegido).

    Soporta paginación y múltiples filtros combinados.

    Query Params:
        - **status**: open, in_progress, resolved, discarded
        - **origin**: customer, branch, internal
        - **branch**: Nombre de sede o "central"
        - **category**: Categoría según BRIEFING
        - **limit**: Máximo 500 resultados por página (default 100)
        - **offset**: Número de registros a saltar (default 0)

    Returns:
        Lista paginada de incidencias con total
    """
    try:
        items, total = list_incidents_with_filters(
            status=status,
            origin=origin,
            branch=branch,
            category=category,
            limit=limit,
            offset=offset
        )

        return IncidentListResponse(
            total=total,
            items=items,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        print(f"Error listing incidents: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al listar incidencias")


@router.get("/summary", response_model=IncidentSummary)
async def get_summary_endpoint(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Obtener métricas agregadas del sistema (protegido).

    Retorna conteos agrupados por:
    - Estado (open, in_progress, resolved, discarded)
    - Categoría (calidad_comida, servicio_cliente, etc.)
    - Origen (customer, branch, internal)
    - Sede (14 locales + central)
    - Satisfacción promedio (solo incidencias resueltas)

    Returns:
        Métricas agregadas del sistema
    """
    try:
        return get_incidents_summary()
    except Exception as e:
        print(f"Error calculating summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al calcular métricas")


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Obtener detalle de incidencia por UUID (protegido).

    Args:
        - **incident_id**: UUID de la incidencia

    Returns:
        Detalle completo de la incidencia

    Raises:
        - **404**: Incidencia no encontrada
    """
    return get_incident_by_uuid(incident_id)


@router.patch("/{incident_id}/status", response_model=IncidentResponse)
async def update_status_endpoint(
    incident_id: str,
    status_data: IncidentStatusUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Actualizar estado de incidencia (protegido, máquina de estados).

    Máquina de estados (transiciones permitidas):
    - open → in_progress, discarded
    - in_progress → resolved, discarded
    - resolved → (terminal, sin transiciones)
    - discarded → (terminal, sin transiciones)

    Args:
        - **status**: Nuevo estado
        - **satisfaction**: Opcional (1-5), recomendado para resolved

    Returns:
        Incidencia actualizada

    Raises:
        - **400**: Transición de estado inválida
        - **404**: Incidencia no encontrada
    """
    return update_incident_status(incident_id, status_data)


@router.put("/{incident_id}", response_model=IncidentResponse)
async def update_incident_endpoint(
    incident_id: str,
    data: IncidentUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Actualizar campos de incidencia (protegido, no status).

    No permite actualizar estado (usar PATCH /status).
    No permite actualizar incidencias en estado terminal (resolved/discarded).

    Args:
        - **title**: Nuevo título (opcional)
        - **description**: Nueva descripción (opcional)
        - **category**: Nueva categoría (opcional)
        - **branch**: Nueva sede (opcional)

    Returns:
        Incidencia actualizada

    Raises:
        - **400**: Incidencia en estado terminal
        - **404**: Incidencia no encontrada
    """
    return update_incident_fields(incident_id, data)
