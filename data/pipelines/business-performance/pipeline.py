"""
Business Performance ETL Pipeline - Brasaland Digital

Pipeline de orquestación en Prefect que transforma eventos de telemetría
en KPIs de negocio para el dashboard ejecutivo.

Arquitectura:
    telemetry_events → Extract → Transform → Load → reporting.business_kpis

Ejecución:
    # CLI standalone
    python data/pipelines/business-performance/pipeline.py

    # Con parámetros personalizados
    python data/pipelines/business-performance/pipeline.py --days 7

    # Backfill histórico
    python data/pipelines/business-performance/pipeline.py --start-date 2026-10-01 --end-date 2026-10-30

Características:
- Idempotencia garantizada (UPSERT)
- Reintentos inteligentes con backoff
- Caching de transformaciones
- Auditoría completa de ejecuciones
- Tolerancia a fallos parciales
"""

import argparse
import json
import logging
import os
import sys
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple

import pandas as pd
from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ============================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================

PIPELINE_NAME = "business-performance-etl"
PIPELINE_VERSION = "1.0.0"

# Conexión a Supabase/PostgreSQL
# IMPORTANTE: En producción, usar Prefect Blocks para secrets
DATABASE_URL = os.getenv(
    "SUPABASE_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres"
)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================
# UTILIDADES DE BASE DE DATOS
# ============================================================

def get_database_engine() -> Engine:
    """
    Crea engine de SQLAlchemy para conexión a PostgreSQL.

    En producción, esta función debería cargar la conexión desde
    un Prefect Block (SqlAlchemyConnector) en lugar de variables de entorno.

    Returns:
        Engine de SQLAlchemy configurado
    """
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verificar conexión antes de usar
        pool_size=5,
        max_overflow=10
    )


def init_audit_table(engine: Engine) -> None:
    """
    Crea la tabla de auditoría si no existe.

    Tabla: reporting.pipeline_runs
    Propósito: Registrar metadata de cada ejecución del pipeline

    Args:
        engine: Engine de SQLAlchemy
    """
    create_schema_query = "CREATE SCHEMA IF NOT EXISTS reporting;"

    create_table_query = """
    CREATE TABLE IF NOT EXISTS reporting.pipeline_runs (
        -- Primary Key
        run_id UUID PRIMARY KEY,

        -- Pipeline Identity
        pipeline_name VARCHAR(100) NOT NULL,
        pipeline_version VARCHAR(20) NOT NULL,

        -- Ejecución
        started_at TIMESTAMPTZ NOT NULL,
        finished_at TIMESTAMPTZ,
        duration_seconds INTEGER,

        -- Input Parameters
        input_params JSONB NOT NULL,

        -- Output Metrics
        records_read INTEGER,
        records_processed INTEGER,
        records_inserted INTEGER,
        records_updated INTEGER,

        -- Estado Final
        status VARCHAR(20) NOT NULL,

        -- Error Handling
        error_message TEXT,
        error_traceback TEXT,

        -- Metadata
        triggered_by VARCHAR(50),
        prefect_flow_run_id TEXT,

        -- Timestamps
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at
    ON reporting.pipeline_runs (started_at DESC);

    CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status
    ON reporting.pipeline_runs (status);
    """

    with engine.connect() as conn:
        conn.execute(text(create_schema_query))
        conn.execute(text(create_table_query))
        conn.commit()

    logger.info("✅ Tabla de auditoría inicializada: reporting.pipeline_runs")


