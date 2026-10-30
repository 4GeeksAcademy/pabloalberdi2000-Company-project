"""
Celery Application - Brasaland Digital

Configuración de Celery para procesamiento asíncrono de tareas pesadas.

Arquitectura:
- Broker: Redis (mensajes ligeros con IDs)
- Result Backend: Redis (resultados y estados)
- Workers: Procesos independientes de FastAPI
- Monitoring: Flower (UI web en puerto 5555)

Principios de Diseño:
1. Mensajes Ligeros: Solo enviar IDs, workers cargan datos
2. Confirmación tras Éxito: ACK solo si task completa exitosamente
3. Timeouts Obligatorios: Cada task tiene límite de ejecución
4. Reintentos con Backoff: 3 intentos con delay exponencial
5. Dead Letter Queue: Persistir tareas fallidas tras max_retries

Uso:
    # Encolar tarea desde FastAPI
    from app.celery_app import process_telemetry_batch

    task = process_telemetry_batch.delay(batch_id=123)
    return {"task_id": task.id}

    # Consultar estado
    from app.celery_app import celery_app
    result = celery_app.AsyncResult(task_id)
    return {"status": result.status, "result": result.result}

Workers:
    # Iniciar worker (proceso independiente)
    celery -A app.celery_app.celery_app worker --loglevel=info --concurrency=4

    # Monitoreo con Flower
    celery -A app.celery_app.celery_app flower --port=5555
"""

import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from celery import Celery
from celery.signals import task_failure, task_success
from sqlalchemy import create_engine, text

# ============================================================
# CONFIGURACIÓN
# ============================================================

logger = logging.getLogger(__name__)

# URLs de conexión
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv(
    "SUPABASE_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres"
)

# Configuración de Celery
celery_app = Celery(
    "brasaland_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Configuración avanzada
celery_app.conf.update(
    # Serialización
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Timeouts globales
    task_time_limit=1800,  # 30 minutos hard limit
    task_soft_time_limit=1620,  # 27 minutos soft limit (warning)

    # Reintentos
    task_acks_late=True,  # ACK solo tras éxito
    task_reject_on_worker_lost=True,  # Re-encolar si worker muere

    # Result backend
    result_expires=3600,  # Resultados expiran en 1 hora
    result_persistent=True,  # Persistir en Redis AOF

    # Worker
    worker_prefetch_multiplier=1,  # 1 tarea por worker (mejor para long-running)
    worker_max_tasks_per_child=1000,  # Reciclar worker cada 1000 tareas

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)


# ============================================================
# DEAD LETTER QUEUE (DLQ)
# ============================================================

def persist_failed_task(
    task_id: str,
    task_name: str,
    args: tuple,
    kwargs: dict,
    exception: Exception,
    retries: int
) -> None:
    """
    Persiste tareas fallidas en base de datos tras agotar reintentos.

    Propósito: Dead Letter Queue para análisis post-mortem y reprocesamiento manual.

    Args:
        task_id: ID único de la tarea
        task_name: Nombre de la función (ej: "process_telemetry_batch")
        args: Argumentos posicionales
        kwargs: Argumentos nombrados
        exception: Excepción que causó el fallo
        retries: Número de intentos realizados
    """
    try:
        engine = create_engine(DATABASE_URL)

        insert_query = """
            INSERT INTO failed_tasks (
                task_id,
                task_name,
                args,
                kwargs,
                error_message,
                error_traceback,
                retries,
                failed_at
            ) VALUES (
                :task_id,
                :task_name,
                :args,
                :kwargs,
                :error_message,
                :error_traceback,
                :retries,
                :failed_at
            )
            ON CONFLICT (task_id) DO UPDATE SET
                error_message = EXCLUDED.error_message,
                error_traceback = EXCLUDED.error_traceback,
                retries = EXCLUDED.retries,
                failed_at = EXCLUDED.failed_at
        """

        with engine.connect() as conn:
            conn.execute(
                text(insert_query),
                {
                    "task_id": task_id,
                    "task_name": task_name,
                    "args": str(args),
                    "kwargs": str(kwargs),
                    "error_message": str(exception),
                    "error_traceback": traceback.format_exc(),
                    "retries": retries,
                    "failed_at": datetime.now(timezone.utc)
                }
            )
            conn.commit()

        logger.error(
            f"❌ DLQ: Tarea {task_id} ({task_name}) persistida tras {retries} intentos. "
            f"Error: {exception}"
        )

    except Exception as e:
        logger.error(
            f"❌ Error persistiendo tarea fallida en DLQ: {e}. "
            f"Task ID: {task_id}, Error original: {exception}"
        )


# ============================================================
# SIGNALS (Hooks de Ciclo de Vida)
# ============================================================

@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    """Hook ejecutado tras éxito de una tarea."""
    logger.info(
        f"✅ Tarea completada: {sender.name} | "
        f"ID: {kwargs.get('task_id')} | "
        f"Result: {result}"
    )


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, **kwargs):
    """Hook ejecutado tras fallo de una tarea."""
    logger.error(
        f"❌ Tarea fallida: {sender.name} | "
        f"ID: {task_id} | "
        f"Error: {exception}"
    )


