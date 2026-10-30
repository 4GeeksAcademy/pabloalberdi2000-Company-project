"""
Business Performance ETL Pipeline - Brasaland Digital (Production v2.0)

Pipeline refactorizado con subflows modulares para producción.

Arquitectura de Subflows:
    1. brasaland_telemetry_extraction_subflow → DataFrame de eventos
    2. brasaland_business_kpis_transformation_subflow → DataFrame de KPIs
    3. brasaland_kpis_persistence_subflow → Carga idempotente
    4. brasaland_notification_subflow (opcional) → Alertas

Mejoras v2.0:
- Topología modular con 4 subflows independientes
- Contratos explícitos (inputs/outputs tipados)
- Zero variables globales (estado inmutable)
- Manejo de fallos parciales (notification no bloqueante)
- Testing unitario completo (tests/pipelines/test_pipeline.py)

Ejecución:
    python data/pipelines/business-performance/pipeline_v2.py
    python data/pipelines/business-performance/pipeline_v2.py --days 7
"""

import argparse
import json
import logging
import os
import sys
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List

import pandas as pd
from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ============================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================

PIPELINE_NAME = "business-performance-etl"
PIPELINE_VERSION = "2.0.0"  # Production-ready with subflows

DATABASE_URL = os.getenv(
    "SUPABASE_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================
# UTILIDADES DE BASE DE DATOS (Reutilizables)
# ============================================================

def get_database_engine() -> Engine:
    """Crea engine de SQLAlchemy para PostgreSQL/Supabase."""
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10
    )


def init_reporting_schema(engine: Engine) -> None:
    """
    Inicializa schema 'reporting' y tablas necesarias.

    Tablas creadas:
    - reporting.pipeline_runs (auditoría)
    - reporting.business_kpis (KPIs de negocio)
    """
    create_schema = "CREATE SCHEMA IF NOT EXISTS reporting;"

    create_pipeline_runs = """
    CREATE TABLE IF NOT EXISTS reporting.pipeline_runs (
        run_id UUID PRIMARY KEY,
        pipeline_name VARCHAR(100) NOT NULL,
        pipeline_version VARCHAR(20) NOT NULL,
        started_at TIMESTAMPTZ NOT NULL,
        finished_at TIMESTAMPTZ,
        duration_seconds INTEGER,
        input_params JSONB NOT NULL,
        records_read INTEGER,
        records_processed INTEGER,
        records_inserted INTEGER,
        status VARCHAR(20) NOT NULL,
        error_message TEXT,
        error_traceback TEXT,
        triggered_by VARCHAR(50),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at
    ON reporting.pipeline_runs (started_at DESC);
    """

    create_business_kpis = """
    CREATE TABLE IF NOT EXISTS reporting.business_kpis (
        id BIGSERIAL PRIMARY KEY,
        date DATE NOT NULL,
        country VARCHAR(2),
        service VARCHAR(50),
        warehouse VARCHAR(100),
        period_start TIMESTAMPTZ NOT NULL,
        period_end TIMESTAMPTZ NOT NULL,
        daily_active_users INTEGER NOT NULL DEFAULT 0,
        total_sessions INTEGER NOT NULL DEFAULT 0,
        total_events INTEGER NOT NULL DEFAULT 0,
        avg_events_per_session NUMERIC(10, 2),
        system_availability_pct NUMERIC(5, 2),
        avg_response_time_ms NUMERIC(10, 2),
        error_events INTEGER NOT NULL DEFAULT 0,
        error_rate NUMERIC(5, 4),
        auth_success_rate NUMERIC(5, 2),
        events_with_user_id_pct NUMERIC(5, 2),
        events_with_session_id_pct NUMERIC(5, 2),
        calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        pipeline_run_id UUID NOT NULL,
        pipeline_version VARCHAR(20) NOT NULL DEFAULT '2.0.0',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_business_kpis_natural_key
    ON reporting.business_kpis (
        date,
        COALESCE(country, ''),
        COALESCE(service, ''),
        COALESCE(warehouse, '')
    );
    CREATE INDEX IF NOT EXISTS idx_business_kpis_date
    ON reporting.business_kpis (date DESC);
    """

    with engine.connect() as conn:
        conn.execute(text(create_schema))
        conn.execute(text(create_pipeline_runs))
        conn.execute(text(create_business_kpis))
        conn.commit()

    logger.info("✅ Schema 'reporting' y tablas inicializadas")