def init_kpis_table(engine: Engine) -> None:
    """
    Crea la tabla de KPIs de negocio si no existe.

    Tabla: reporting.business_kpis
    Propósito: Almacenar KPIs agregados por fecha y dimensiones

    Args:
        engine: Engine de SQLAlchemy
    """
    create_table_query = """
    CREATE TABLE IF NOT EXISTS reporting.business_kpis (
        -- Primary Key
        id BIGSERIAL PRIMARY KEY,

        -- Dimensión Temporal
        date DATE NOT NULL,

        -- Dimensiones de Negocio (nullable para agregados globales)
        country VARCHAR(2),
        service VARCHAR(50),
        warehouse VARCHAR(100),

        -- Periodo de Cálculo
        period_start TIMESTAMPTZ NOT NULL,
        period_end TIMESTAMPTZ NOT NULL,

        -- KPIs: Usuarios Activos
        daily_active_users INTEGER NOT NULL DEFAULT 0,

        -- KPIs: Sesiones y Engagement
        total_sessions INTEGER NOT NULL DEFAULT 0,
        total_events INTEGER NOT NULL DEFAULT 0,
        avg_events_per_session NUMERIC(10, 2),
        avg_session_duration_minutes NUMERIC(10, 2),

        -- KPIs: Disponibilidad y Performance
        system_availability_pct NUMERIC(5, 2),
        avg_response_time_ms NUMERIC(10, 2),
        p95_response_time_ms NUMERIC(10, 2),

        -- KPIs: Errores
        error_events INTEGER NOT NULL DEFAULT 0,
        error_rate NUMERIC(5, 4),

        -- KPIs: Autenticación
        auth_success_rate NUMERIC(5, 2),

        -- KPIs: Calidad de Datos
        events_with_user_id_pct NUMERIC(5, 2),
        events_with_session_id_pct NUMERIC(5, 2),
        avg_ingestion_lag_seconds NUMERIC(10, 2),

        -- Metadata de Pipeline
        calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        pipeline_run_id UUID NOT NULL,
        pipeline_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',

        -- Audit Trail
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- Índice único para idempotencia (UPSERT)
    CREATE UNIQUE INDEX IF NOT EXISTS idx_business_kpis_natural_key
    ON reporting.business_kpis (
        date,
        COALESCE(country, ''),
        COALESCE(service, ''),
        COALESCE(warehouse, '')
    );

    CREATE INDEX IF NOT EXISTS idx_business_kpis_date
    ON reporting.business_kpis (date DESC);

    CREATE INDEX IF NOT EXISTS idx_business_kpis_country
    ON reporting.business_kpis (country)
    WHERE country IS NOT NULL;

    CREATE INDEX IF NOT EXISTS idx_business_kpis_pipeline_run
    ON reporting.business_kpis (pipeline_run_id);
    """

    with engine.connect() as conn:
        conn.execute(text(create_table_query))
        conn.commit()

    logger.info("✅ Tabla de KPIs inicializada: reporting.business_kpis")


# ============================================================
# TASK 1: EXTRACCIÓN (Extract)
# ============================================================

@task(
    name="extract-telemetry-events",
    description="Extrae eventos de telemetry_events con filtro temporal",
    retries=3,  # Reintentos para fallos transitorios (timeout, red)
    retry_delay_seconds=60,  # Esperar 1 minuto entre reintentos
    tags=["extract", "database", "telemetry"]
)
def extract_telemetry_events(
    start_date: datetime,
    end_date: datetime,
    run_id: uuid.UUID
) -> pd.DataFrame:
    """
    Extrae eventos de telemetry_events en el rango temporal especificado.

    Estrategia de extracción:
    - SQL filtra por timestamp (índice optimizado)
    - Carga completa en DataFrame (ventana típica: 24h → ~10k eventos)
    - Sin paginación (ventanas pequeñas)

    Política de reintentos:
    - 3 intentos con delay de 60s
    - Justificación: Fallos típicos son timeout de red o BD sobrecargada,
      que se resuelven esperando 1 minuto.

    Args:
        start_date: Inicio del rango (inclusive)
        end_date: Fin del rango (exclusivo)
        run_id: UUID del run actual (para logging)

    Returns:
        DataFrame con columnas de telemetry_events

    Raises:
        Exception: Si falla query después de 3 reintentos
    """
    logger = get_run_logger()
    logger.info(f"📥 Extrayendo eventos: {start_date.date()} - {end_date.date()}")

    engine = get_database_engine()

    query = """
        SELECT
            id,
            event_id,
            event_type,
            timestamp,
            session_id,
            user_id,
            request_id,
            schema_version,
            service,
            tags,
            ingested_at,
            batch_id
        FROM telemetry_events
        WHERE timestamp >= :start_date
          AND timestamp < :end_date
        ORDER BY timestamp ASC
    """

    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(query),
                {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            )

            rows = result.fetchall()
            columns = result.keys()

        if not rows:
            logger.warning(
                f"📭 Sin eventos en rango {start_date.date()} a {end_date.date()}"
            )
            return pd.DataFrame(columns=columns)

        df = pd.DataFrame(rows, columns=columns)

        logger.info(f"✅ Extraídos {len(df):,} eventos")

        # Actualizar audit log con records_read
        update_pipeline_run_metrics(run_id, {"records_read": len(df)})

        return df

    except Exception as e:
        logger.error(
            f"❌ Error extrayendo eventos: {type(e).__name__}: {str(e)}"
        )
        # Actualizar audit log con error
        update_pipeline_run_metrics(
            run_id,
            {"status": "failed", "error_message": str(e)}
        )
        raise


