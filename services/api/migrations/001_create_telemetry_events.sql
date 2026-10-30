-- ============================================================
-- Migration 001: Telemetry Events Table (Supabase/PostgreSQL)
-- ============================================================
-- Descripción: Tabla inmutable (append-only) para eventos de telemetría
-- Arquitectura: Event Sourcing / Log-Structured Storage
-- Backend: FastAPI + Supabase
-- Fecha: 2026-10-30
-- ============================================================

-- ============================================================
-- 1. CREACIÓN DE TABLA telemetry_events
-- ============================================================

CREATE TABLE IF NOT EXISTS telemetry_events (
    -- ========================================
    -- Columnas Fijas (Consultas Analíticas)
    -- ========================================

    -- Primary Key: Auto-incremental (BigSerial para escala)
    id BIGSERIAL PRIMARY KEY,

    -- Event Envelope Fields (columnas indexables)
    event_id UUID NOT NULL UNIQUE,
    event_type VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,

    -- Context Fields (nullable para eventos anónimos/backend)
    session_id VARCHAR(100),
    user_id UUID,
    request_id UUID,

    -- Schema Versioning
    schema_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',

    -- Service Origin (para multi-service architectures futuras)
    service VARCHAR(50) NOT NULL DEFAULT 'backoffice',

    -- ========================================
    -- Payload JSONB (Allowlist Properties)
    -- ========================================

    -- Tags: Objeto properties del evento (JSONB para queries eficientes)
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- ========================================
    -- Metadata de Ingestion
    -- ========================================

    -- Timestamp de ingestion (server-side)
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Batch ID para correlación (opcional)
    batch_id UUID
);

-- ============================================================
-- 2. COMENTARIOS DE DOCUMENTACIÓN
-- ============================================================

COMMENT ON TABLE telemetry_events IS 'Tabla inmutable (append-only) de eventos de telemetría. Event Sourcing pattern: cada fila es un hecho inmutable. NO soporta UPDATE ni DELETE.';

COMMENT ON COLUMN telemetry_events.event_id IS 'UUID v4 único del evento. Generado por TelemetryService en frontend.';
COMMENT ON COLUMN telemetry_events.event_type IS 'Tipo de evento en formato entidad_acción (snake_case). Ej: page_view, login_attempt_failed.';
COMMENT ON COLUMN telemetry_events.timestamp IS 'Marca temporal ISO 8601 UTC del evento (client-side).';
COMMENT ON COLUMN telemetry_events.session_id IS 'ID de sesión del usuario (nullable para eventos backend sin sesión).';
COMMENT ON COLUMN telemetry_events.user_id IS 'UUID del usuario autenticado (nullable para flujos anónimos).';
COMMENT ON COLUMN telemetry_events.request_id IS 'UUID para correlación distribuida entre frontend-backend.';
COMMENT ON COLUMN telemetry_events.schema_version IS 'Versión semántica del schema (MAJOR.MINOR.PATCH). Permite evolución de eventos.';
COMMENT ON COLUMN telemetry_events.service IS 'Servicio origen del evento (backoffice, api, mobile). Para multi-service architectures.';
COMMENT ON COLUMN telemetry_events.tags IS 'Payload JSONB con propiedades específicas del evento. Solo contiene claves del allowlist definido en event-schemas.json.';
COMMENT ON COLUMN telemetry_events.ingested_at IS 'Timestamp de ingestion en servidor (server-side). Diferencia con timestamp (client-side) mide latencia de red.';
COMMENT ON COLUMN telemetry_events.batch_id IS 'UUID del batch de ingestion. Correlaciona eventos enviados en el mismo lote por TelemetryService.';

-- ============================================================
-- 3. ÍNDICES PARA ESCALA
-- ============================================================

-- Índice B-Tree en timestamp (queries por rango temporal)
-- Usado en: Dashboards con filtros de fecha, alertas temporales
CREATE INDEX idx_telemetry_events_timestamp
ON telemetry_events (timestamp DESC);

-- Índice B-Tree en event_type (queries por tipo de evento)
-- Usado en: Métricas agregadas por tipo, filtros de evento específico
CREATE INDEX idx_telemetry_events_event_type
ON telemetry_events (event_type);

-- Índice compuesto timestamp + event_type (queries frecuentes)
-- Usado en: "Todos los login_attempt_failed de las últimas 24h"
CREATE INDEX idx_telemetry_events_timestamp_type
ON telemetry_events (timestamp DESC, event_type);

-- Índice GIN sobre tags (JSONB)
-- Permite queries eficientes con operadores @>, ?, ?&, ?|
-- Ejemplos:
--   WHERE tags @> '{"warehouse": "medellin_centro"}'  (contiene clave-valor)
--   WHERE tags ? 'ingredient_id'                       (contiene clave)
--   WHERE tags ?& array['user_role', 'warehouse']      (contiene todas las claves)
CREATE INDEX idx_telemetry_events_tags_gin
ON telemetry_events USING GIN (tags);

