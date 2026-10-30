"""
Telemetry Analysis Pipeline - Pure Pandas Analytics

Pipeline analítico modular para transformar datos crudos de telemetría
en métricas operativas y técnicas para el equipo de ingeniería.

Principios de diseño:
- Separación SQL/Pandas: SQL filtra temporal y event_type, Pandas agrega
- Funciones puras y deterministas (mismo input → mismo output)
- Cero bucles manuales, solo vectorización con Pandas
- Conversión obligatoria pd.to_datetime() antes de groupby
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlmodel import Session, text
import pandas as pd
import logging

logger = logging.getLogger(__name__)


# ============================================================
# 1. VOLUMEN TEMPORAL DE EVENTOS
# ============================================================

def get_events_per_day(
    start_date: datetime,
    end_date: datetime,
    db: Session
) -> List[Dict[str, Any]]:
    """
    Calcula el volumen total de eventos por día (agregación temporal).

    Reglas de implementación:
    - SQL filtra rango temporal: timestamp >= start_date AND timestamp < end_date
    - Pandas convierte timestamp a datetime UTC con pd.to_datetime()
    - Agrupa por día usando .dt.date (sin bucles manuales)
    - Serializa a lista de dicts con .to_dict(orient='records')

    Args:
        start_date: Inicio del rango (inclusive)
        end_date: Fin del rango (exclusivo)
        db: Sesión de Supabase

    Returns:
        Lista de dicts: [{"date": "2026-10-23", "event_count": 150}, ...]

    Example:
        >>> events = get_events_per_day(
        ...     start_date=datetime(2026, 10, 23),
        ...     end_date=datetime(2026, 10, 30),
        ...     db=db_session
        ... )
        >>> events[0]
        {"date": "2026-10-23", "event_count": 150}
    """
    try:
        # ============================================================
        # SQL: Filtrar rango temporal (NUNCA cargar toda la tabla)
        # ============================================================

        query = text("""
            SELECT timestamp
            FROM telemetry_events
            WHERE timestamp >= :start_date
              AND timestamp < :end_date
            ORDER BY timestamp ASC
        """)

        result = db.execute(query, {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        })

        rows = result.fetchall()

        if not rows:
            logger.info(f"📭 Sin eventos en rango {start_date.date()} a {end_date.date()}")
            return []

        # ============================================================
        # Pandas: Conversión obligatoria a datetime UTC
        # ============================================================

        df = pd.DataFrame(rows, columns=["timestamp"])

        # CRÍTICO: Convertir a datetime UTC ANTES de groupby
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

        # ============================================================
        # Pandas: Agregación vectorizada por día (sin bucles)
        # ============================================================

        # Extraer fecha del timestamp (sin hora)
        df["date"] = df["timestamp"].dt.date

        # Agrupar y contar eventos por día
        events_per_day = df.groupby("date").size().reset_index(name="event_count")

        # Convertir fecha a string ISO 8601 (YYYY-MM-DD)
        events_per_day["date"] = events_per_day["date"].astype(str)

        # ============================================================
        # Serialización: DataFrame → List[Dict]
        # ============================================================

        result_list = events_per_day.to_dict(orient="records")

        logger.info(f"📊 Volumen temporal: {len(result_list)} días con datos")

        return result_list

    except Exception as e:
        logger.error(f"❌ Error en get_events_per_day: {type(e).__name__}: {str(e)}")
        return []


# ============================================================
# 2. TASA DE ERRORES POR TIPO
# ============================================================

def get_error_rate_by_type(
    start_date: datetime,
    end_date: datetime,
    db: Session
) -> List[Dict[str, Any]]:
    """
    Calcula la tasa de errores por tipo de evento.

    Lógica de detección de errores:
    - event_type contiene 'error', 'failed', 'rejected' → es error
    - event_type contiene 'success', 'created', 'updated' → NO es error

    Métrica: error_rate = errores / total por cada event_type

    Reglas de implementación:
    - SQL filtra rango temporal
    - Pandas crea flag is_error con vectorización (.str.contains())
    - Agrupa por event_type calculando sum(is_error) / count()
    - Sin bucles manuales

    Args:
        start_date: Inicio del rango (inclusive)
        end_date: Fin del rango (exclusivo)
        db: Sesión de Supabase

    Returns:
        Lista de dicts: [
            {
                "event_type": "login_attempt_failed",
                "total_events": 50,
                "error_events": 50,
                "error_rate": 1.0
            },
            ...
        ]

    Example:
        >>> errors = get_error_rate_by_type(
        ...     start_date=datetime(2026, 10, 23),
        ...     end_date=datetime(2026, 10, 30),
        ...     db=db_session
        ... )
        >>> errors[0]
        {
            "event_type": "frontend_error_uncaught",
            "total_events": 25,
            "error_events": 25,
            "error_rate": 1.0
        }
    """
    try:
        # ============================================================
        # SQL: Filtrar rango temporal
        # ============================================================

        query = text("""
            SELECT event_type
            FROM telemetry_events
            WHERE timestamp >= :start_date
              AND timestamp < :end_date
        """)

        result = db.execute(query, {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        })

        rows = result.fetchall()

        if not rows:
            logger.info(f"📭 Sin eventos para calcular error rate")
            return []

        # ============================================================
        # Pandas: Crear flag is_error con vectorización
        # ============================================================

        df = pd.DataFrame(rows, columns=["event_type"])

        # Flag is_error usando .str.contains() (vectorizado, sin bucles)
        error_keywords = ["error", "failed", "rejected"]
        df["is_error"] = df["event_type"].str.contains(
            "|".join(error_keywords),
            case=False,
            na=False
        )

        # ============================================================
        # Pandas: Agregación vectorizada por event_type
        # ============================================================

        error_stats = df.groupby("event_type").agg(
            total_events=("event_type", "size"),
            error_events=("is_error", "sum")
        ).reset_index()

        # Calcular tasa de error (vectorizado)
        error_stats["error_rate"] = (
            error_stats["error_events"] / error_stats["total_events"]
        ).round(4)

        # Convertir int64 a int nativo de Python (para JSON serialization)
        error_stats["total_events"] = error_stats["total_events"].astype(int)
        error_stats["error_events"] = error_stats["error_events"].astype(int)

        # Ordenar por tasa de error descendente
        error_stats = error_stats.sort_values("error_rate", ascending=False)

        # ============================================================
        # Serialización: DataFrame → List[Dict]
        # ============================================================

        result_list = error_stats.to_dict(orient="records")

        logger.info(f"📊 Error rate: {len(result_list)} tipos de evento analizados")

        return result_list

    except Exception as e:
        logger.error(f"❌ Error en get_error_rate_by_type: {type(e).__name__}: {str(e)}")
        return []


# ============================================================
# 3. TASA DE FALLOS DE AUTENTICACIÓN
# ============================================================

def get_auth_failure_rate(
    start_date: datetime,
    end_date: datetime,
    db: Session
) -> List[Dict[str, Any]]:
    """
    Calcula la tasa de fallos de autenticación por día.

    Métrica: auth_failure_rate = login_attempt_failed / (login_attempt_failed + login_attempt_success)

    Reglas de implementación:
    - SQL filtra rango temporal Y event_type IN ('login_attempt_success', 'login_attempt_failed')
    - Pandas convierte timestamp a datetime UTC
    - Agrupa por día y event_type
    - Pivotea para tener columnas success/failed
    - Calcula ratio vectorizado

    Args:
        start_date: Inicio del rango (inclusive)
        end_date: Fin del rango (exclusivo)
        db: Sesión de Supabase

    Returns:
        Lista de dicts: [
            {
                "date": "2026-10-23",
                "total_attempts": 100,
                "failed_attempts": 15,
                "success_attempts": 85,
                "failure_rate": 0.15
            },
            ...
        ]

    Example:
        >>> auth = get_auth_failure_rate(
        ...     start_date=datetime(2026, 10, 23),
        ...     end_date=datetime(2026, 10, 30),
        ...     db=db_session
        ... )
        >>> auth[0]
        {
            "date": "2026-10-23",
            "total_attempts": 100,
            "failed_attempts": 15,
            "success_attempts": 85,
            "failure_rate": 0.15
        }
    """
    try:
        # ============================================================
        # SQL: Filtrar rango temporal Y tipos de evento de auth
        # ============================================================

        query = text("""
            SELECT timestamp, event_type
            FROM telemetry_events
            WHERE timestamp >= :start_date
              AND timestamp < :end_date
              AND event_type IN ('login_attempt_success', 'login_attempt_failed')
            ORDER BY timestamp ASC
        """)

        result = db.execute(query, {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        })

        rows = result.fetchall()

        if not rows:
            logger.info(f"📭 Sin eventos de autenticación en rango")
            return []

        # ============================================================
        # Pandas: Conversión obligatoria a datetime UTC
        # ============================================================

        df = pd.DataFrame(rows, columns=["timestamp", "event_type"])

        # CRÍTICO: Convertir a datetime UTC ANTES de groupby
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df["date"] = df["timestamp"].dt.date

        # ============================================================
        # Pandas: Agregación vectorizada por día y tipo
        # ============================================================

        # Contar eventos por día y tipo
        auth_counts = df.groupby(["date", "event_type"]).size().reset_index(name="count")

        # Pivotar para tener columnas success/failed
        auth_pivot = auth_counts.pivot(
            index="date",
            columns="event_type",
            values="count"
        ).fillna(0).reset_index()

        # Renombrar columnas si existen
        auth_pivot.columns.name = None  # Eliminar nombre de índice de columnas

        # Asegurar que ambas columnas existen (pueden no existir si solo hay uno de los tipos)
        if "login_attempt_success" not in auth_pivot.columns:
            auth_pivot["login_attempt_success"] = 0
        if "login_attempt_failed" not in auth_pivot.columns:
            auth_pivot["login_attempt_failed"] = 0

        # Renombrar columnas a nombres más claros
        auth_pivot = auth_pivot.rename(columns={
            "login_attempt_success": "success_attempts",
            "login_attempt_failed": "failed_attempts"
        })

        # ============================================================
        # Pandas: Calcular métricas derivadas (vectorizado)
        # ============================================================

        auth_pivot["total_attempts"] = (
            auth_pivot["success_attempts"] + auth_pivot["failed_attempts"]
        )

        # Calcular failure_rate (evitar división por cero)
        auth_pivot["failure_rate"] = (
            auth_pivot["failed_attempts"] / auth_pivot["total_attempts"]
        ).fillna(0).round(4)

        # Convertir tipos a int nativo (para JSON serialization)
        auth_pivot["success_attempts"] = auth_pivot["success_attempts"].astype(int)
        auth_pivot["failed_attempts"] = auth_pivot["failed_attempts"].astype(int)
        auth_pivot["total_attempts"] = auth_pivot["total_attempts"].astype(int)

        # Convertir fecha a string ISO 8601
        auth_pivot["date"] = auth_pivot["date"].astype(str)

        # Ordenar por fecha ascendente
        auth_pivot = auth_pivot.sort_values("date")

        # ============================================================
        # Serialización: DataFrame → List[Dict]
        # ============================================================

        result_list = auth_pivot.to_dict(orient="records")

        logger.info(f"📊 Auth failure rate: {len(result_list)} días con intentos de login")

        return result_list

    except Exception as e:
        logger.error(f"❌ Error en get_auth_failure_rate: {type(e).__name__}: {str(e)}")
        return []


# ============================================================
# 4. FUNCIÓN DE CONVENIENCIA: Generar Reporte Completo
# ============================================================

def generate_telemetry_report(
    start_date: datetime,
    end_date: datetime,
    db: Session
) -> Dict[str, Any]:
    """
    Genera reporte completo ejecutando todas las funciones analíticas.

    Esta función orquesta el pipeline completo y retorna un diccionario
    con el periodo analizado y todas las métricas calculadas.

    Args:
        start_date: Inicio del rango (inclusive)
        end_date: Fin del rango (exclusivo)
        db: Sesión de Supabase

    Returns:
        Dict con estructura:
        {
            "period": {
                "from": "2026-10-23T00:00:00Z",
                "to": "2026-10-30T00:00:00Z"
            },
            "metrics": {
                "events_per_day": [...],
                "error_rate_by_type": [...],
                "auth_failure_rate": [...]
            }
        }
    """
    logger.info(
        f"🔄 Generando reporte de telemetría: {start_date.date()} a {end_date.date()}"
    )

    # Ejecutar pipeline analítico completo
    events_per_day = get_events_per_day(start_date, end_date, db)
    error_rate_by_type = get_error_rate_by_type(start_date, end_date, db)
    auth_failure_rate = get_auth_failure_rate(start_date, end_date, db)

    report = {
        "period": {
            "from": start_date.isoformat(),
            "to": end_date.isoformat()
        },
        "metrics": {
            "events_per_day": events_per_day,
            "error_rate_by_type": error_rate_by_type,
            "auth_failure_rate": auth_failure_rate
        }
    }

    logger.info(
        f"✅ Reporte generado: "
        f"{len(events_per_day)} días, "
        f"{len(error_rate_by_type)} tipos de evento, "
        f"{len(auth_failure_rate)} días con auth"
    )

    return report