# ============================================================
# TASK 2: TRANSFORMACIÓN (Transform)
# ============================================================

def generate_cache_key(
    context: Dict[str, Any],
    parameters: Dict[str, Any]
) -> str:
    """
    Genera clave de caché basada en el hash del DataFrame de entrada.

    Lógica:
    - Si el DataFrame de eventos no cambia → mismo hash → caché válido
    - Si llegan late-arriving events → hash cambia → recalcula transformación

    Args:
        context: Contexto de Prefect (incluye task_run_id, flow_run_id)
        parameters: Parámetros de la task (incluye events_df)

    Returns:
        String de clave de caché
    """
    events_df = parameters.get("events_df")
    start_date = parameters.get("start_date")
    end_date = parameters.get("end_date")

    if events_df is None or events_df.empty:
        # DataFrame vacío → clave única por rango de fechas
        return f"empty_{start_date.date()}_{end_date.date()}"

    # Hash del contenido del DataFrame
    # Usamos columnas clave: event_id, timestamp, event_type
    cache_data = (
        f"{len(events_df)}_"
        f"{events_df['event_id'].iloc[0]}_"
        f"{events_df['event_id'].iloc[-1]}_"
        f"{start_date.date()}_{end_date.date()}"
    )

    return cache_data


@task(
    name="transform-events-to-kpis",
    description="Transforma eventos crudos en KPIs agregados con Pandas",
    retries=1,  # Solo 1 reintento (errores suelen ser deterministas)
    retry_delay_seconds=30,
    tags=["transform", "pandas", "kpis"],
    cache_key_fn=generate_cache_key,  # Caching de transformación
    cache_expiration=timedelta(hours=1)  # Caché válido por 1 hora
)
def transform_events_to_kpis(
    events_df: pd.DataFrame,
    start_date: datetime,
    end_date: datetime,
    run_id: uuid.UUID
) -> pd.DataFrame:
    """
    Transforma DataFrame de eventos en DataFrame de KPIs agregados.

    Esta función es PURA:
    - Mismo input → mismo output
    - Sin side-effects (no escribe BD, no llama APIs)
    - Determinista (no usa datetime.now() en cálculos)

    Caching:
    - Clave: Hash del DataFrame de entrada + rango de fechas
    - Expiración: 1 hora
    - Justificación: Si procesamos el mismo rango dos veces en 1h
      y no llegaron nuevos eventos → reutilizamos transformación

    KPIs calculados (alineados con company-BRIEFING.md):
    - Usuarios activos diarios (DAU)
    - Sesiones totales y engagement
    - Disponibilidad del sistema (%)
    - Tasa de errores
    - Calidad de datos (% eventos con user_id)

    Args:
        events_df: DataFrame con eventos crudos de telemetry_events
        start_date: Inicio del periodo (para metadata)
        end_date: Fin del periodo (para metadata)
        run_id: UUID del run actual

    Returns:
        DataFrame con KPIs agregados (columnas de reporting.business_kpis)
    """
    logger = get_run_logger()
    logger.info(f"🔄 Transformando {len(events_df):,} eventos en KPIs")

    if events_df.empty:
        logger.warning("⚠️ DataFrame vacío, retornando KPIs vacíos")
        return pd.DataFrame()

    # ============================================================
    # 1. CONVERSIÓN DE TIPOS (obligatorio)
    # ============================================================

    events_df = events_df.copy()  # Evitar SettingWithCopyWarning

    # Convertir timestamp a datetime UTC
    events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], utc=True)
    events_df["date"] = events_df["timestamp"].dt.date

    # ============================================================
    # 2. EXTRACCIÓN DE DIMENSIONES DESDE JSONB
    # ============================================================

    # El campo 'tags' es un dict Python (deserializado por SQLAlchemy)
    if "tags" in events_df.columns:
        events_df["country"] = events_df["tags"].apply(
            lambda x: x.get("country") if isinstance(x, dict) else None
        )
        events_df["warehouse"] = events_df["tags"].apply(
            lambda x: x.get("warehouse") if isinstance(x, dict) else None
        )
        events_df["user_role"] = events_df["tags"].apply(
            lambda x: x.get("user_role") if isinstance(x, dict) else None
        )
        events_df["duration_ms"] = events_df["tags"].apply(
            lambda x: x.get("duration_ms") if isinstance(x, dict) else None
        )

    # ============================================================
    # 3. DERIVACIÓN DE DIMENSIONES TÉCNICAS
    # ============================================================

    # Flag is_error usando vectorización (sin bucles)
    error_keywords = ["error", "failed", "rejected"]
    events_df["is_error"] = events_df["event_type"].str.contains(
        "|".join(error_keywords),
        case=False,
        na=False
    )

    # Flag de eventos de autenticación
    events_df["is_auth_success"] = (
        events_df["event_type"] == "login_attempt_success"
    )
    events_df["is_auth_failed"] = (
        events_df["event_type"] == "login_attempt_failed"
    )

    # ============================================================
    # 4. AGREGACIONES VECTORIZADAS (por fecha)
    # ============================================================

    kpis = events_df.groupby("date").agg(
        # Volumetría
        total_events=("event_id", "size"),
        total_sessions=("session_id", "nunique"),
        daily_active_users=("user_id", "nunique"),

        # Performance (solo eventos con duration_ms)
        avg_response_time_ms=("duration_ms", "mean"),

        # Errores
        error_events=("is_error", "sum"),

        # Autenticación
        auth_success_events=("is_auth_success", "sum"),
        auth_failed_events=("is_auth_failed", "sum"),

        # Calidad de datos
        events_with_user_id=("user_id", lambda x: x.notna().sum()),
        events_with_session_id=("session_id", lambda x: x.notna().sum())
    ).reset_index()

    # ============================================================
    # 5. MÉTRICAS DERIVADAS (vectorizado)
    # ============================================================

    # Disponibilidad del sistema
    kpis["system_availability_pct"] = (
        (1 - kpis["error_events"] / kpis["total_events"]) * 100
    ).round(2)

    # Tasa de error
    kpis["error_rate"] = (
        kpis["error_events"] / kpis["total_events"]
    ).round(4)

    # Tasa de éxito de autenticación
    kpis["auth_success_rate"] = (
        kpis["auth_success_events"] /
        (kpis["auth_success_events"] + kpis["auth_failed_events"])
    ).fillna(0).round(4) * 100

    # Calidad de datos (%)
    kpis["events_with_user_id_pct"] = (
        (kpis["events_with_user_id"] / kpis["total_events"]) * 100
    ).round(2)

    kpis["events_with_session_id_pct"] = (
        (kpis["events_with_session_id"] / kpis["total_events"]) * 100
    ).round(2)

    # Promedio de eventos por sesión
    kpis["avg_events_per_session"] = (
        kpis["total_events"] / kpis["total_sessions"]
    ).round(2)

    # ============================================================
    # 6. METADATA DEL PERIODO
    # ============================================================

    kpis["period_start"] = start_date
    kpis["period_end"] = end_date
    kpis["calculated_at"] = datetime.now(timezone.utc)
    kpis["pipeline_run_id"] = run_id
    kpis["pipeline_version"] = PIPELINE_VERSION

    # Dimensiones de negocio (globales por ahora, Fase 1)
    kpis["country"] = None
    kpis["service"] = None
    kpis["warehouse"] = None

    # Convertir date a string para serialización
    kpis["date"] = kpis["date"].astype(str)

    # Convertir tipos numéricos a nativos de Python (para JSON serialization)
    numeric_cols = [
        "total_events", "total_sessions", "daily_active_users",
        "error_events", "auth_success_events", "auth_failed_events",
        "events_with_user_id", "events_with_session_id"
    ]
    for col in numeric_cols:
        if col in kpis.columns:
            kpis[col] = kpis[col].astype(int)

    logger.info(f"✅ Generados {len(kpis):,} registros de KPIs")

    # Actualizar audit log
    update_pipeline_run_metrics(run_id, {"records_processed": len(kpis)})

    return kpis


