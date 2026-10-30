"""
Telemetry Report Router - Analytics Endpoint with In-Memory Cache

Endpoint de reporte operativo de telemetría optimizado con caché en memoria.

Características:
- GET /telemetry/report con parámetros opcionales start_date y end_date
- Ventana móvil por defecto: últimos 7 días
- Caché en memoria con TTL de 60 segundos por combinación de parámetros
- Cero recalculación en cada request (prohibido)
- Respuesta estandarizada con periodo y métricas
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from sqlmodel import Session
import logging
import time

from app.services.telemetry_analysis import generate_telemetry_report
from app.database_supabase import get_inventory_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/telemetry",
    tags=["telemetry-analytics"]
)


# ============================================================
# CACHÉ EN MEMORIA (TTL: 60 segundos)
# ============================================================

# Estructura del caché: {(start_iso, end_iso): (timestamp, report_data)}
_report_cache: Dict[Tuple[str, str], Tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 60


def get_cached_report(
    start_date: datetime,
    end_date: datetime,
    db: Session
) -> Dict[str, Any]:
    """
    Obtiene reporte desde caché o lo genera si no existe o expiró.

    Estrategia de caché:
    - Key: (start_date_iso, end_date_iso)
    - Value: (timestamp_creación, report_data)
    - TTL: 60 segundos
    - Limpieza: Al verificar cache, elimina entradas expiradas

    Args:
        start_date: Inicio del rango (datetime UTC)
        end_date: Fin del rango (datetime UTC)
        db: Sesión de Supabase

    Returns:
        Dict con reporte completo
    """
    # Crear key del caché (ISO strings para hashable key)
    cache_key = (start_date.isoformat(), end_date.isoformat())
    current_time = time.time()

    # ============================================================
    # 1. Limpiar entradas expiradas del caché (garbage collection)
    # ============================================================

    expired_keys = [
        key for key, (timestamp, _) in _report_cache.items()
        if current_time - timestamp > CACHE_TTL_SECONDS
    ]

    for key in expired_keys:
        del _report_cache[key]
        logger.debug(f"🗑️ Cache entry expired: {key}")

    # ============================================================
    # 2. Verificar si existe entrada válida en caché
    # ============================================================

    if cache_key in _report_cache:
        cached_timestamp, cached_report = _report_cache[cache_key]

        # Verificar si aún está dentro del TTL
        age = current_time - cached_timestamp

        if age < CACHE_TTL_SECONDS:
            logger.info(
                f"✅ Cache HIT: Reporte servido desde caché (age: {age:.1f}s)"
            )
            return cached_report
        else:
            # Expiró, eliminar del caché
            del _report_cache[cache_key]
            logger.debug(f"🗑️ Cache entry expired on access: {cache_key}")

    # ============================================================
    # 3. Cache MISS: Generar reporte y almacenar en caché
    # ============================================================

    logger.info(f"❌ Cache MISS: Generando reporte...")

    report = generate_telemetry_report(start_date, end_date, db)

    # Almacenar en caché con timestamp actual
    _report_cache[cache_key] = (current_time, report)

    logger.info(
        f"💾 Reporte almacenado en caché: {cache_key} | "
        f"Cache size: {len(_report_cache)} entradas"
    )

    return report


# ============================================================
# ENDPOINT: GET /telemetry/report
# ============================================================

@router.get("/report")
async def get_telemetry_report(
    start_date: Optional[str] = Query(
        None,
        description="Fecha de inicio en formato ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ). Si no se provee, usa últimos 7 días.",
        example="2026-10-23T00:00:00Z"
    ),
    end_date: Optional[str] = Query(
        None,
        description="Fecha de fin en formato ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ). Si no se provee, usa NOW.",
        example="2026-10-30T00:00:00Z"
    ),
    db: Session = Depends(get_inventory_db)
):
    """
    Genera reporte operativo de telemetría con métricas de volumen, errores y autenticación.

    **Ventana móvil por defecto**: Últimos 7 días si no se especifican fechas.

    **Parámetros**:
    - `start_date` (opcional): Inicio del periodo en ISO 8601 UTC
    - `end_date` (opcional): Fin del periodo en ISO 8601 UTC

    **Respuesta**:
    ```json
    {
        "period": {
            "from": "2026-10-23T00:00:00+00:00",
            "to": "2026-10-30T00:00:00+00:00"
        },
        "metrics": {
            "events_per_day": [
                {"date": "2026-10-23", "event_count": 150},
                {"date": "2026-10-24", "event_count": 200}
            ],
            "error_rate_by_type": [
                {
                    "event_type": "frontend_error_uncaught",
                    "total_events": 25,
                    "error_events": 25,
                    "error_rate": 1.0
                }
            ],
            "auth_failure_rate": [
                {
                    "date": "2026-10-23",
                    "total_attempts": 100,
                    "failed_attempts": 15,
                    "success_attempts": 85,
                    "failure_rate": 0.15
                }
            ]
        }
    }
    ```

    **Caché**: TTL de 60 segundos por combinación de parámetros de fecha.

    **Ejemplos de uso**:
    ```bash
    # Últimos 7 días (ventana móvil por defecto)
    GET /telemetry/report

    # Periodo específico
    GET /telemetry/report?start_date=2026-10-01T00:00:00Z&end_date=2026-10-31T00:00:00Z

    # Solo desde una fecha hasta ahora
    GET /telemetry/report?start_date=2026-10-25T00:00:00Z
    ```

    **Errores**:
    - 400: Formato de fecha inválido
    - 422: start_date >= end_date (rango inválido)
    - 500: Error en pipeline analítico
    """
    try:
        # ============================================================
        # 1. RESOLUCIÓN DE RANGO DE FECHAS (una sola vez)
        # ============================================================

        now_utc = datetime.now(timezone.utc)

        # Parsear end_date o usar NOW por defecto
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Formato de end_date inválido: {end_date}. Usar ISO 8601 UTC (ej: 2026-10-30T00:00:00Z)"
                )
        else:
            end_dt = now_utc

        # Parsear start_date o calcular ventana móvil de 7 días
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Formato de start_date inválido: {start_date}. Usar ISO 8601 UTC (ej: 2026-10-23T00:00:00Z)"
                )
        else:
            # Ventana móvil por defecto: últimos 7 días
            start_dt = end_dt - timedelta(days=7)

        # Validar que start_date < end_date
        if start_dt >= end_dt:
            raise HTTPException(
                status_code=422,
                detail=f"start_date debe ser menor que end_date. Recibido: start={start_dt.isoformat()}, end={end_dt.isoformat()}"
            )

        logger.info(
            f"📊 Request de reporte: {start_dt.date()} a {end_dt.date()} "
            f"(ventana: {(end_dt - start_dt).days} días)"
        )

        # ============================================================
        # 2. OBTENER REPORTE (desde caché o generar)
        # ============================================================

        report = get_cached_report(start_dt, end_dt, db)

        return report

    except HTTPException:
        # Re-raise HTTPException tal cual (400, 422)
        raise

    except Exception as e:
        logger.error(
            f"❌ Error generando reporte de telemetría: {type(e).__name__}: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail="Error interno al generar reporte de telemetría. Ver logs del servidor."
        )


# ============================================================
# ENDPOINT DE UTILIDAD: Limpiar Caché Manual
# ============================================================

@router.delete("/report/cache")
async def clear_report_cache():
    """
    Limpia manualmente el caché de reportes de telemetría.

    **Uso**: Para forzar recalculación inmediata sin esperar TTL.

    **Respuesta**:
    ```json
    {
        "cleared_entries": 5,
        "message": "Caché limpiado exitosamente"
    }
    ```
    """
    global _report_cache

    cleared_count = len(_report_cache)
    _report_cache.clear()

    logger.info(f"🗑️ Caché limpiado manualmente: {cleared_count} entradas eliminadas")

    return {
        "cleared_entries": cleared_count,
        "message": "Caché limpiado exitosamente"
    }


# ============================================================
# ENDPOINT DE HEALTH CHECK
# ============================================================

@router.get("/report/health")
async def report_health_check():
    """
    Health check del servicio de reportes de telemetría.

    **Respuesta**:
    ```json
    {
        "status": "healthy",
        "cache_entries": 3,
        "cache_ttl_seconds": 60
    }
    ```
    """
    return {
        "status": "healthy",
        "cache_entries": len(_report_cache),
        "cache_ttl_seconds": CACHE_TTL_SECONDS
    }