-- Índice en user_id (queries por usuario)
-- Usado en: Auditoría de actividad de usuario, análisis de comportamiento
CREATE INDEX idx_telemetry_events_user_id
ON telemetry_events (user_id)
WHERE user_id IS NOT NULL;

-- Índice en session_id (queries por sesión)
-- Usado en: Reconstrucción de journey de usuario, debugging de sesión
CREATE INDEX idx_telemetry_events_session_id
ON telemetry_events (session_id)
WHERE session_id IS NOT NULL;

-- Índice en ingested_at (queries de monitoreo de ingesta)
-- Usado en: Detectar delays de ingestion, métricas de throughput
CREATE INDEX idx_telemetry_events_ingested_at
ON telemetry_events (ingested_at DESC);

-- ============================================================
-- 4. POLÍTICAS DE RETENCIÓN (Opcional - Fase 2)
-- ============================================================

-- NOTA: Esta tabla es append-only. La eliminación física de datos
-- se gestiona mediante particionamiento por timestamp (Fase 2) y
-- políticas de archivado a cold storage (S3/Glacier).
--
-- Hot storage: 90 días (particiones activas en PostgreSQL)
-- Warm storage: 90-365 días (particiones archivadas en PostgreSQL)
-- Cold storage: >365 días (exportar a Parquet en S3 y DROP partition)
--
-- Implementación sugerida (Fase 2):
-- - Particionamiento por RANGE (timestamp) con particiones mensuales
-- - Cron job que ejecuta pg_dump mensual + DROP partition antigua
-- - Lambda/Cloud Function para queries en cold storage (Athena/BigQuery)

-- ============================================================
-- 5. PERMISOS (Row Level Security - RLS)
-- ============================================================

-- Habilitar RLS en la tabla
ALTER TABLE telemetry_events ENABLE ROW LEVEL SECURITY;

-- Política: Solo el servicio backend puede insertar
-- (authentica con service role key de Supabase)
CREATE POLICY "Service role can insert telemetry events"
ON telemetry_events
FOR INSERT
TO service_role
WITH CHECK (true);

-- Política: Solo el servicio backend puede leer
-- (evita lectura desde frontend sin autorización)
CREATE POLICY "Service role can read telemetry events"
ON telemetry_events
FOR SELECT
TO service_role
USING (true);

-- Política: NO permitir UPDATE ni DELETE
-- (tabla inmutable - append-only)
-- NO crear políticas para UPDATE/DELETE garantiza inmutabilidad

-- ============================================================
-- 6. TRIGGERS DE AUDITORÍA (Opcional - Fase 2)
-- ============================================================

-- NOTA: En arquitectura event sourcing pura, los triggers de UPDATE/DELETE
-- deberían RECHAZAR la operación (RAISE EXCEPTION).
--
-- Implementación sugerida (Fase 2):
--
-- CREATE OR REPLACE FUNCTION prevent_telemetry_mutation()
-- RETURNS TRIGGER AS $$
-- BEGIN
--     RAISE EXCEPTION 'telemetry_events is append-only. UPDATE and DELETE are not allowed.';
-- END;
-- $$ LANGUAGE plpgsql;
--
-- CREATE TRIGGER prevent_update_on_telemetry_events
-- BEFORE UPDATE ON telemetry_events
-- FOR EACH ROW
-- EXECUTE FUNCTION prevent_telemetry_mutation();
--
-- CREATE TRIGGER prevent_delete_on_telemetry_events
-- BEFORE DELETE ON telemetry_events
-- FOR EACH ROW
-- EXECUTE FUNCTION prevent_telemetry_mutation();

-- ============================================================
-- 7. VERIFICACIÓN DE MIGRACIÓN
-- ============================================================

-- Verificar tabla creada
SELECT
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE tablename = 'telemetry_events';

-- Verificar índices creados
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'telemetry_events'
ORDER BY indexname;

-- Verificar políticas RLS
SELECT
    schemaname,
    tablename,
    policyname,
    cmd,
    qual
FROM pg_policies
WHERE tablename = 'telemetry_events';

-- Test de inserción (debe funcionar)
-- INSERT INTO telemetry_events (event_id, event_type, timestamp, tags)
-- VALUES (
--     gen_random_uuid(),
--     'migration_test',
--     NOW(),
--     '{"test": true, "migration": "001"}'::jsonb
-- );

-- Test de query (debe funcionar)
-- SELECT * FROM telemetry_events WHERE event_type = 'migration_test';

-- Test de JSONB query (debe usar índice GIN)
-- EXPLAIN ANALYZE
-- SELECT * FROM telemetry_events
-- WHERE tags @> '{"test": true}';

-- ============================================================
-- FIN DE MIGRACIÓN
-- ============================================================