def create_audit_record(
    run_id: uuid.UUID,
    start_date: datetime,
    end_date: datetime,
    triggered_by: str
) -> None:
    """Crea registro inicial en pipeline_runs."""
    engine = get_database_engine()

    query = """
        INSERT INTO reporting.pipeline_runs (
            run_id, pipeline_name, pipeline_version,
            started_at, status, input_params, triggered_by
        ) VALUES (
            :run_id, :pipeline_name, :pipeline_version,
            :started_at, :status, :input_params, :triggered_by
        )
    """

    with engine.connect() as conn:
        conn.execute(
            text(query),
            {
                "run_id": run_id,
                "pipeline_name": PIPELINE_NAME,
                "pipeline_version": PIPELINE_VERSION,
                "started_at": datetime.now(timezone.utc),
                "status": "running",
                "input_params": json.dumps({
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }),
                "triggered_by": triggered_by
            }
        )
        conn.commit()


def update_audit_metrics(run_id: uuid.UUID, metrics: Dict[str, Any]) -> None:
    """Actualiza métricas en pipeline_runs."""
    engine = get_database_engine()

    set_clauses = [f"{k} = :{k}" for k in metrics.keys()]
    query = f"""
        UPDATE reporting.pipeline_runs
        SET {', '.join(set_clauses)}
        WHERE run_id = :run_id
    """

    params = {"run_id": run_id, **metrics}

    with engine.connect() as conn:
        conn.execute(text(query), params)
        conn.commit()


def finalize_audit_record(
    run_id: uuid.UUID,
    status: str,
    error_message: Optional[str] = None
) -> None:
    """Finaliza registro de auditoría."""
    engine = get_database_engine()

    select_query = """
        SELECT started_at FROM reporting.pipeline_runs WHERE run_id = :run_id
    """

    with engine.connect() as conn:
        result = conn.execute(text(select_query), {"run_id": run_id})
        row = result.fetchone()

        if row:
            started_at = row[0]
            finished_at = datetime.now(timezone.utc)
            duration = int((finished_at - started_at).total_seconds())
        else:
            duration = None

    metrics = {
        "finished_at": datetime.now(timezone.utc),
        "status": status,
        "duration_seconds": duration
    }

    if error_message:
        metrics["error_message"] = error_message

    update_audit_metrics(run_id, metrics)


# ============================================================
# FUNCIONES DE TRANSFORMACIÓN (Puras, para testing unitario)
# ============================================================

def calculate_daily_active_users(events_df: pd.DataFrame) -> pd.Series:
    """
    Calcula Daily Active Users (DAU) por fecha.

    Función PURA para testing unitario.

    Args:
        events_df: DataFrame con columnas ['date', 'user_id']

    Returns:
        Series con índice=date, values=daily_active_users
    """
    if events_df.empty or 'user_id' not in events_df.columns:
        return pd.Series(dtype=int)

    return events_df.groupby("date")["user_id"].nunique()


def calculate_system_availability(events_df: pd.DataFrame) -> pd.Series:
    """
    Calcula disponibilidad del sistema (%) por fecha.

    Fórmula: (1 - error_events / total_events) * 100

    Función PURA para testing unitario.

    Args:
        events_df: DataFrame con columnas ['date', 'is_error']

    Returns:
        Series con índice=date, values=availability_pct
    """
    if events_df.empty or 'is_error' not in events_df.columns:
        return pd.Series(dtype=float)

    grouped = events_df.groupby("date")
    total = grouped.size()
    errors = grouped["is_error"].sum()

    availability = (1 - errors / total) * 100
    return availability.round(2)


def calculate_auth_success_rate(events_df: pd.DataFrame) -> pd.Series:
    """
    Calcula tasa de éxito de autenticación (%) por fecha.

    Fórmula: (login_success / (login_success + login_failed)) * 100

    Función PURA para testing unitario.

    Args:
        events_df: DataFrame con columnas ['date', 'is_auth_success', 'is_auth_failed']

    Returns:
        Series con índice=date, values=auth_success_rate_pct
    """
    if events_df.empty:
        return pd.Series(dtype=float)

    if 'is_auth_success' not in events_df.columns:
        return pd.Series(dtype=float)

    grouped = events_df.groupby("date")
    success = grouped["is_auth_success"].sum()
    failed = grouped["is_auth_failed"].sum()

    total_attempts = success + failed
    rate = (success / total_attempts).fillna(0) * 100

    return rate.round(2)


# ============================================================
# SUBFLOW 1: EXTRACCIÓN DE EVENTOS DE TELEMETRÍA
# ============================================================