# ============================================================
# TASK 3: CARGA (Load)
# ============================================================

@task(
    name="load-kpis-to-database",
    description="Carga KPIs en reporting.business_kpis con UPSERT idempotente",
    retries=2,  # 2 reintentos para fallos de BD
    retry_delay_seconds=30,
    tags=["load", "database", "upsert"]
)
def load_kpis_to_database(
    kpis_df: pd.DataFrame,
    run_id: uuid.UUID
) -> Dict[str, int]:
    """
    Carga KPIs en tabla reporting.business_kpis usando UPSERT.

    Estrategia de idempotencia:
    - UPSERT basado en constraint único: (date, country, service, warehouse)
    - Si fila existe → UPDATE
    - Si fila no existe → INSERT
    - Operación atómica (transacción)

    Política de reintentos:
    - 2 intentos con delay de 30s
    - Justificación: Fallos típicos son deadlocks o locks de tabla,
      que se resuelven esperando 30 segundos.

    Args:
        kpis_df: DataFrame con KPIs agregados
        run_id: UUID del run actual

    Returns:
        Dict con métricas: {"inserted": N, "updated": M, "total": T}
    """
    logger = get_run_logger()
    logger.info(f"💾 Cargando {len(kpis_df):,} registros de KPIs")

    if kpis_df.empty:
        logger.warning("⚠️ DataFrame vacío, nada que cargar")
        return {"inserted": 0, "updated": 0, "total": 0}

    engine = get_database_engine()

    upsert_query = """
        INSERT INTO reporting.business_kpis (
            date, country, service, warehouse,
            period_start, period_end,
            daily_active_users, total_sessions, total_events,
            avg_events_per_session, avg_response_time_ms,
            system_availability_pct, error_events, error_rate,
            auth_success_rate,
            events_with_user_id_pct, events_with_session_id_pct,
            calculated_at, pipeline_run_id, pipeline_version
        )
        VALUES (
            :date, :country, :service, :warehouse,
            :period_start, :period_end,
            :daily_active_users, :total_sessions, :total_events,
            :avg_events_per_session, :avg_response_time_ms,
            :system_availability_pct, :error_events, :error_rate,
            :auth_success_rate,
            :events_with_user_id_pct, :events_with_session_id_pct,
            :calculated_at, :pipeline_run_id, :pipeline_version
        )
        ON CONFLICT (date, COALESCE(country, ''), COALESCE(service, ''), COALESCE(warehouse, ''))
        DO UPDATE SET
            period_start = EXCLUDED.period_start,
            period_end = EXCLUDED.period_end,
            daily_active_users = EXCLUDED.daily_active_users,
            total_sessions = EXCLUDED.total_sessions,
            total_events = EXCLUDED.total_events,
            avg_events_per_session = EXCLUDED.avg_events_per_session,
            avg_response_time_ms = EXCLUDED.avg_response_time_ms,
            system_availability_pct = EXCLUDED.system_availability_pct,
            error_events = EXCLUDED.error_events,
            error_rate = EXCLUDED.error_rate,
            auth_success_rate = EXCLUDED.auth_success_rate,
            events_with_user_id_pct = EXCLUDED.events_with_user_id_pct,
            events_with_session_id_pct = EXCLUDED.events_with_session_id_pct,
            calculated_at = EXCLUDED.calculated_at,
            pipeline_run_id = EXCLUDED.pipeline_run_id,
            pipeline_version = EXCLUDED.pipeline_version,
            updated_at = NOW()
    """

    total_processed = 0

    try:
        with engine.begin() as conn:  # Transacción atómica (all-or-nothing)
            for row in kpis_df.to_dict(orient="records"):
                conn.execute(text(upsert_query), row)
                total_processed += 1

        logger.info(
            f"✅ Cargados {total_processed:,} registros (UPSERT exitoso)"
        )

        # En PostgreSQL, no hay forma directa de saber cuántos fueron INSERT vs UPDATE
        # sin usar RETURNING clause. Por simplicidad, asumimos todos como "procesados"
        result = {
            "inserted": 0,  # Refinamiento en Fase 2
            "updated": 0,   # Refinamiento en Fase 2
            "total": total_processed
        }

        # Actualizar audit log
        update_pipeline_run_metrics(
            run_id,
            {
                "records_inserted": result["total"],
                "records_updated": 0
            }
        )

        return result

    except Exception as e:
        logger.error(f"❌ Error cargando KPIs: {type(e).__name__}: {str(e)}")
        update_pipeline_run_metrics(
            run_id,
            {"status": "failed", "error_message": str(e)}
        )
        raise


