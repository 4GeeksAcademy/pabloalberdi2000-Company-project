"""
Job Runner Service - Brasaland Digital

Módulo de control de estado para jobs nocturnos de orquestación.

Responsabilidades:
- Lock distribuido (detección de ejecuciones en paralelo)
- Idempotencia (verificación de completitud por fecha)
- Gestión de estados (pending → processing → completed/failed)
- Auditoría de ejecuciones

Arquitectura:
- Capa de orquestación externa (job_runs)
- Separada de pipeline_runs (capa ETL interna)
- Lock distribuido nativo vía estado "processing"

Uso:
    from app.services.job_runner import (
        has_processing_lock,
        has_completed_for_date,
        create_job_run,
        update_job_status
    )

    # Verificar lock
    if has_processing_lock("nightly_export"):
        print("Job ya en ejecución, abortar")
        return

    # Verificar idempotencia
    if has_completed_for_date("nightly_export", target_date):
        print("Job ya completado para esta fecha")
        return

    # Crear run
    job_run = create_job_run("nightly_export", target_date)

    try:
        # ... trabajo ...
        update_job_status(job_run.id, "completed")
    except Exception as e:
        update_job_status(job_run.id, "failed", str(e))
"""

import logging
import traceback
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import os

# ============================================================
# CONFIGURACIÓN
# ============================================================

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "SUPABASE_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres"
)


# ============================================================
# MODELOS DE DATOS (Simple Dataclass)
# ============================================================

class JobRun:
    """
    Modelo simple para representar un job run.

    Atributos:
        id: ID del job run
        job_name: Nombre del job
        target_date: Fecha objetivo
        status: Estado actual
        started_at: Timestamp de inicio
        finished_at: Timestamp de fin (opcional)
        error_message: Mensaje de error (opcional)
    """

    def __init__(
        self,
        id: int,
        job_name: str,
        target_date: date,
        status: str,
        started_at: datetime,
        finished_at: Optional[datetime] = None,
        error_message: Optional[str] = None
    ):
        self.id = id
        self.job_name = job_name
        self.target_date = target_date
        self.status = status
        self.started_at = started_at
        self.finished_at = finished_at
        self.error_message = error_message

    def __repr__(self) -> str:
        return (
            f"JobRun(id={self.id}, job_name='{self.job_name}', "
            f"target_date={self.target_date}, status='{self.status}')"
        )


# ============================================================
# UTILIDADES DE BASE DE DATOS
# ============================================================

def get_database_engine() -> Engine:
    """
    Crea engine de SQLAlchemy para conexión a PostgreSQL/Supabase.

    Returns:
        Engine configurado
    """
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10
    )


# ============================================================
# FUNCIONES DE VALIDACIÓN (Lock e Idempotencia)
# ============================================================

def has_processing_lock(job_name: str) -> bool:
    """
    Comprueba si existe una ejecución activa en estado 'processing'.

    Implementa lock distribuido nativo: si otro proceso está ejecutando
    el mismo job, esta función retorna True para prevenir ejecuciones paralelas.

    Args:
        job_name: Nombre del job (ej: "nightly_export")

    Returns:
        True si existe un job en processing, False en caso contrario

    Example:
        >>> if has_processing_lock("nightly_export"):
        ...     print("Job ya en ejecución, abortar")
        ...     return
    """
    engine = get_database_engine()

    query = """
        SELECT COUNT(*) as count
        FROM job_runs
        WHERE job_name = :job_name
          AND status = 'processing'
    """

    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(query),
                {"job_name": job_name}
            )
            row = result.fetchone()
            count = row[0] if row else 0

        has_lock = count > 0

        if has_lock:
            logger.warning(
                f"🔒 Lock detectado: job '{job_name}' ya está en processing. "
                f"Abortar para prevenir ejecución paralela."
            )

        return has_lock

    except Exception as e:
        logger.error(f"❌ Error verificando lock: {e}")
        # En caso de error de BD, asumir que SÍ hay lock (fail-safe)
        return True


def has_completed_for_date(job_name: str, target_date: date) -> bool:
    """
    Verifica si el job ya fue completado exitosamente para la fecha objetivo.

    Implementa idempotencia: permite ejecutar el script múltiples veces
    sin reprocesar fechas ya completadas.

    Args:
        job_name: Nombre del job
        target_date: Fecha objetivo (DATE)

    Returns:
        True si ya existe un run completado para esta fecha, False en caso contrario

    Example:
        >>> from datetime import date
        >>> if has_completed_for_date("nightly_export", date(2026, 10, 29)):
        ...     print("Ya procesado, omitir")
        ...     return
    """
    engine = get_database_engine()

    query = """
        SELECT COUNT(*) as count
        FROM job_runs
        WHERE job_name = :job_name
          AND target_date = :target_date
          AND status = 'completed'
    """

    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(query),
                {
                    "job_name": job_name,
                    "target_date": target_date.isoformat()
                }
            )
            row = result.fetchone()
            count = row[0] if row else 0

        already_completed = count > 0

        if already_completed:
            logger.info(
                f"✅ Job '{job_name}' ya completado para fecha {target_date}. "
                f"Omitir por idempotencia."
            )

        return already_completed

    except Exception as e:
        logger.error(f"❌ Error verificando completitud: {e}")
        # En caso de error, asumir que NO está completado (permitir reintento)
        return False


# ============================================================
# FUNCIONES DE GESTIÓN DE ESTADO
# ============================================================

