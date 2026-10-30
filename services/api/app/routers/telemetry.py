"""
Telemetry Router - Event Ingestion Stub

Router dedicado para captura de eventos de telemetría.
MVP: Stub que valida y loguea eventos sin persistencia (preparación para pipeline real).
"""
from fastapi import APIRouter, HTTPException
from typing import Counter
import logging

from app.schemas.telemetry import TelemetryBatchRequest, TelemetryBatchResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/telemetry",
    tags=["telemetry"]
)


@router.post("/events", response_model=TelemetryBatchResponse, status_code=200)
async def ingest_telemetry_batch(
    batch: TelemetryBatchRequest
):
    """
    Endpoint stub de ingestion de eventos de telemetría.

    **MVP Behavior (Fase 1):**
    - Valida estructura del Event Envelope (Pydantic automático)
    - Registra en logs la cantidad y tipos de eventos recibidos
    - Retorna confirmación de recepción

    **Producción (Fase 2):**
    - Validación contra schemas en event-schemas.json (allowlists estrictos)
    - Enrutamiento a pipeline Stream vs Batch según event_type
    - Sanitización de PII (emails, IPs, stack traces)
    - Persistencia en PostgreSQL JSONB + eventual Kafka/S3

    Args:
        batch: Lote de eventos (1-100 eventos por request)

    Returns:
        TelemetryBatchResponse con cantidad de eventos procesados

    Raises:
        HTTPException 400: Si la validación Pydantic falla
        HTTPException 500: Si ocurre un error interno
    """
    try:
        events = batch.events
        total_events = len(events)

        # Contar event_types para logging agregado
        event_type_counts = Counter(event.event_type for event in events)

        # Log agregado (no loguear individualmente cada evento para evitar spam)
        logger.info(
            f"📊 Telemetry batch received: {total_events} events | "
            f"Types: {dict(event_type_counts)}"
        )

        # Log detallado solo en desarrollo (comentar en producción)
        for event in events:
            logger.debug(
                f"  └─ {event.event_type} | "
                f"eventId={event.eventId[:8]}... | "
                f"userId={event.userId or 'null'} | "
                f"sessionId={event.sessionId or 'null'}"
            )

        # TODO (Fase 2): Validación contra event-schemas.json
        # TODO (Fase 2): Sanitización de PII en properties
        # TODO (Fase 2): Enrutamiento Stream (Kafka) vs Batch (S3)
        # TODO (Fase 2): Persistencia en PostgreSQL events table

        return TelemetryBatchResponse(
            received=total_events,
            status="success"
        )

    except Exception as e:
        # Log error sin exponer detalles internos al cliente
        logger.error(f"❌ Telemetry ingestion error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process telemetry batch. Please try again later."
        )


@router.get("/health")
async def telemetry_health():
    """
    Health check del servicio de telemetría.

    En producción verificaría:
    - Conexión a Kafka/base de datos
    - Estado de la cola de procesamiento
    - Latencia promedio de ingestion
    """
    return {
        "status": "healthy",
        "service": "telemetry-ingestion",
        "version": "1.0.0-stub",
        "mode": "MVP (no persistence)"
    }
