"""
Nightly Export Script - Brasaland Digital

Script nocturno automatizado para:
1. Exportar telemetría del día anterior a CSV (backup/auditoría)
2. Ejecutar pipeline de datos como subproceso
3. Garantizar idempotencia y lock distribuido

Arquitectura:
- Proceso completamente independiente de FastAPI
- Lock distribuido nativo vía tabla job_runs
- Exportación CSV a data/raw/ (snapshot de backup)
- Pipeline lee directamente de BD (no del CSV)

Ejecución:
    # Modo automático (ayer)
    python scripts/nightly_export.py

    # Modo manual (fecha específica)
    TARGET_DATE=2026-10-29 python scripts/nightly_export.py

    # Con dry-run (sin ejecutar pipeline)
    DRY_RUN=true python scripts/nightly_export.py

Cron:
    # Ejecutar diariamente a las 2:00 AM UTC
    0 2 * * * cd /path/to/project && python scripts/nightly_export.py >> logs/nightly.log 2>&1
"""

import logging
import os
import subprocess
import sys
import traceback
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

# Agregar raíz del proyecto al path para imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.api.app.services.job_runner import (
    has_processing_lock,
    has_completed_for_date,
    create_job_run,
    update_job_status,
    JobRun
)

# ============================================================
# CONFIGURACIÓN
# ============================================================

JOB_NAME = "nightly_export"

# Directorio de salida para CSVs
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("nightly_export")


# ============================================================
# UTILIDADES
# ============================================================

def resolve_target_date() -> date:
    """
    Resuelve la fecha objetivo para el procesamiento.

    Lógica:
    1. Si existe variable de entorno TARGET_DATE (YYYY-MM-DD), usar esa fecha
    2. Si no, calcular "Ayer" en UTC

    Returns:
        Fecha objetivo (date)

    Example:
        >>> # Sin TARGET_DATE
        >>> resolve_target_date()  # Ayer

        >>> # Con TARGET_DATE=2026-10-29
        >>> resolve_target_date()  # 2026-10-29
    """
    target_date_str = os.getenv("TARGET_DATE")

    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            logger.info(f"📅 Fecha objetivo desde TARGET_DATE: {target_date}")
            return target_date
        except ValueError as e:
            logger.error(
                f"❌ TARGET_DATE inválido: '{target_date_str}'. "
                f"Formato esperado: YYYY-MM-DD. Error: {e}"
            )
            sys.exit(1)

    # Calcular "Ayer" en UTC
    now_utc = datetime.now(timezone.utc)
    yesterday = (now_utc - timedelta(days=1)).date()

    logger.info(f"📅 Fecha objetivo (ayer UTC): {yesterday}")

    return yesterday


