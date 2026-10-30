-- ============================================================
-- Migration 003: Failed Tasks Table (Dead Letter Queue)
-- ============================================================
-- Descripción: Dead Letter Queue para tareas Celery que agotan reintentos
-- Propósito: Análisis post-mortem, reprocesamiento manual, debugging
-- Arquitectura: Persistencia de tareas fallidas tras max_retries
-- Fecha: 2026-10-30
-- ============================================================

-- ============================================================
-- 1. CREACIÓN DE TABLA failed_tasks (DLQ)
-- ============================================================

CREATE TABLE IF NOT EXISTS failed_tasks (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,

    -- Task Identification
    task_id VARCHAR(255) NOT NULL UNIQUE,
    task_name VARCHAR(255) NOT NULL,

    -- Task Arguments
    args TEXT,
    kwargs TEXT,

    -- Error Details
    error_message TEXT NOT NULL,
    error_traceback TEXT,

    -- Retry Information
    retries INT NOT NULL DEFAULT 0,

    -- Timestamps
    failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reprocessed_at TIMESTAMPTZ,

    -- Reprocessing Status
    reprocess_status VARCHAR(20) CHECK (reprocess_status IN ('pending', 'reprocessing', 'completed', 'abandoned')),
    reprocess_notes TEXT,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 2. ÍNDICES PARA CONSULTAS Y MONITOREO
-- ============================================================

-- Índice para búsqueda por task_id (único)
CREATE UNIQUE INDEX idx_failed_tasks_task_id
ON failed_tasks (task_id);

-- Índice para consultas por task_name
CREATE INDEX idx_failed_tasks_task_name
ON failed_tasks (task_name);

-- Índice para consultas temporales (últimos fallos)
CREATE INDEX idx_failed_tasks_failed_at
ON failed_tasks (failed_at DESC);

-- Índice para tareas pendientes de reprocesamiento
CREATE INDEX idx_failed_tasks_reprocess_status
ON failed_tasks (reprocess_status)
WHERE reprocess_status = 'pending';

-- ============================================================
-- 3. COMENTARIOS DE DOCUMENTACIÓN
-- ============================================================

COMMENT ON TABLE failed_tasks IS 'Dead Letter Queue para tareas Celery que agotan max_retries. Propósito: análisis post-mortem, reprocesamiento manual, debugging.';

COMMENT ON COLUMN failed_tasks.task_id IS 'UUID único de la tarea Celery (AsyncResult ID).';
COMMENT ON COLUMN failed_tasks.task_name IS 'Nombre de la función decorada con @celery_app.task (ej: "process_telemetry_batch").';
COMMENT ON COLUMN failed_tasks.args IS 'Argumentos posicionales serializados como string.';
COMMENT ON COLUMN failed_tasks.kwargs IS 'Argumentos nombrados serializados como string.';
COMMENT ON COLUMN failed_tasks.error_message IS 'Mensaje de la excepción que causó el fallo.';
COMMENT ON COLUMN failed_tasks.error_traceback IS 'Stack trace completo de la excepción.';
COMMENT ON COLUMN failed_tasks.retries IS 'Número de intentos realizados antes del fallo definitivo (max_retries).';
COMMENT ON COLUMN failed_tasks.failed_at IS 'Timestamp del fallo definitivo (tras agotar reintentos).';
COMMENT ON COLUMN failed_tasks.reprocessed_at IS 'Timestamp de reprocesamiento manual (si aplicó).';
COMMENT ON COLUMN failed_tasks.reprocess_status IS 'Estado del reprocesamiento: pending | reprocessing | completed | abandoned.';
COMMENT ON COLUMN failed_tasks.reprocess_notes IS 'Notas manuales sobre el reprocesamiento (razón, resultados, etc.).';

-- ============================================================
-- 4. FUNCIÓN HELPER: OBTENER TAREAS FALLIDAS RECIENTES
-- ============================================================

CREATE OR REPLACE FUNCTION get_recent_failed_tasks(limit_count INT DEFAULT 10)
RETURNS TABLE(
    task_id VARCHAR,
    task_name VARCHAR,
    error_message TEXT,
    retries INT,
    failed_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ft.task_id,
        ft.task_name,
        ft.error_message,
        ft.retries,
        ft.failed_at
    FROM failed_tasks ft
    WHERE ft.reprocess_status IS NULL OR ft.reprocess_status = 'pending'
    ORDER BY ft.failed_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_recent_failed_tasks IS 'Obtiene las N tareas fallidas más recientes pendientes de reprocesamiento.';

-- ============================================================
-- 5. FUNCIÓN HELPER: ESTADÍSTICAS DE FALLOS POR TAREA
-- ============================================================

CREATE OR REPLACE FUNCTION get_task_failure_stats(days INT DEFAULT 7)
RETURNS TABLE(
    task_name VARCHAR,
    total_failures BIGINT,
    avg_retries NUMERIC,
    last_failure TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ft.task_name,
        COUNT(*) as total_failures,
        AVG(ft.retries)::NUMERIC(5,2) as avg_retries,
        MAX(ft.failed_at) as last_failure
    FROM failed_tasks ft
    WHERE ft.failed_at >= NOW() - (days || ' days')::INTERVAL
    GROUP BY ft.task_name
    ORDER BY total_failures DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_task_failure_stats IS 'Estadísticas de fallos por tipo de tarea en los últimos N días.';

-- ============================================================
-- 6. FUNCIÓN HELPER: MARCAR TAREA PARA REPROCESAMIENTO
-- ============================================================

CREATE OR REPLACE FUNCTION mark_task_for_reprocessing(
    p_task_id VARCHAR,
    p_notes TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    updated_rows INT;
BEGIN
    UPDATE failed_tasks
    SET
        reprocess_status = 'pending',
        reprocess_notes = COALESCE(p_notes, reprocess_notes),
        reprocessed_at = NOW()
    WHERE task_id = p_task_id
      AND (reprocess_status IS NULL OR reprocess_status = 'abandoned');

    GET DIAGNOSTICS updated_rows = ROW_COUNT;

    RETURN updated_rows > 0;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION mark_task_for_reprocessing IS 'Marca una tarea fallida para reprocesamiento manual.';

-- ============================================================
-- 7. VERIFICACIÓN DE MIGRACIÓN
-- ============================================================

-- Verificar tabla creada
SELECT
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE tablename = 'failed_tasks';

-- Verificar índices creados
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'failed_tasks'
ORDER BY indexname;

-- Verificar funciones creadas
SELECT
    proname AS function_name,
    prokind AS kind,
    pg_get_function_arguments(oid) AS arguments
FROM pg_proc
WHERE proname IN ('get_recent_failed_tasks', 'get_task_failure_stats', 'mark_task_for_reprocessing');

-- Test de inserción (debe funcionar)
-- INSERT INTO failed_tasks (task_id, task_name, error_message, retries)
-- VALUES ('test-uuid-123', 'test_task', 'Test error message', 3);

-- Test de función de consulta
-- SELECT * FROM get_recent_failed_tasks(5);

-- Test de función de stats
-- SELECT * FROM get_task_failure_stats(7);

-- Limpiar test
-- DELETE FROM failed_tasks WHERE task_id = 'test-uuid-123';

-- ============================================================
-- FIN DE MIGRACIÓN
-- ============================================================