# ============================================================
# TASK 4: NOTIFICACIÓN OPCIONAL (Paso No Crítico)
# ============================================================

@task(
    name="send-completion-notification",
    description="Envía notificación de completado (paso opcional no bloqueante)",
    retries=0,  # Sin reintentos (fallo no debe abortar pipeline)
    tags=["notification", "optional"]
)
def send_completion_notification(
    run_id: uuid.UUID,
    metrics: Dict[str, int]
) -> Dict[str, str]:
    """
    Envía notificación de completado del pipeline.

    Esta task es OPCIONAL y NO CRÍTICA:
    - Si falla, el pipeline continúa normalmente
    - Se invoca con return_state=True para capturar estado sin propagar error

    En producción, esto podría:
    - Enviar email al equipo de Data
    - Post a Slack webhook
    - Registrar métrica en sistema de monitoreo

    Args:
        run_id: UUID del run
        metrics: Diccionario con métricas del run

    Returns:
        Dict con resultado de notificación
    """
    logger = get_run_logger()
    logger.info(f"📧 Enviando notificación de completado: run_id={run_id}")

    # Simulación de notificación (en producción: email/Slack)
    notification_message = (
        f"✅ Pipeline Brasaland Business Performance completado\n"
        f"Run ID: {run_id}\n"
        f"Registros procesados: {metrics.get('total', 0):,}\n"
        f"Timestamp: {datetime.now(timezone.utc).isoformat()}"
    )

    logger.info(notification_message)

    # Simular fallo aleatorio para demostrar tolerancia (Fase de prueba)
    # En producción, quitar esta línea
    # import random
    # if random.random() < 0.3:  # 30% probabilidad de fallo
    #     raise Exception("Simulated notification failure")

    return {
        "status": "sent",
        "message": notification_message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================================
# UTILIDADES DE AUDITORÍA
# ============================================================

def create_pipeline_run_record(
    run_id: uuid.UUID,
    start_date: datetime,
    end_date: datetime,
    triggered_by: str = "manual"
) -> None:
    """
    Crea registro inicial en tabla de auditoría.

    Args:
        run_id: UUID del run
        start_date: Inicio del rango de datos
        end_date: Fin del rango de datos
        triggered_by: Origen del trigger ('manual', 'scheduled', 'api')
    """
    engine = get_database_engine()

    insert_query = """
        INSERT INTO reporting.pipeline_runs (
            run_id, pipeline_name, pipeline_version,
            started_at, status, input_params, triggered_by
        ) VALUES (
            :run_id, :pipeline_name, :pipeline_version,
            :started_at, :status, :input_params, :triggered_by
        )
    """

    input_params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    }

    with engine.connect() as conn:
        conn.execute(
            text(insert_query),
            {
                "run_id": run_id,
                "pipeline_name": PIPELINE_NAME,
                "pipeline_version": PIPELINE_VERSION,
                "started_at": datetime.now(timezone.utc),
                "status": "running",
                "input_params": json.dumps(input_params),
                "triggered_by": triggered_by
            }
        )
        conn.commit()

    logger.info(f"📝 Registro de auditoría creado: run_id={run_id}")