def export_telemetry_to_csv(target_date: date) -> Path:
    """
    Exporta eventos de telemetría a CSV.

    Propósito: Snapshot de backup/auditoría en data/raw/

    Args:
        target_date: Fecha de los eventos a exportar

    Returns:
        Path del archivo CSV creado

    Raises:
        Exception: Si falla la exportación
    """
    csv_filename = f"telemetry_{target_date.isoformat()}.csv"
    csv_path = DATA_RAW_DIR / csv_filename

    # Si el archivo ya existe, omitir exportación
    if csv_path.exists():
        logger.info(
            f"📄 CSV ya existe: {csv_path}. Omitir exportación."
        )
        return csv_path

    logger.info(f"📤 Exportando telemetría a: {csv_path}")

    # Importar dependencias de BD
    from sqlalchemy import create_engine, text
    import pandas as pd

    DATABASE_URL = os.getenv(
        "SUPABASE_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/postgres"
    )

    engine = create_engine(DATABASE_URL)

    # Query para extraer eventos del día objetivo
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
        WHERE DATE(timestamp) = :target_date
        ORDER BY timestamp ASC
    """

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                text(query),
                conn,
                params={"target_date": target_date.isoformat()}
            )

        if df.empty:
            logger.warning(
                f"📭 Sin eventos para fecha {target_date}. "
                f"Creando CSV vacío."
            )
        else:
            logger.info(f"📊 Extraídos {len(df):,} eventos")

        # Exportar a CSV
        df.to_csv(csv_path, index=False, encoding="utf-8")

        file_size_mb = csv_path.stat().st_size / (1024 * 1024)
        logger.info(
            f"✅ CSV exportado: {csv_path} ({file_size_mb:.2f} MB)"
        )

        return csv_path

    except Exception as e:
        logger.error(f"❌ Error exportando CSV: {e}")
        raise


def run_pipeline_subprocess(target_date: date) -> subprocess.CompletedProcess:
    """
    Ejecuta el pipeline de datos como subproceso.

    Estrategia:
    - Invocar entrypoint CLI del pipeline (pipeline_v2.py)
    - Capturar stdout/stderr y exit code
    - Timeout de 30 minutos (1800 segundos)

    Args:
        target_date: Fecha objetivo para el pipeline

    Returns:
        CompletedProcess con resultado de la ejecución

    Raises:
        subprocess.CalledProcessError: Si el pipeline falla (exit code != 0)
        subprocess.TimeoutExpired: Si el pipeline tarda más de 30 minutos
    """
    # Path del entrypoint del pipeline
    pipeline_path = PROJECT_ROOT / "data" / "pipelines" / "business-performance" / "pipeline_v2.py"

    if not pipeline_path.exists():
        raise FileNotFoundError(
            f"Pipeline no encontrado: {pipeline_path}"
        )

    # Calcular start_date y end_date para el pipeline
    # El pipeline espera un rango [start_date, end_date)
    start_date = target_date
    end_date = target_date + timedelta(days=1)

    # Comando a ejecutar
    cmd = [
        sys.executable,  # Usar el mismo intérprete de Python
        str(pipeline_path),
        "--start-date", start_date.isoformat(),
        "--end-date", end_date.isoformat(),
        "--triggered-by", "scheduled"
    ]

    logger.info(f"🚀 Ejecutando pipeline: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minutos
            check=True  # Raise exception si exit code != 0
        )

        logger.info(f"✅ Pipeline completado exitosamente (exit code: 0)")

        # Log de stdout (últimas 10 líneas)
        if result.stdout:
            stdout_lines = result.stdout.strip().split("\n")
            logger.info(
                f"📜 Pipeline stdout (últimas 10 líneas):\n"
                + "\n".join(stdout_lines[-10:])
            )

        return result

    except subprocess.CalledProcessError as e:
        logger.error(
            f"❌ Pipeline falló (exit code: {e.returncode})"
        )

        # Log de stderr
        if e.stderr:
            stderr_lines = e.stderr.strip().split("\n")
            logger.error(
                f"📜 Pipeline stderr:\n"
                + "\n".join(stderr_lines[-20:])  # Últimas 20 líneas
            )

        raise

    except subprocess.TimeoutExpired as e:
        logger.error(
            f"❌ Pipeline timeout (>30 min). Terminando proceso..."
        )
        raise


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def main() -> int:
    """
    Función principal del script nocturno.

    Flujo:
    1. Resolver fecha objetivo
    2. Validar idempotencia (¿ya completado?)
    3. Validar lock distribuido (¿ya en ejecución?)
    4. Crear job run (estado: processing)
    5. Exportar CSV
    6. Ejecutar pipeline como subproceso
    7. Actualizar job run (estado: completed/failed)

    Returns:
        Exit code (0 = éxito, 1 = error)
    """
    logger.info("=" * 80)
    logger.info("🌙 NIGHTLY EXPORT - BRASALAND DIGITAL")
    logger.info("=" * 80)

    job_run = None

    try:
        # ============================================================
        # 1. RESOLVER FECHA OBJETIVO
        # ============================================================

        target_date = resolve_target_date()

        # ============================================================
        # 2. VALIDAR IDEMPOTENCIA
        # ============================================================

        if has_completed_for_date(JOB_NAME, target_date):
            logger.info(
                f"✅ Job '{JOB_NAME}' ya completado para {target_date}. "
                f"Omitir por idempotencia."
            )
            return 0

        # ============================================================
        # 3. VALIDAR LOCK DISTRIBUIDO
        # ============================================================

        if has_processing_lock(JOB_NAME):
            logger.warning(
                f"🔒 Job '{JOB_NAME}' ya en ejecución. "
                f"Abortar para prevenir ejecución paralela."
            )
            return 0

        # ============================================================
        # 4. CREAR JOB RUN (Lock distribuido activado)
        # ============================================================

        job_run = create_job_run(JOB_NAME, target_date)

        logger.info(f"🆔 Job run ID: {job_run.id}")

        # ============================================================
        # 5. EXPORTAR CSV
        # ============================================================

        csv_path = export_telemetry_to_csv(target_date)

        # ============================================================
        # 6. EJECUTAR PIPELINE (solo si no es DRY_RUN)
        # ============================================================

        if os.getenv("DRY_RUN", "").lower() in ("true", "1", "yes"):
            logger.info("🏃 DRY_RUN mode: Omitir ejecución de pipeline")
        else:
            result = run_pipeline_subprocess(target_date)

        # ============================================================
        # 7. FINALIZACIÓN EXITOSA
        # ============================================================

        update_job_status(job_run.id, "completed")

        logger.info("=" * 80)
        logger.info("✅ NIGHTLY EXPORT COMPLETADO EXITOSAMENTE")
        logger.info("=" * 80)
        logger.info(f"Job run ID: {job_run.id}")
        logger.info(f"Fecha objetivo: {target_date}")
        logger.info(f"CSV exportado: {csv_path}")
        logger.info("=" * 80)

        return 0

    except Exception as e:
        # ============================================================
        # MANEJO DE ERRORES GLOBAL
        # ============================================================

        error_message = str(e)
        error_traceback = traceback.format_exc()

        logger.error("=" * 80)
        logger.error("❌ NIGHTLY EXPORT FALLÓ")
        logger.error("=" * 80)
        logger.error(f"Error: {error_message}")
        logger.error(f"Traceback:\n{error_traceback}")
        logger.error("=" * 80)

        # Actualizar job run a failed (si fue creado)
        if job_run:
            try:
                update_job_status(
                    job_run.id,
                    "failed",
                    error_message,
                    error_traceback
                )
            except Exception as update_error:
                logger.error(
                    f"❌ Error actualizando job status: {update_error}"
                )

        return 1


# ============================================================
# ENTRYPOINT CLI
# ============================================================

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
