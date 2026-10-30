"""
Telemetry Router - Event Ingestion con Persistencia Supabase

Router para captura de eventos de telemetría con persistencia en PostgreSQL.
Arquitectura resiliente: validación parcial + bulk insert.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Counter
from pydantic import ValidationError
from sqlmodel import Session, text
import logging
import uuid
from datetime import datetime

from app.schemas.telemetry import TelemetryEvent, TelemetryBatchResponse
from app.database_supabase import get_inventory_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/telemetry",
    tags=["telemetry"]
)


@router.post("/events", response_model=TelemetryBatchResponse, status_code=200)
async def ingest_telemetry_batch(
    body: dict,  # ← Envelope laxo: recibe dict crudo, NO TelemetryBatchRequest tipado
    db: Session = Depends(get_inventory_db)
):
    """
    Endpoint real de ingestion de eventos de telemetría con persistencia Supabase.

    **Arquitectura Resiliente:**
    - Validación parcial por evento (un evento inválido no tira abajo el lote)
    - Bulk insert en una sola transacción (evita saturar pool de conexiones)
    - Retorna siempre HTTP 200 con desglose: received/stored/rejected

    **Contrato HTTP:**
    - Body: {"events": [{"eventId": "...", "timestamp": "...", ...}, ...]}
    - Response: {"received": N, "stored": M, "rejected": R} donde N = M + R
    - Status: 200 OK (SIEMPRE, incluso si algunos eventos fallan validación)

    **Invariantes:**
    - Frontend NO sufre cambios (URL, payload y contrato HTTP idénticos)
    - Eventos válidos se persisten SIEMPRE (aislados de los inválidos)
    - Base de datos NUNCA bloquea ingestion (bulk insert transaccional)

    Args:
        body: Dict crudo con clave "events" (lista de dicts de eventos)
        db: Sesión de Supabase (inyectada por dependency)

    Returns:
        TelemetryBatchResponse con desglose de eventos procesados

    Raises:
        HTTPException 500: Solo si falla bulk insert en base de datos
    """
    try:
        # ============================================================
        # 1. PARSEO LAXO: Extraer lista cruda de eventos
        # ============================================================

        raw_events = body.get("events", [])
        total_received = len(raw_events)

        if not isinstance(raw_events, list):
            logger.warning("⚠️ Body 'events' no es una lista")
            return TelemetryBatchResponse(
                received=0,
                stored=0,
                rejected=0
            )

        if total_received == 0:
            logger.info("📭 Batch vacío recibido")
            return TelemetryBatchResponse(
                received=0,
                stored=0,
                rejected=0
            )

        # ============================================================
        # 2. VALIDACIÓN PARCIAL: Parsear cada evento individualmente
        # ============================================================

        valid_events = []
        rejected_count = 0
        event_type_counts = Counter()

        for idx, raw_event in enumerate(raw_events):
            try:
                # Validar con Pydantic (puede lanzar ValidationError)
                validated_event = TelemetryEvent.model_validate(raw_event)
                valid_events.append(validated_event)
                event_type_counts[validated_event.event_type] += 1

            except ValidationError as e:
                rejected_count += 1
                logger.warning(
                    f"⚠️ Evento {idx + 1}/{total_received} rechazado: "
                    f"{e.error_count()} errores | "
                    f"Snippet: {str(raw_event)[:100]}..."
                )
                # Continuar con siguiente evento (resiliente)
                continue

        stored_count = len(valid_events)

        # Log agregado
        logger.info(
            f"📊 Telemetry batch: {total_received} received | "
            f"{stored_count} valid | {rejected_count} rejected | "
            f"Types: {dict(event_type_counts)}"
        )

        # ============================================================
        # 3. BULK INSERT: Persistir eventos válidos en una transacción
        # ============================================================

        if stored_count == 0:
            logger.warning("⚠️ Ningún evento válido en el batch")
            return TelemetryBatchResponse(
                received=total_received,
                stored=0,
                rejected=rejected_count
            )

        # Generar batch_id para correlación
        batch_id = str(uuid.uuid4())

        # Transformar eventos válidos a filas SQL
        rows = []
        for event in valid_events:
            row = {
                "event_id": event.eventId,
                "event_type": event.event_type,
                "timestamp": event.timestamp,
                "session_id": event.sessionId,
                "user_id": event.userId,
                "request_id": event.requestId,
                "schema_version": event.schemaVersion,
                "service": "backoffice",  # Hardcoded (multi-service en Fase 2)
                "tags": event.properties,  # JSONB
                "batch_id": batch_id,
            }
            rows.append(row)

        # Bulk insert con SQLAlchemy Core (más eficiente que ORM)
        insert_stmt = text("""
            INSERT INTO telemetry_events (
                event_id,
                event_type,
                timestamp,
                session_id,
                user_id,
                request_id,
                schema_version,
                service,
                tags,
                batch_id
            )
            VALUES (
                :event_id,
                :event_type,
                :timestamp,
                :session_id,
                :user_id,
                :request_id,
                :schema_version,
                :service,
                :tags::jsonb,
                :batch_id
            )
        """)

        # Ejecutar bulk insert en transacción
        try:
            for row in rows:
                db.execute(insert_stmt, row)

            db.commit()

            logger.info(
                f"✅ Bulk insert exitoso: {stored_count} eventos | "
                f"batch_id={batch_id[:8]}..."
            )

        except Exception as db_error:
            db.rollback()
            logger.error(
                f"❌ Bulk insert fallido: {type(db_error).__name__}: {str(db_error)}"
            )
            raise HTTPException(
                status_code=500,
                detail="Database insertion failed. Events not persisted."
            )

        # ============================================================
        # 4. RESPUESTA: Desglose de eventos procesados
        # ============================================================

        return TelemetryBatchResponse(
            received=total_received,
            stored=stored_count,
            rejected=rejected_count
        )

    except HTTPException:
        # Re-lanzar HTTPException sin modificar
        raise

    except Exception as e:
        # Log error inesperado
        logger.error(
            f"❌ Telemetry ingestion error: {type(e).__name__}: {str(e)}"
        )
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