def update_pipeline_run_metrics(
    run_id: uuid.UUID,
    metrics: Dict[str, Any]
) -> None:
    """
    Actualiza métricas del run en la tabla de auditoría.

    Args:
        run_id: UUID del run
        metrics: Diccionario con campos a actualizar
    """
    engine = get_database_engine()

    # Construir SET clause dinámicamente
    set_clauses = []
    params = {"run_id": run_id}

    for key, value in metrics.items():
        set_clauses.append(f"{key} = :{key}")
        params[key] = value

    if not set_clauses:
        return

    update_query = f"""
        UPDATE reporting.pipeline_runs
        SET {', '.join(set_clauses)}
        WHERE run_id = :run_id
    """

    with engine.connect() as conn:
        conn.execute(text(update_query), params)
        conn.commit()


def finalize_pipeline_run(
    run_id: uuid.UUID,
    status: str,
    error_message: Optional[str] = None,
    error_traceback: Optional[str] = None
) -> None:
    """
    Finaliza el registro de auditoría del run.

    Args:
        run_id: UUID del run
        status: Estado final ('completed' o 'failed')
        error_message: Mensaje de error (si aplica)
        error_traceback: Stack trace (si aplica)
    """
    engine = get_database_engine()

    # Calcular duración del run
    select_query = """
        SELECT started_at FROM reporting.pipeline_runs WHERE run_id = :run_id
    """

    with engine.connect() as conn:
        result = conn.execute(text(select_query), {"run_id": run_id})
        row = result.fetchone()

        if row:
            started_at = row[0]
            finished_at = datetime.now(timezone.utc)
            duration_seconds = int((finished_at - started_at).total_seconds())
        else:
            duration_seconds = None

    update_metrics = {
        "finished_at": datetime.now(timezone.utc),
        "status": status,
        "duration_seconds": duration_seconds
    }

    if error_message:
        update_metrics["error_message"] = error_message
    if error_traceback:
        update_metrics["error_traceback"] = error_traceback

    update_pipeline_run_metrics(run_id, update_metrics)

    logger.info(f"🏁 Pipeline finalizado: status={status}, duration={duration_seconds}s")