# ============================================================
# TAREAS ASÍNCRONAS
# ============================================================

@celery_app.task(
    bind=True,
    name="process_telemetry_batch",
    max_retries=3,
    default_retry_delay=60,  # 1 minuto base
    autoretry_for=(Exception,),
    retry_backoff=True,  # Backoff exponencial: 60s, 120s, 240s
    retry_backoff_max=600,  # Máximo 10 minutos entre intentos
    retry_jitter=True  # Agregar jitter para evitar thundering herd
)
def process_telemetry_batch(self, batch_id: int) -> Dict[str, Any]:
    """
    Procesa un lote de eventos de telemetría de forma asíncrona.

    Operación: Carga eventos desde BD, calcula KPIs, persiste resultados.

    Diseño:
    - Mensaje ligero: Solo recibe batch_id (no datos completos)
    - Worker carga datos desde BD usando el ID
    - Timeout: 30 minutos hard limit
    - Reintentos: 3 intentos con backoff exponencial
    - DLQ: Persistir en failed_tasks tras agotar reintentos

    Args:
        batch_id: ID del lote de eventos a procesar

    Returns:
        Dict con resultado del procesamiento:
        {
            "batch_id": 123,
            "events_processed": 1500,
            "kpis_calculated": 45,
            "duration_seconds": 120.5,
            "completed_at": "2026-10-30T12:00:00Z"
        }

    Raises:
        Exception: Si falla tras 3 reintentos (persiste en DLQ)

    Example:
        # Desde FastAPI
        task = process_telemetry_batch.delay(batch_id=123)
        return {"task_id": task.id, "status": "pending"}

        # Consultar estado
        result = celery_app.AsyncResult(task_id)
        if result.ready():
            return {"status": "completed", "result": result.result}
    """
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"🚀 Iniciando procesamiento de lote {batch_id} | "
        f"Task ID: {self.request.id} | "
        f"Intento: {self.request.retries + 1}/3"
    )

    try:
        # ============================================================
        # 1. CARGAR EVENTOS DESDE BD (No desde mensaje)
        # ============================================================

        engine = create_engine(DATABASE_URL)

        query = """
            SELECT COUNT(*) as count
            FROM telemetry_events
            WHERE batch_id = :batch_id
        """

        with engine.connect() as conn:
            result = conn.execute(text(query), {"batch_id": batch_id})
            row = result.fetchone()
            events_count = row[0] if row else 0

        if events_count == 0:
            logger.warning(f"📭 Lote {batch_id} no contiene eventos")
            return {
                "batch_id": batch_id,
                "events_processed": 0,
                "kpis_calculated": 0,
                "duration_seconds": 0,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }

        logger.info(f"📊 Lote {batch_id}: {events_count} eventos encontrados")

        # ============================================================
        # 2. PROCESAR EVENTOS (Simulación)
        # ============================================================

        # TODO: Implementar lógica real de procesamiento
        # - Calcular KPIs (DAU, system availability, auth success rate, etc.)
        # - Persistir en reporting.business_kpis
        # - Actualizar marcas de agua

        import time
        time.sleep(5)  # Simulación de trabajo pesado

        kpis_calculated = events_count // 30  # Simulación

        # ============================================================
        # 3. PERSISTIR RESULTADOS
        # ============================================================

        # TODO: INSERT INTO reporting.business_kpis ...

        # ============================================================
        # 4. RETORNAR RESULTADO
        # ============================================================

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        result = {
            "batch_id": batch_id,
            "events_processed": events_count,
            "kpis_calculated": kpis_calculated,
            "duration_seconds": duration,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }

        logger.info(
            f"✅ Lote {batch_id} procesado exitosamente | "
            f"Eventos: {events_count} | "
            f"KPIs: {kpis_calculated} | "
            f"Duración: {duration:.2f}s"
        )

        return result

    except Exception as e:
        logger.error(
            f"❌ Error procesando lote {batch_id} | "
            f"Intento: {self.request.retries + 1}/3 | "
            f"Error: {e}"
        )

        # Si agotamos los reintentos, persistir en DLQ
        if self.request.retries >= self.max_retries:
            persist_failed_task(
                task_id=self.request.id,
                task_name=self.name,
                args=(batch_id,),
                kwargs={},
                exception=e,
                retries=self.request.retries
            )

        # Re-lanzar para activar retry automático
        raise