@flow(
    name="brasaland-telemetry-extraction",
    description="Extrae eventos de telemetría de Brasaland desde telemetry_events",
    retries=2,
    retry_delay_seconds=30
)
def brasaland_telemetry_extraction_subflow(
    start_date: datetime,
    end_date: datetime,
    run_id: uuid.UUID
) -> pd.DataFrame:
    """
    Subflow de extracción de eventos de telemetría.

    Responsabilidad única: Cargar eventos desde telemetry_events
    en el rango temporal especificado.

    Args:
        start_date: Inicio del rango (inclusive)
        end_date: Fin del rango (exclusivo)
        run_id: UUID del run actual

    Returns:
        DataFrame con eventos crudos de telemetry_events
    """
    logger = get_run_logger()
    logger.info(
        f"📥 [EXTRACTION] Rango: {start_date.date()} → {end_date.date()}"
    )

    engine = get_database_engine()

    query = """
        SELECT
            id, event_id, event_type, timestamp,
            session_id, user_id, service, tags
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
            logger.warning("📭 Sin eventos en el rango especificado")
            return pd.DataFrame(columns=columns)

        df = pd.DataFrame(rows, columns=columns)

        logger.info(f"✅ Extraídos {len(df):,} eventos")

        # Actualizar audit
        update_audit_metrics(run_id, {"records_read": len(df)})

        return df

    except Exception as e:
        logger.error(f"❌ Error en extracción: {e}")
        update_audit_metrics(
            run_id,
            {"status": "failed", "error_message": str(e)}
        )
        raise


# ============================================================
# SUBFLOW 2: TRANSFORMACIÓN A KPIs DE NEGOCIO
# ============================================================

@flow(
    name="brasaland-business-kpis-transformation",
    description="Transforma eventos de telemetría en KPIs de negocio de Brasaland",
    retries=1,
    retry_delay_seconds=20
)
def brasaland_business_kpis_transformation_subflow(
    events_df: pd.DataFrame,
    start_date: datetime,
    end_date: datetime,
    run_id: uuid.UUID
) -> pd.DataFrame:
    """
    Subflow de transformación de eventos → KPIs de negocio.

    Responsabilidad única: Calcular KPIs agregados por fecha
    usando funciones puras y deterministas.

    Args:
        events_df: DataFrame con eventos crudos
        start_date: Inicio del periodo (metadata)
        end_date: Fin del periodo (metadata)
        run_id: UUID del run actual

    Returns:
        DataFrame con KPIs agregados (columnas de business_kpis)
    """
    logger = get_run_logger()
    logger.info(f"🔄 [TRANSFORMATION] Procesando {len(events_df):,} eventos")

    if events_df.empty:
        logger.warning("⚠️ DataFrame vacío, retornando KPIs vacíos")
        return pd.DataFrame()

    # ============================================================
    # 1. PREPARACIÓN DE DATOS
    # ============================================================

    df = events_df.copy()

    # Conversión de tipos
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["timestamp"].dt.date

    # Extracción de dimensiones desde JSONB tags
    if "tags" in df.columns:
        df["country"] = df["tags"].apply(
            lambda x: x.get("country") if isinstance(x, dict) else None
        )
        df["warehouse"] = df["tags"].apply(
            lambda x: x.get("warehouse") if isinstance(x, dict) else None
        )
        df["duration_ms"] = df["tags"].apply(
            lambda x: x.get("duration_ms") if isinstance(x, dict) else None
        )

    # Flags de clasificación
    error_keywords = ["error", "failed", "rejected"]
    df["is_error"] = df["event_type"].str.contains(
        "|".join(error_keywords), case=False, na=False
    )

    df["is_auth_success"] = (df["event_type"] == "login_attempt_success")
    df["is_auth_failed"] = (df["event_type"] == "login_attempt_failed")

    # ============================================================
    # 2. AGREGACIONES VECTORIZADAS
    # ============================================================

    kpis = df.groupby("date").agg(
        total_events=("event_id", "size"),
        total_sessions=("session_id", "nunique"),
        daily_active_users=("user_id", "nunique"),
        avg_response_time_ms=("duration_ms", "mean"),
        error_events=("is_error", "sum"),
        auth_success_events=("is_auth_success", "sum"),
        auth_failed_events=("is_auth_failed", "sum"),
        events_with_user_id=("user_id", lambda x: x.notna().sum()),
        events_with_session_id=("session_id", lambda x: x.notna().sum())
    ).reset_index()

    # ============================================================
    # 3. MÉTRICAS DERIVADAS (usando funciones puras)
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

    # Calidad de datos
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
    # 4. METADATA
    # ============================================================

    kpis["period_start"] = start_date
    kpis["period_end"] = end_date
    kpis["calculated_at"] = datetime.now(timezone.utc)
    kpis["pipeline_run_id"] = run_id
    kpis["pipeline_version"] = PIPELINE_VERSION

    # Dimensiones (globales en Fase 1)
    kpis["country"] = None
    kpis["service"] = None
    kpis["warehouse"] = None

    # Convertir date a string
    kpis["date"] = kpis["date"].astype(str)

    # Convertir tipos numéricos a int nativo
    int_cols = [
        "total_events", "total_sessions", "daily_active_users",
        "error_events", "auth_success_events", "auth_failed_events",
        "events_with_user_id", "events_with_session_id"
    ]
    for col in int_cols:
        if col in kpis.columns:
            kpis[col] = kpis[col].astype(int)

    logger.info(f"✅ Generados {len(kpis):,} registros de KPIs")

    # Actualizar audit
    update_audit_metrics(run_id, {"records_processed": len(kpis)})

    return kpis


# ============================================================
# SUBFLOW 3: PERSISTENCIA IDEMPOTENTE EN BD
# ============================================================

@flow(
    name="brasaland-kpis-persistence",
    description="Persiste KPIs de Brasaland en reporting.business_kpis con UPSERT",
    retries=2,
    retry_delay_seconds=30
)
def brasaland_kpis_persistence_subflow(
    kpis_df: pd.DataFrame,
    run_id: uuid.UUID
) -> Dict[str, int]:
    """
    Subflow de persistencia de KPIs con UPSERT idempotente.

    Responsabilidad única: Cargar KPIs en business_kpis
    garantizando idempotencia.

    Args:
        kpis_df: DataFrame con KPIs agregados
        run_id: UUID del run actual

    Returns:
        Dict con métricas: {"total": N}
    """
    logger = get_run_logger()
    logger.info(f"💾 [PERSISTENCE] Cargando {len(kpis_df):,} registros")

    if kpis_df.empty:
        logger.warning("⚠️ DataFrame vacío, nada que cargar")
        return {"total": 0}

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
        with engine.begin() as conn:
            for row in kpis_df.to_dict(orient="records"):
                conn.execute(text(upsert_query), row)
                total_processed += 1

        logger.info(f"✅ Cargados {total_processed:,} registros (UPSERT exitoso)")

        result = {"total": total_processed}

        # Actualizar audit
        update_audit_metrics(run_id, {"records_inserted": total_processed})

        return result

    except Exception as e:
        logger.error(f"❌ Error en persistencia: {e}")
        update_audit_metrics(
            run_id,
            {"status": "failed", "error_message": str(e)}
        )
        raise


# ============================================================
# SUBFLOW 4: NOTIFICACIÓN (OPCIONAL, NO BLOQUEANTE)
# ============================================================

@flow(
    name="brasaland-notification",
    description="Envía notificación de completado (paso opcional)",
    retries=0  # Sin reintentos (paso no crítico)
)
def brasaland_notification_subflow(
    run_id: uuid.UUID,
    metrics: Dict[str, int]
) -> Dict[str, str]:
    """
    Subflow de notificación (opcional, no bloqueante).

    Este subflow es NO CRÍTICO:
    - Si falla, el pipeline continúa normalmente
    - Se invoca con return_state=True para capturar error sin propagar

    Args:
        run_id: UUID del run
        metrics: Métricas del run

    Returns:
        Dict con resultado de notificación
    """
    logger = get_run_logger()
    logger.info(f"📧 [NOTIFICATION] Run ID: {run_id}")

    message = (
        f"✅ Pipeline Brasaland Business Performance completado\n"
        f"Run ID: {run_id}\n"
        f"Registros procesados: {metrics.get('total', 0):,}\n"
        f"Timestamp: {datetime.now(timezone.utc).isoformat()}"
    )

    logger.info(message)

    return {
        "status": "sent",
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================================
# FLOW PRINCIPAL COORDINADOR
# ============================================================

@flow(
    name="brasaland-business-performance-etl",
    description="Flow coordinador del pipeline ETL de Brasaland (Production v2.0)",
    version=PIPELINE_VERSION,
    retries=0
)
def brasaland_business_performance_etl_flow(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    triggered_by: str = "manual"
) -> Dict[str, Any]:
    """
    Flow principal coordinador del pipeline de negocio de Brasaland.

    Coordina 4 subflows independientes:
    1. Extracción de eventos de telemetría
    2. Transformación a KPIs de negocio
    3. Persistencia idempotente en BD
    4. Notificación (opcional, no bloqueante)

    Args:
        start_date: Inicio del rango (default: ayer)
        end_date: Fin del rango (default: hoy)
        triggered_by: Origen del trigger

    Returns:
        Dict con métricas del run
    """
    logger = get_run_logger()

    # ============================================================
    # 1. INICIALIZACIÓN
    # ============================================================

    now_utc = datetime.now(timezone.utc)

    if end_date is None:
        end_date = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    if start_date is None:
        start_date = end_date - timedelta(days=1)

    run_id = uuid.uuid4()

    logger.info("🚀 Iniciando pipeline Brasaland Business Performance v2.0")
    logger.info(f"📅 Periodo: {start_date.date()} → {end_date.date()}")
    logger.info(f"🆔 Run ID: {run_id}")
    logger.info(f"🔧 Triggered by: {triggered_by}")

    # Inicializar schema y tablas
    engine = get_database_engine()
    init_reporting_schema(engine)

    # Crear registro de auditoría
    create_audit_record(run_id, start_date, end_date, triggered_by)

    try:
        # ============================================================
        # 2. SUBFLOW 1: EXTRACCIÓN
        # ============================================================

        events_df = brasaland_telemetry_extraction_subflow(
            start_date=start_date,
            end_date=end_date,
            run_id=run_id
        )

        # ============================================================
        # 3. SUBFLOW 2: TRANSFORMACIÓN
        # ============================================================

        kpis_df = brasaland_business_kpis_transformation_subflow(
            events_df=events_df,
            start_date=start_date,
            end_date=end_date,
            run_id=run_id
        )

        # ============================================================
        # 4. SUBFLOW 3: PERSISTENCIA
        # ============================================================

        load_result = brasaland_kpis_persistence_subflow(
            kpis_df=kpis_df,
            run_id=run_id
        )

        # ============================================================
        # 5. SUBFLOW 4: NOTIFICACIÓN (OPCIONAL, NO BLOQUEANTE)
        # ============================================================

        # Invocar con return_state=True para NO propagar errores
        notification_state = brasaland_notification_subflow.submit(
            run_id=run_id,
            metrics=load_result,
            return_state=True
        )

        # Esperar resultado sin bloquear
        notification_result = notification_state.result()

        if notification_result.is_failed():
            logger.warning(
                f"⚠️ Notificación falló (no crítico): "
                f"{notification_result.message}"
            )
        else:
            logger.info("✅ Notificación enviada exitosamente")

        # ============================================================
        # 6. FINALIZACIÓN EXITOSA
        # ============================================================

        finalize_audit_record(run_id, status="completed")

        result = {
            "run_id": str(run_id),
            "status": "completed",
            "records_read": len(events_df),
            "records_processed": len(kpis_df),
            "records_inserted": load_result["total"],
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat()
        }

        logger.info("✅ Pipeline completado exitosamente")
        logger.info(f"📊 Métricas: {result}")

        return result

    except Exception as e:
        # ============================================================
        # 7. MANEJO DE ERRORES
        # ============================================================

        error_message = str(e)
        error_traceback = traceback.format_exc()

        logger.error(f"❌ Pipeline falló: {type(e).__name__}: {error_message}")
        logger.error(f"📜 Traceback:\n{error_traceback}")

        finalize_audit_record(run_id, status="failed", error_message=error_message)

        raise


# ============================================================
# CLI ENTRYPOINT
# ============================================================

def parse_args() -> argparse.Namespace:
    """Parsea argumentos de CLI."""
    parser = argparse.ArgumentParser(
        description="Brasaland Business Performance ETL Pipeline v2.0 (Production)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Días hacia atrás desde hoy (default: 1)"
    )

    parser.add_argument(
        "--start-date",
        type=str,
        help="Fecha inicio YYYY-MM-DD (opcional)"
    )

    parser.add_argument(
        "--end-date",
        type=str,
        help="Fecha fin YYYY-MM-DD (opcional)"
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
    Punto de entrada CLI para ejecución autónoma.

    Returns:
        Exit code (0 = éxito, 1 = error)
    """
    args = parse_args()

    # Resolver fechas
    now_utc = datetime.now(timezone.utc)

    if args.start_date and args.end_date:
        start_date = datetime.fromisoformat(args.start_date).replace(
            tzinfo=timezone.utc
        )
        end_date = datetime.fromisoformat(args.end_date).replace(
            tzinfo=timezone.utc
        )
    else:
        end_date = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=args.days)

    logger.info("=" * 80)
    logger.info("🏢 BRASALAND DIGITAL - BUSINESS PERFORMANCE ETL v2.0 (PRODUCTION)")
    logger.info("=" * 80)
    logger.info(f"📅 Rango: {start_date.date()} → {end_date.date()}")
    logger.info(f"🔧 Trigger: {args.triggered_by}")
    logger.info("=" * 80)

    try:
        result = brasaland_business_performance_etl_flow(
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