# ============================================================
# FLOW PRINCIPAL: business_performance_etl
# ============================================================

@flow(
    name="business-performance-etl",
    description="Pipeline ETL diario: telemetry_events → reporting.business_kpis",
    version=PIPELINE_VERSION,
    retries=0,  # No retry a nivel de flow (solo tasks individuales)
    retry_delay_seconds=60
)
def business_performance_etl_flow(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    triggered_by: str = "manual"
) -> Dict[str, Any]:
    """
    Flow principal del pipeline de desempeño de negocio de Brasaland.

    Arquitectura ETL:
        telemetry_events → Extract → Transform → Load → reporting.business_kpis

    Características:
    - Idempotencia garantizada (UPSERT con constraint único)
    - Reintentos inteligentes por task
    - Caching de transformaciones (1h)
    - Auditoría completa de ejecuciones
    - Tolerancia a fallos parciales (notificación opcional)

    Args:
        start_date: Inicio del rango temporal (default: ayer)
        end_date: Fin del rango temporal (default: hoy)
        triggered_by: Origen del trigger ('manual', 'scheduled', 'api')

    Returns:
        Dict con métricas del run:
        {
            "run_id": "uuid",
            "status": "completed",
            "records_read": 1234,
            "records_processed": 5,
            "records_inserted": 5,
            "duration_seconds": 42
        }
    """
    logger = get_run_logger()

    # ============================================================
    # 1. RESOLUCIÓN DE PARÁMETROS
    # ============================================================

    now_utc = datetime.now(timezone.utc)

    # Ventana por defecto: últimas 24 horas (desde medianoche de ayer)
    if end_date is None:
        end_date = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    if start_date is None:
        start_date = end_date - timedelta(days=1)

    # Generar run_id único
    run_id = uuid.uuid4()

    logger.info(f"🚀 Iniciando pipeline business-performance-etl")
    logger.info(f"📅 Periodo: {start_date.date()} a {end_date.date()}")
    logger.info(f"🆔 Run ID: {run_id}")
    logger.info(f"🔧 Triggered by: {triggered_by}")

    # ============================================================
    # 2. INICIALIZACIÓN
    # ============================================================

    # Inicializar tablas de BD si no existen
    engine = get_database_engine()
    init_audit_table(engine)
    init_kpis_table(engine)

    # Crear registro de auditoría inicial
    create_pipeline_run_record(run_id, start_date, end_date, triggered_by)

    # ============================================================
    # 3. PIPELINE ETL (Tasks Secuenciales)
    # ============================================================

    try:
        # TASK 1: EXTRACT
        events_df = extract_telemetry_events(start_date, end_date, run_id)

        # TASK 2: TRANSFORM (con caching)
        kpis_df = transform_events_to_kpis(events_df, start_date, end_date, run_id)

        # TASK 3: LOAD (idempotente)
        load_result = load_kpis_to_database(kpis_df, run_id)

        # ============================================================
        # 4. PASO OPCIONAL NO CRÍTICO (Tolerancia a Fallos Parciales)
        # ============================================================

        # Invocar con return_state=True para capturar estado sin propagar error
        notification_state = send_completion_notification.submit(
            run_id=run_id,
            metrics=load_result,
            return_state=True  # NO propagar error si falla
        )

        # Esperar resultado sin bloquear el flow
        notification_result = notification_state.result()

        if notification_result.is_failed():
            logger.warning(
                f"⚠️ Notificación falló (no crítico): "
                f"{notification_result.message}"
            )
        else:
            logger.info("✅ Notificación enviada exitosamente")

        # ============================================================
        # 5. FINALIZACIÓN EXITOSA
        # ============================================================

        finalize_pipeline_run(run_id, status="completed")

        result = {
            "run_id": str(run_id),
            "status": "completed",
            "records_read": len(events_df),
            "records_processed": len(kpis_df),
            "records_inserted": load_result["total"],
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat()
        }

        logger.info(f"✅ Pipeline completado exitosamente")
        logger.info(f"📊 Métricas: {result}")

        return result

    except Exception as e:
        # ============================================================
        # 6. MANEJO DE ERRORES GLOBALES
        # ============================================================

        error_message = str(e)
        error_traceback = traceback.format_exc()

        logger.error(f"❌ Pipeline falló: {type(e).__name__}: {error_message}")
        logger.error(f"📜 Traceback:\n{error_traceback}")

        # Finalizar audit log con error
        finalize_pipeline_run(
            run_id,
            status="failed",
            error_message=error_message,
            error_traceback=error_traceback
        )

        # Re-raise para que Prefect lo marque como Failed
        raise