@celery_app.task(
    bind=True,
    name="generate_business_report",
    max_retries=3,
    default_retry_delay=120,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def generate_business_report(self, report_id: int, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Genera reporte de negocio agregando KPIs en un rango de fechas.

    Operación: Consulta KPIs desde BD, calcula agregaciones, exporta PDF/Excel.

    Args:
        report_id: ID del reporte a generar
        start_date: Fecha inicio (YYYY-MM-DD)
        end_date: Fecha fin (YYYY-MM-DD)

    Returns:
        Dict con resultado de la generación:
        {
            "report_id": 456,
            "file_path": "/reports/business_report_456.pdf",
            "kpis_included": 120,
            "duration_seconds": 45.2,
            "completed_at": "2026-10-30T12:05:00Z"
        }
    """
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"📊 Generando reporte {report_id} | "
        f"Rango: {start_date} - {end_date} | "
        f"Task ID: {self.request.id}"
    )

    try:
        # TODO: Implementar generación de reporte
        # - Consultar KPIs en rango de fechas
        # - Calcular agregaciones (promedio, suma, tendencias)
        # - Generar PDF/Excel con gráficos
        # - Subir a storage (S3, GCS, etc.)

        import time
        time.sleep(10)  # Simulación

        file_path = f"/reports/business_report_{report_id}.pdf"

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        result = {
            "report_id": report_id,
            "file_path": file_path,
            "kpis_included": 120,
            "duration_seconds": duration,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }

        logger.info(
            f"✅ Reporte {report_id} generado exitosamente | "
            f"Archivo: {file_path} | "
            f"Duración: {duration:.2f}s"
        )

        return result

    except Exception as e:
        logger.error(
            f"❌ Error generando reporte {report_id} | "
            f"Error: {e}"
        )

        if self.request.retries >= self.max_retries:
            persist_failed_task(
                task_id=self.request.id,
                task_name=self.name,
                args=(report_id, start_date, end_date),
                kwargs={},
                exception=e,
                retries=self.request.retries
            )

        raise


# ============================================================
# UTILIDADES PARA FastAPI
# ============================================================

def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Consulta el estado de una tarea asíncrona.

    Args:
        task_id: ID de la tarea (UUID retornado por .delay())

    Returns:
        Dict con estado actual:
        {
            "task_id": "uuid",
            "status": "pending | started | success | failure | retry",
            "result": {...} | null,
            "error": "..." | null
        }
    """
    result = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": result.status.lower(),
        "result": None,
        "error": None
    }

    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["error"] = str(result.info)

    return response