def create_job_run(job_name: str, target_date: date) -> JobRun:
    """
    Crea un nuevo registro de job run en estado 'processing'.

    Este registro actúa como lock distribuido: otros procesos verán
    el estado 'processing' y abortarán.

    Args:
        job_name: Nombre del job
        target_date: Fecha objetivo

    Returns:
        JobRun creado con id asignado

    Raises:
        Exception: Si falla la inserción (ej: duplicate key por constraint único)

    Example:
        >>> from datetime import date
        >>> job_run = create_job_run("nightly_export", date(2026, 10, 29))
        >>> print(f"Job run creado: {job_run.id}")
    """
    engine = get_database_engine()

    insert_query = """
        INSERT INTO job_runs (
            job_name,
            target_date,
            status,
            started_at
        ) VALUES (
            :job_name,
            :target_date,
            'processing',
            :started_at
        )
        RETURNING id, job_name, target_date, status, started_at
    """

    started_at = datetime.now(timezone.utc)

    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(insert_query),
                {
                    "job_name": job_name,
                    "target_date": target_date.isoformat(),
                    "started_at": started_at
                }
            )
            conn.commit()

            row = result.fetchone()

        job_run = JobRun(
            id=row[0],
            job_name=row[1],
            target_date=row[2],
            status=row[3],
            started_at=row[4]
        )

        logger.info(
            f"🚀 Job run creado: id={job_run.id}, "
            f"job_name='{job_name}', target_date={target_date}"
        )

        return job_run

    except Exception as e:
        logger.error(f"❌ Error creando job run: {e}")
        raise


def update_job_status(
    run_id: int,
    status: str,
    error_message: Optional[str] = None,
    error_traceback: Optional[str] = None
) -> None:
    """
    Actualiza el estado de un job run.

    Transiciones válidas:
    - processing → completed (éxito)
    - processing → failed (error)

    Al transicionar a 'completed' o 'failed', automáticamente se setea
    finished_at al timestamp actual (via trigger de BD).

    Args:
        run_id: ID del job run
        status: Nuevo estado ('completed' o 'failed')
        error_message: Mensaje de error (opcional, requerido si status='failed')
        error_traceback: Stack trace completo (opcional)

    Example:
        >>> try:
        ...     # ... trabajo ...
        ...     update_job_status(job_run.id, "completed")
        ... except Exception as e:
        ...     update_job_status(
        ...         job_run.id,
        ...         "failed",
        ...         str(e),
        ...         traceback.format_exc()
        ...     )
    """
    engine = get_database_engine()

    # Validar status
    if status not in ("completed", "failed"):
        raise ValueError(
            f"Status inválido: '{status}'. "
            f"Solo se permiten 'completed' o 'failed'."
        )

    # Si es failed, error_message es obligatorio
    if status == "failed" and not error_message:
        raise ValueError("error_message es obligatorio cuando status='failed'")

    update_query = """
        UPDATE job_runs
        SET
            status = :status,
            finished_at = :finished_at,
            error_message = :error_message,
            error_traceback = :error_traceback
        WHERE id = :run_id
    """

    finished_at = datetime.now(timezone.utc)

    try:
        with engine.connect() as conn:
            conn.execute(
                text(update_query),
                {
                    "run_id": run_id,
                    "status": status,
                    "finished_at": finished_at,
                    "error_message": error_message,
                    "error_traceback": error_traceback
                }
            )
            conn.commit()

        if status == "completed":
            logger.info(f"✅ Job run {run_id} completado exitosamente")
        else:
            logger.error(
                f"❌ Job run {run_id} falló: {error_message}"
            )

    except Exception as e:
        logger.error(f"❌ Error actualizando job status: {e}")
        raise


# ============================================================
# FUNCIONES DE CONSULTA (Para Debugging/Monitoring)
# ============================================================

def get_latest_runs(job_name: str, limit: int = 10) -> list:
    """
    Obtiene las últimas N ejecuciones de un job.

    Útil para debugging y monitoreo.

    Args:
        job_name: Nombre del job
        limit: Número de runs a retornar (default: 10)

    Returns:
        Lista de tuplas (id, target_date, status, started_at, finished_at, duration_seconds)
    """
    engine = get_database_engine()

    query = """
        SELECT
            id,
            target_date,
            status,
            started_at,
            finished_at,
            EXTRACT(EPOCH FROM (finished_at - started_at)) AS duration_seconds
        FROM job_runs
        WHERE job_name = :job_name
        ORDER BY started_at DESC
        LIMIT :limit
    """

    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(query),
                {"job_name": job_name, "limit": limit}
            )
            rows = result.fetchall()

        return rows

    except Exception as e:
        logger.error(f"❌ Error consultando runs: {e}")
        return []


def get_failed_runs(job_name: str, days: int = 7) -> list:
    """
    Obtiene runs fallidos en los últimos N días.

    Args:
        job_name: Nombre del job
        days: Días hacia atrás (default: 7)

    Returns:
        Lista de tuplas (id, target_date, started_at, error_message)
    """
    engine = get_database_engine()

    query = """
        SELECT
            id,
            target_date,
            started_at,
            error_message
        FROM job_runs
        WHERE job_name = :job_name
          AND status = 'failed'
          AND started_at >= NOW() - INTERVAL ':days days'
        ORDER BY started_at DESC
    """

    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(query),
                {"job_name": job_name, "days": days}
            )
            rows = result.fetchall()

        return rows

    except Exception as e:
        logger.error(f"❌ Error consultando runs fallidos: {e}")
        return []