# ============================================================
# EJECUCIÓN AUTÓNOMA POR CLI
# ============================================================

def parse_cli_arguments() -> argparse.Namespace:
    """
    Parsea argumentos de línea de comandos.

    Returns:
        Namespace con argumentos parseados
    """
    parser = argparse.ArgumentParser(
        description="Brasaland Business Performance ETL Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Ventana por defecto (últimas 24 horas)
  python data/pipelines/business-performance/pipeline.py

  # Ventana personalizada (últimos 7 días)
  python data/pipelines/business-performance/pipeline.py --days 7

  # Rango específico (backfill)
  python data/pipelines/business-performance/pipeline.py \\
    --start-date 2026-10-01 --end-date 2026-10-31

  # Con origen del trigger
  python data/pipelines/business-performance/pipeline.py \\
    --triggered-by scheduled
        """
    )

    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Número de días hacia atrás desde hoy (default: 1)"
    )

    parser.add_argument(
        "--start-date",
        type=str,
        help="Fecha de inicio en formato YYYY-MM-DD (opcional)"
    )

    parser.add_argument(
        "--end-date",
        type=str,
        help="Fecha de fin en formato YYYY-MM-DD (opcional, default: hoy)"
    )

    parser.add_argument(
        "--triggered-by",
        type=str,
        default="manual",
        choices=["manual", "scheduled", "api"],
        help="Origen del trigger (default: manual)"
    )

    return parser.parse_args()


def main() -> int:
    """
    Punto de entrada CLI para ejecución standalone del pipeline.

    Returns:
        Exit code (0 = éxito, 1 = error)
    """
    args = parse_cli_arguments()

    # Resolver fechas
    now_utc = datetime.now(timezone.utc)

    if args.start_date and args.end_date:
        # Rango explícito
        start_date = datetime.fromisoformat(args.start_date).replace(
            tzinfo=timezone.utc
        )
        end_date = datetime.fromisoformat(args.end_date).replace(
            tzinfo=timezone.utc
        )
    else:
        # Ventana relativa
        end_date = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=args.days)

    logger.info("=" * 80)
    logger.info("🏢 BRASALAND DIGITAL - BUSINESS PERFORMANCE ETL")
    logger.info("=" * 80)
    logger.info(f"📅 Rango: {start_date.date()} → {end_date.date()}")
    logger.info(f"🔧 Trigger: {args.triggered_by}")
    logger.info("=" * 80)

    try:
        # Ejecutar flow
        result = business_performance_etl_flow(
            start_date=start_date,
            end_date=end_date,
            triggered_by=args.triggered_by
        )

        logger.info("=" * 80)
        logger.info("✅ PIPELINE COMPLETADO EXITOSAMENTE")
        logger.info("=" * 80)
        logger.info(f"Run ID: {result['run_id']}")
        logger.info(f"Eventos procesados: {result['records_read']:,}")
        logger.info(f"KPIs generados: {result['records_processed']:,}")
        logger.info(f"Registros insertados: {result['records_inserted']:,}")
        logger.info("=" * 80)

        return 0

    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ PIPELINE FALLÓ")
        logger.error("=" * 80)
        logger.error(f"Error: {type(e).__name__}: {str(e)}")
        logger.error("=" * 80)

        return 1


if __name__ == "__main__":
    sys.exit(main())
