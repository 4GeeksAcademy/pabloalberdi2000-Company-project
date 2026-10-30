-- ============================================================
-- Migration 002: Job Runs Table (Orchestration Layer)
-- ============================================================
-- Descripción: Tabla de orquestación para jobs nocturnos
-- Propósito: Lock distribuido, idempotencia, auditoría de ejecuciones
-- Arquitectura: Separada de pipeline_runs (capa ETL interna)
-- Fecha: 2026-10-30
-- ============================================================

-- ============================================================
-- 1. CREACIÓN DE TABLA job_runs
-- ============================================================

CREATE TABLE IF NOT EXISTS job_runs (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,

    -- Identificación del Job
    job_name VARCHAR(100) NOT NULL,
    target_date DATE NOT NULL,

    -- Estado del Ciclo de Vida
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),

    -- Timestamps de Ejecución
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,

    -- Error Handling
    error_message TEXT,
    error_traceback TEXT,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 2. ÍNDICES PARA LOCK DISTRIBUIDO E IDEMPOTENCIA
-- ============================================================

-- Índice compuesto para validación de lock e idempotencia
-- Usado en: has_processing_lock(), has_completed_for_date()
CREATE UNIQUE INDEX idx_job_runs_unique_date
ON job_runs (job_name, target_date);

-- Índice para queries por status (lock distribuido)
CREATE INDEX idx_job_runs_status
ON job_runs (job_name, status)
WHERE status = 'processing';

-- Índice para queries temporales
CREATE INDEX idx_job_runs_started_at
ON job_runs (started_at DESC);

-- ============================================================
-- 3. COMENTARIOS DE DOCUMENTACIÓN
-- ============================================================

COMMENT ON TABLE job_runs IS 'Tabla de orquestación para jobs nocturnos. Provee lock distribuido, idempotencia y auditoría. Arquitectura: Capa externa separada de pipeline_runs (capa ETL interna).';

COMMENT ON COLUMN job_runs.job_name IS 'Nombre del job (ej: "nightly_export"). Usado para lock distribuido.';
COMMENT ON COLUMN job_runs.target_date IS 'Fecha analítica procesada (DATE). Clave para idempotencia: un job solo corre una vez por fecha.';
COMMENT ON COLUMN job_runs.status IS 'Estado del ciclo: pending → processing → completed/failed. "processing" actúa como lock distribuido.';
COMMENT ON COLUMN job_runs.started_at IS 'Timestamp de inicio de ejecución.';
COMMENT ON COLUMN job_runs.finished_at IS 'Timestamp de finalización (NULL si en curso).';
COMMENT ON COLUMN job_runs.error_message IS 'Mensaje de error (NULL si exitoso). Siempre se setea en status=failed.';

-- ============================================================
-- 4. CONSTRAINT ADICIONAL: FINISHED_AT OBLIGATORIO EN COMPLETED/FAILED
-- ============================================================

-- Trigger para asegurar que finished_at se setea en completed/failed
CREATE OR REPLACE FUNCTION ensure_finished_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status IN ('completed', 'failed') AND NEW.finished_at IS NULL THEN
        NEW.finished_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_ensure_finished_at
BEFORE UPDATE ON job_runs
FOR EACH ROW
WHEN (NEW.status IN ('completed', 'failed'))
EXECUTE FUNCTION ensure_finished_at();

-- ============================================================
-- 5. VALIDACIÓN: TRANSICIONES DE ESTADO VÁLIDAS
-- ============================================================

-- Trigger para validar transiciones de estado
CREATE OR REPLACE FUNCTION validate_job_status_transition()
RETURNS TRIGGER AS $$
BEGIN
    -- Validar transiciones permitidas:
    -- pending → processing
    -- processing → completed
    -- processing → failed
    -- (no permitir completed/failed → processing)

    IF OLD.status IN ('completed', 'failed') AND NEW.status = 'processing' THEN
        RAISE EXCEPTION 'No se puede regresar a processing desde % para job_name=%, target_date=%',
            OLD.status, NEW.job_name, NEW.target_date;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_validate_status_transition
BEFORE UPDATE ON job_runs
FOR EACH ROW
WHEN (OLD.status IS DISTINCT FROM NEW.status)
EXECUTE FUNCTION validate_job_status_transition();

-- ============================================================
-- 6. FUNCIÓN HELPER: LIMPIAR LOCKS ZOMBIE (EMERGENCY)
-- ============================================================

-- Función de emergencia para liberar locks zombie (jobs en processing > 1 hora)
-- SOLO usar manualmente en caso de crash del script nocturno
CREATE OR REPLACE FUNCTION cleanup_zombie_locks(max_age_hours INT DEFAULT 1)
RETURNS TABLE(job_name VARCHAR, target_date DATE, started_at TIMESTAMPTZ) AS $$
BEGIN
    RETURN QUERY
    UPDATE job_runs
    SET status = 'failed',
        error_message = 'Zombie lock cleanup: job stuck in processing for > ' || max_age_hours || ' hours',
        finished_at = NOW()
    WHERE status = 'processing'
      AND started_at < NOW() - (max_age_hours || ' hours')::INTERVAL
    RETURNING job_runs.job_name, job_runs.target_date, job_runs.started_at;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_zombie_locks IS 'EMERGENCIA: Libera locks zombie (jobs en processing > N horas). Solo usar manualmente tras crash del script.';

-- ============================================================
-- 7. VERIFICACIÓN DE MIGRACIÓN
-- ============================================================

-- Verificar tabla creada
SELECT
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE tablename = 'job_runs';

-- Verificar índices creados
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'job_runs'
ORDER BY indexname;

-- Verificar triggers
SELECT
    tgname AS trigger_name,
    proname AS function_name
FROM pg_trigger
JOIN pg_proc ON pg_trigger.tgfoid = pg_proc.oid
WHERE tgrelid = 'job_runs'::regclass;

-- Test de inserción (debe funcionar)
-- INSERT INTO job_runs (job_name, target_date, status)
-- VALUES ('migration_test', CURRENT_DATE, 'pending');

-- Test de constraint único (debe fallar - duplicate)
-- INSERT INTO job_runs (job_name, target_date, status)
-- VALUES ('migration_test', CURRENT_DATE, 'pending');

-- Test de transición inválida (debe fallar - no completed → processing)
-- UPDATE job_runs SET status = 'completed' WHERE job_name = 'migration_test';
-- UPDATE job_runs SET status = 'processing' WHERE job_name = 'migration_test';

-- Limpiar test
-- DELETE FROM job_runs WHERE job_name = 'migration_test';

-- ============================================================
-- FIN DE MIGRACIÓN
-- ============================================================
