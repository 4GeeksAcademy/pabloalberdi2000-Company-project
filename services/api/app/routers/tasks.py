"""
Tasks Router - Async Task Management

Endpoints para encolar y monitorear tareas asíncronas procesadas por Celery.

Arquitectura:
- Patrón Productor/Consumidor: API encola, Workers procesan
- Respuesta inmediata: 202 Accepted con task_id
- Consulta de estado: GET /tasks/{task_id}

Endpoints:
- POST /tasks/telemetry/batch: Encolar procesamiento de lote
- POST /tasks/reports/generate: Encolar generación de reporte
- GET /tasks/{task_id}: Consultar estado de tarea
- GET /tasks: Listar tareas recientes
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.celery_app import (
    process_telemetry_batch,
    generate_business_report,
    get_task_status
)

# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks - Async Processing"]
)


# ============================================================
# SCHEMAS
# ============================================================

class TaskEnqueueResponse(BaseModel):
    """Respuesta tras encolar una tarea."""
    task_id: str = Field(..., description="UUID de la tarea encolada")
    status: str = Field(default="pending", description="Estado inicial: pending")
    message: str = Field(..., description="Mensaje de confirmación")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "status": "pending",
                "message": "Tarea encolada exitosamente. Usa task_id para consultar progreso."
            }
        }


class TaskStatusResponse(BaseModel):
    """Estado de una tarea asíncrona."""
    task_id: str = Field(..., description="UUID de la tarea")
    status: str = Field(..., description="pending | started | success | failure | retry")
    result: Optional[Dict[str, Any]] = Field(None, description="Resultado si completó exitosamente")
    error: Optional[str] = Field(None, description="Mensaje de error si falló")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "status": "success",
                "result": {
                    "batch_id": 123,
                    "events_processed": 1500,
                    "kpis_calculated": 45,
                    "duration_seconds": 120.5
                },
                "error": None
            }
        }


class ProcessBatchRequest(BaseModel):
    """Request para procesar lote de telemetría."""
    batch_id: int = Field(..., description="ID del lote de eventos", gt=0)

    class Config:
        json_schema_extra = {
            "example": {
                "batch_id": 123
            }
        }


class GenerateReportRequest(BaseModel):
    """Request para generar reporte de negocio."""
    report_id: int = Field(..., description="ID del reporte a generar", gt=0)
    start_date: str = Field(..., description="Fecha inicio (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., description="Fecha fin (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$")

    class Config:
        json_schema_extra = {
            "example": {
                "report_id": 456,
                "start_date": "2026-10-01",
                "end_date": "2026-10-31"
            }
        }


# ============================================================
# ENDPOINTS - PRODUCTORES (Encolar Tareas)
# ============================================================

@router.post(
    "/telemetry/batch",
    response_model=TaskEnqueueResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Encolar procesamiento de lote de telemetría",
    description="""
    Encola el procesamiento asíncrono de un lote de eventos de telemetría.

    **Operación**: Calcular KPIs (DAU, disponibilidad, tasas de éxito) y persistir resultados.

    **Respuesta inmediata**: El endpoint retorna 202 Accepted en <200ms con un task_id.

    **Procesamiento real**: Ejecutado por workers Celery en background.

    **Consultar progreso**: Usar `GET /tasks/{task_id}` con el task_id retornado.

    **Reintentos automáticos**: 3 intentos con backoff exponencial (60s, 120s, 240s).

    **Dead Letter Queue**: Tareas que agotan reintentos se persisten en `failed_tasks`.
    """
)
async def enqueue_process_batch(request: ProcessBatchRequest) -> TaskEnqueueResponse:
    """
    Encola procesamiento de lote de telemetría.

    Patrón Productor: API solo encola, worker procesa.
    """
    # Encolar tarea (operación ligera, <10ms)
    task = process_telemetry_batch.delay(batch_id=request.batch_id)

    return TaskEnqueueResponse(
        task_id=task.id,
        status="pending",
        message=f"Lote {request.batch_id} encolado. Usa task_id para consultar progreso."
    )


@router.post(
    "/reports/generate",
    response_model=TaskEnqueueResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Encolar generación de reporte de negocio",
    description="""
    Encola la generación asíncrona de un reporte de negocio (PDF/Excel).

    **Operación**: Consultar KPIs, calcular agregaciones, generar archivo.

    **Respuesta inmediata**: 202 Accepted en <200ms con task_id.

    **Tiempo estimado**: 30-60 segundos dependiendo del rango de fechas.

    **Consultar resultado**: Usar `GET /tasks/{task_id}` para obtener file_path del reporte.
    """
)
async def enqueue_generate_report(request: GenerateReportRequest) -> TaskEnqueueResponse:
    """
    Encola generación de reporte de negocio.

    Patrón Productor: API solo encola, worker genera reporte.
    """
    # Validar fechas (orden lógico)
    if request.start_date > request.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date debe ser anterior o igual a end_date"
        )

    # Encolar tarea
    task = generate_business_report.delay(
        report_id=request.report_id,
        start_date=request.start_date,
        end_date=request.end_date
    )

    return TaskEnqueueResponse(
        task_id=task.id,
        status="pending",
        message=f"Reporte {request.report_id} encolado. Usa task_id para consultar progreso."
    )


# ============================================================
# ENDPOINTS - CONSUMIDORES (Consultar Estado)
# ============================================================

@router.get(
    "/{task_id}",
    response_model=TaskStatusResponse,
    summary="Consultar estado de tarea",
    description="""
    Consulta el estado actual de una tarea asíncrona por su ID.

    **Estados posibles**:
    - `pending`: Tarea encolada, aún no iniciada por worker
    - `started`: Worker procesando la tarea
    - `success`: Tarea completada exitosamente (campo `result` disponible)
    - `failure`: Tarea falló tras agotar reintentos (campo `error` disponible)
    - `retry`: Tarea falló, reintentando automáticamente

    **Polling**: Cliente debe hacer polling cada 2-5 segundos hasta obtener `success` o `failure`.

    **Caducidad**: Resultados expiran tras 1 hora (configuración de Redis).
    """
)
async def get_task_status_endpoint(task_id: str) -> TaskStatusResponse:
    """
    Consulta estado de tarea por ID.

    Retorna estado actual y resultado si está disponible.
    """
    task_status = get_task_status(task_id)

    return TaskStatusResponse(
        task_id=task_status["task_id"],
        status=task_status["status"],
        result=task_status.get("result"),
        error=task_status.get("error")
    )


@router.get(
    "",
    summary="Listar tareas recientes (TODO)",
    description="""
    Lista tareas recientes con paginación.

    **Status**: No implementado aún.

    **Implementación futura**: Consultar Redis o tabla de auditoría.
    """
)
async def list_tasks() -> Dict[str, str]:
    """
    Lista tareas recientes.

    TODO: Implementar consulta a Redis o BD.
    """
    return {
        "message": "Endpoint no implementado. Usar Flower (puerto 5555) para monitoreo.",
        "flower_url": "http://localhost:5555"
    }
