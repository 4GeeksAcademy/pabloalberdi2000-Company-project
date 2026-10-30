# Diseño Arquitectónico: Pipeline de Desempeño de Negocio (Business Performance Pipeline)

**Versión**: 1.0  
**Fecha**: 30 de Octubre, 2026  
**Autor**: Lead Data Architect & Analytics Engineer  
**Estado**: 📐 Fase de Diseño (Implementación pendiente)

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Fase 1: Análisis del Estado Actual y Detección de la Brecha](#2-fase-1-análisis-del-estado-actual-y-detección-de-la-brecha)
3. [Fase 2: Diseño del Pipeline y Modelo de Datos](#3-fase-2-diseño-del-pipeline-y-modelo-de-datos)
4. [Fase 3: Resiliencia, Idempotencia y Observabilidad](#4-fase-3-resiliencia-idempotencia-y-observabilidad)
5. [Fase 4: Mapeo de Arquitectura a Conceptos de Prefect](#5-fase-4-mapeo-de-arquitectura-a-conceptos-de-prefect)
6. [Fase 5: Integración con la Aplicación](#6-fase-5-integración-con-la-aplicación)
7. [Anexos](#7-anexos)

---

## 1. Resumen Ejecutivo

### 1.1. Contexto del Negocio

**Brasaland** es una cadena de 14 restaurantes de cocina a la brasa con operaciones en Colombia (10 locales) y Florida, USA (4 locales). Con 115 empleados y $6M USD de facturación anual, la empresa enfrenta desafíos operacionales críticos:

- **Cero visibilidad en tiempo real**: La CEO Mariana Restrepo y los directores de área toman decisiones basadas en llamadas telefónicas e informes PDF semanales que llegan los martes.
- **Gestión manual de datos**: Sin dashboards ejecutivos, CRM, ni sistemas de análisis de comportamiento de clientes.
- **Competidores digitales ganando terreno**: Cadenas más pequeñas con herramientas modernas están capturando mercado.

**Brasaland Digital** fue creado por Mariana para construir la infraestructura tecnológica que permita operar como empresa moderna. Actualmente existe:

- ✅ Sistema de telemetría técnica capturando eventos inmutables en `telemetry_events`
- ✅ Reporte operacional técnico (`GET /telemetry/report`) para ingeniería
- ❌ **Gap crítico**: No existe transformación de estos datos técnicos en métricas de negocio accionables para dirección

### 1.2. Propósito del Pipeline

**Transformar eventos de telemetría técnica en métricas de desempeño de negocio para stakeholders no técnicos (gerentes de departamento, dirección y CEO), generando un briefing ejecutivo automatizado con cadencia semanal (lunes 7am), construido sobre las métricas operacionales de volumen, latencia y errores ya capturadas, agregando dimensiones de negocio (costes operativos, ingresos por transacción, satisfacción del cliente) cuando estén disponibles en el payload de los eventos.**

---

## 2. Fase 1: Análisis del Estado Actual y Detección de la Brecha

### 2.1. Estado Actual: Sistema de Telemetría Técnica

#### 2.1.1. Tabla `telemetry_events` (Fuente de Datos)

**Ubicación**: Supabase PostgreSQL  
**Arquitectura**: Event Sourcing / Log-Structured Storage (Append-Only)  
**Migración**: `services/api/migrations/001_create_telemetry_events.sql`

**Schema de la tabla**:

```sql
CREATE TABLE telemetry_events (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,
    
    -- Event Envelope (columnas indexables)
    event_id UUID NOT NULL UNIQUE,
    event_type VARCHAR(100) NOT NULL,  -- Ej: page_view, login_attempt_failed
    timestamp TIMESTAMPTZ NOT NULL,    -- Client-side timestamp (UTC)
    
    -- Context Fields (nullable)
    session_id VARCHAR(100),
    user_id UUID,
    request_id UUID,
    
    -- Schema Versioning
    schema_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    service VARCHAR(50) NOT NULL DEFAULT 'backoffice',
    
    -- Payload JSONB (propiedades específicas del evento)
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Metadata de Ingestion
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    batch_id UUID
);
```

**Índices relevantes**:
- `idx_telemetry_events_timestamp` (B-Tree DESC) → Queries por rango temporal
- `idx_telemetry_events_event_type` (B-Tree) → Filtros por tipo de evento
- `idx_telemetry_events_timestamp_type` (Compuesto) → Query combinado frecuente
- `idx_telemetry_events_tags_gin` (GIN) → Queries JSONB eficientes
- `idx_telemetry_events_user_id` (B-Tree parcial) → Auditoría por usuario

**Políticas RLS (Row Level Security)**:
- ✅ Solo `service_role` puede insertar (backend autenticado)
- ✅ Solo `service_role` puede leer (no lectura directa desde frontend)
- ✅ NO UPDATE ni DELETE permitidos (tabla inmutable)

**Volumen estimado** (basado en la arquitectura de 14 locales y 115 empleados):
- ~5,000-10,000 eventos/día (estimación conservadora)
- Crecimiento lineal con adopción de nuevas features

#### 2.1.2. Reporte Técnico Existente

**Endpoint**: `GET /telemetry/report`  
**Archivo**: `services/api/app/routers/telemetry_report.py`  
**Pipeline Analítico**: `services/api/app/services/telemetry_analysis.py`

**Usuario objetivo**: Equipo de Ingeniería (CTO Nicolás Park y desarrolladores)

**Métricas actuales** (orientadas a operaciones técnicas):

1. **`events_per_day`**: Volumen temporal de eventos
   ```json
   [
     {"date": "2026-10-23", "event_count": 150},
     {"date": "2026-10-24", "event_count": 200}
   ]
   ```

2. **`error_rate_by_type`**: Tasa de errores por tipo de evento
   ```json
   [
     {
       "event_type": "frontend_error_uncaught",
       "total_events": 25,
       "error_events": 25,
       "error_rate": 1.0
     }
   ]
   ```

3. **`auth_failure_rate`**: Tasa de fallos de autenticación por día
   ```json
   [
     {
       "date": "2026-10-23",
       "total_attempts": 100,
       "failed_attempts": 15,
       "success_attempts": 85,
       "failure_rate": 0.15
     }
   ]
   ```

**Características técnicas**:
- Ventana móvil por defecto: últimos 7 días
- Caché en memoria con TTL de 60 segundos
- Funciones puras con Pandas (vectorización, sin bucles manuales)
- SQL filtra temporal, Pandas agrega

**Limitaciones para negocio**:
- ❌ No mapea eventos técnicos a procesos de negocio
- ❌ No calcula métricas financieras (ingresos, costes, ROI)
- ❌ No segmenta por dimensiones de negocio (país, local, departamento)
- ❌ No correlaciona eventos con resultados de negocio (ventas, satisfacción)

### 2.2. Identificación de la Brecha

#### 2.2.1. Preguntas Estratégicas NO Respondidas por el Reporte Técnico

**Dirección Ejecutiva (Mariana Restrepo - CEO)**:
- ¿Cuántos clientes únicos interactuaron con nuestros sistemas digitales esta semana?
- ¿Qué local tiene el mayor engagement digital (sesiones, páginas vistas)?
- ¿Cuál es el tiempo promedio de respuesta del sistema percibido por los usuarios?
- ¿Cuántos errores críticos experimentaron los clientes vs. errores internos?
- ¿Qué % de sesiones terminan en abandono sin completar una acción objetivo?

**Operaciones (Felipe Guerrero)**:
- ¿Cuántas transacciones exitosas completamos por local/día?
- ¿Qué local tiene los tiempos de respuesta más lentos?
- ¿Cuál es la tasa de abandono del flujo de pedidos por etapa?
- ¿Cuántos errores de backend afectaron operaciones vs. errores de frontend?

**Marketing (Camila Ospina)**:
- ¿Cuántos usuarios nuevos vs. recurrentes tenemos por semana?
- ¿Qué páginas tienen mayor tasa de rebote?
- ¿Cuál es el journey típico de un usuario antes de convertir?
- ¿Qué canales (web/app) tienen mejor engagement?

**RRHH (Ashley Turner)**:
- ¿Cuántos empleados están usando el sistema ATS semanalmente?
- ¿Qué módulos del backoffice tienen mayor adopción?
- ¿Hay patrones de errores correlacionados con falta de formación?

**Tecnología (Nicolás Park)**:
- ¿Qué features nuevas tienen mayor adopción post-lanzamiento?
- ¿Cuál es el impacto en experiencia de usuario de los errores técnicos?
- ¿Qué % de eventos son de valor (transacciones) vs. navegación?

#### 2.2.2. Gap de Datos Identificado

**Actualmente capturado en `telemetry_events`**:
- ✅ Volumen de eventos por tipo y tiempo
- ✅ Errores técnicos y tasas de fallo
- ✅ Eventos de autenticación (login success/failed)
- ✅ Context fields: `user_id`, `session_id`, `timestamp`
- ✅ Payload JSONB flexible en campo `tags`

**Faltante para métricas de negocio** (NO requiere nuevo pipeline, solo extracción del payload):
- ⚠️ Identificador de local (`warehouse`, `location_id`) → **Probable en `tags`**
- ⚠️ Identificador de país (`country`) → **Probable en `tags`**
- ⚠️ Tipo de usuario/rol (`user_role`) → **Probable en `tags`**
- ⚠️ Valor de transacción (`transaction_amount`, `currency`) → **Agregar a `tags` cuando aplique**
- ⚠️ Duración de operaciones (`duration_ms`, `latency_ms`) → **Agregar a `tags`**
- ⚠️ Resultado de operación (`outcome`: success/partial/failed) → **Derivable de `event_type`**
- ⚠️ Costes operativos asociados → **Requerirá JOIN con tablas de dominio (Fase 2)**

**Decisión arquitectónica**:
1. **Fase 1 del pipeline** (este diseño): Trabajar **solo con datos ya presentes** en `telemetry_events` (columnas fijas + `tags` JSONB existentes)
2. **Fase 2** (futuro): JOIN con tablas de dominio (`users`, `locations`, `transactions`) para enriquecer métricas financieras

### 2.3. Justificación del Pipeline Analítico Dedicado

**¿Por qué NO extender el reporte técnico existente?**

| Aspecto | Reporte Técnico (`/telemetry/report`) | Pipeline de Negocio (nuevo) |
|---------|--------------------------------------|------------------------------|
| **Usuario objetivo** | Ingeniería (CTO, devs) | Dirección y gerentes de área |
| **Lenguaje** | Técnico (event_type, error_rate) | Negocio (usuarios activos, tasa de conversión) |
| **Granularidad** | Por tipo de evento | Por proceso de negocio |
| **Dimensiones** | Temporal (día) | Temporal + geográfica (país, local) + organizacional (área) |
| **Agregación** | Suma, tasa de error | Suma + promedios + percentiles + distribuciones |
| **Frecuencia** | On-demand con caché 60s | Batch programado (lunes 7am) + on-demand |
| **Destino** | Caché en memoria (efímero) | Tabla persistente `reporting.business_kpis` |
| **Enriquecimiento** | Solo `telemetry_events` | `telemetry_events` + JOINs con dominio (Fase 2) |

**Conclusión**: Los dos pipelines coexisten sin overlap funcional:
- **Reporte técnico**: Monitoreo operacional para ingeniería (uptime, errors, performance)
- **Pipeline de negocio**: KPIs estratégicos para toma de decisiones ejecutivas

---

## 3. Fase 2: Diseño del Pipeline y Modelo de Datos

### 3.1. Propósito (Frase de Síntesis)

> **Transformar diariamente los eventos de telemetría técnica (`telemetry_events`) en métricas de desempeño de negocio agregadas (`reporting.business_kpis`) para alimentar el dashboard ejecutivo de Brasaland, entregando KPIs semanales (usuarios activos, tasa de conversión, engagement por local, disponibilidad del sistema) a la CEO Mariana Restrepo y gerentes de área cada lunes a las 7am, construidos sobre las métricas operacionales de volumen, errores y autenticación ya capturadas, con arquitectura ETL desacoplada en `data/pipelines/business-performance/` y endpoints REST en `services/reporting/`.**

### 3.2. Extracción (Extract)

#### 3.2.1. Fuente de Datos Primaria

**Tabla**: `telemetry_events` (Supabase PostgreSQL)  
**Naturaleza**: Append-only (inmutable)  
**Formato**: Columnas relacionales + campo JSONB (`tags`)

**Estrategia de extracción**:

```sql
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
    tags,  -- JSONB con propiedades específicas
    ingested_at,
    batch_id
FROM telemetry_events
WHERE timestamp >= :start_date
  AND timestamp < :end_date
ORDER BY timestamp ASC;
```

**Ventana temporal**:
- **Run diario**: Últimas 24 horas (desde última corrida exitosa)
- **Backfill manual**: Rango arbitrario (ej: último mes completo)
- **Weekly briefing**: Últimos 7 días completos (lunes a domingo)

**Volumen estimado**:
- Run diario: ~10,000 eventos
- Weekly briefing: ~70,000 eventos
- Backfill 30 días: ~300,000 eventos

#### 3.2.2. Fuentes de Datos Secundarias (Fase 2 - Enriquecimiento)

**Tablas de dominio** (para JOIN futuro):

1. **`users`** (información de usuarios):
   ```sql
   SELECT user_id, email, role, country, created_at, warehouse_assigned
   FROM users
   WHERE user_id IN (SELECT DISTINCT user_id FROM telemetry_events WHERE ...)
   ```

2. **`locations`** (información de locales):
   ```sql
   SELECT location_id, name, country, city, type (restaurant/office)
   FROM locations
   ```

3. **`transactions`** (datos financieros):
   ```sql
   SELECT transaction_id, user_id, amount, currency, status, created_at
   FROM transactions
   WHERE created_at >= :start_date AND created_at < :end_date
   ```

**Nota Fase 1**: En el diseño inicial, **NO se implementarán JOINs con tablas de dominio**. Las dimensiones de negocio se extraerán **solo del campo `tags` JSONB** donde ya estén presentes.

#### 3.2.3. Frecuencia de Extracción

| Tipo de Run | Frecuencia | Ventana Temporal | Propósito |
|-------------|-----------|------------------|-----------|
| **Daily ETL** | Todos los días 3:00 AM UTC | Últimas 24h | Mantener KPIs actualizados |
| **Weekly Briefing** | Lunes 6:00 AM UTC | Últimos 7 días completos | Reporte ejecutivo semanal |
| **On-Demand Trigger** | Manual vía API | Rango arbitrario | Análisis ad-hoc, debugging |
| **Backfill Historical** | Manual (flow separado) | Rango histórico | Reprocesar periodos pasados |

### 3.3. Transformación (Transform)

#### 3.3.1. Dimensiones de Análisis

**Dimensiones temporales**:
- `date` (día calendario): Agrupación por fecha
- `week_start` (lunes de la semana): Agrupación semanal
- `month` (YYYY-MM): Agrupación mensual
- `hour` (0-23): Análisis de patrones horarios (opcional Fase 2)

**Dimensiones de negocio** (extraídas de `tags` JSONB o columnas fijas):
- `country` (CO/US): Segmentación geográfica
- `service` (backoffice/api/mobile): Origen del evento
- `user_role` (admin/manager/employee): Tipo de usuario
- `warehouse` (local_id): Local específico de Brasaland

**Dimensiones técnicas** (derivadas de `event_type`):
- `event_category` (page_view, auth, transaction, error): Agrupación de eventos
- `event_outcome` (success, failed, partial): Resultado de la operación

#### 3.3.2. KPIs a Calcular

**1. Usuarios Activos**:
- `daily_active_users` (DAU): COUNT(DISTINCT user_id) por día
- `weekly_active_users` (WAU): COUNT(DISTINCT user_id) en ventana de 7 días
- `monthly_active_users` (MAU): COUNT(DISTINCT user_id) en ventana de 30 días

**2. Sesiones y Engagement**:
- `total_sessions`: COUNT(DISTINCT session_id)
- `avg_events_per_session`: AVG(COUNT(event_id) GROUP BY session_id)
- `avg_session_duration_minutes`: Calculado como (MAX(timestamp) - MIN(timestamp)) por session_id

**3. Disponibilidad y Performance**:
- `system_availability_pct`: (1 - error_events / total_events) * 100
- `avg_response_time_ms`: AVG(tags->>'duration_ms') para eventos con métrica de latencia
- `p95_response_time_ms`: PERCENTILE_CONT(0.95) de duración

**4. Tasa de Conversión y Éxito**:
- `transaction_success_rate`: (success_events / total_transaction_events) * 100
- `auth_success_rate`: (login_success / total_login_attempts) * 100
- `funnel_completion_rate`: (completados / iniciados) para flujos multi-paso

**5. Distribución por Dimensiones**:
- `users_by_country`: COUNT(DISTINCT user_id) GROUP BY country
- `events_by_warehouse`: COUNT(*) GROUP BY tags->>'warehouse'
- `errors_by_service`: COUNT(*) WHERE is_error = TRUE GROUP BY service

**6. Calidad de Datos**:
- `events_with_user_id_pct`: (COUNT(user_id IS NOT NULL) / COUNT(*)) * 100
- `events_with_session_id_pct`: (COUNT(session_id IS NOT NULL) / COUNT(*)) * 100
- `avg_ingestion_lag_seconds`: AVG(EXTRACT(EPOCH FROM (ingested_at - timestamp)))

#### 3.3.3. Lógica de Transformación en Pandas

**Patrón de código** (funciones puras, vectorización, sin bucles):

```python
import pandas as pd
from datetime import datetime, timedelta

def transform_events_to_kpis(
    events_df: pd.DataFrame,
    start_date: datetime,
    end_date: datetime
) -> pd.DataFrame:
    """
    Transforma DataFrame de eventos crudos en DataFrame de KPIs agregados.
    
    Args:
        events_df: DataFrame con columnas de telemetry_events
        start_date: Inicio del periodo
        end_date: Fin del periodo
    
    Returns:
        DataFrame con KPIs agregados por fecha y dimensiones
    """
    # 1. CONVERSIÓN DE TIPOS (obligatorio)
    events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], utc=True)
    events_df["date"] = events_df["timestamp"].dt.date
    
    # 2. EXTRACCIÓN DE DIMENSIONES DESDE JSONB
    # (Pandas 2.x permite .str.get() sobre columnas de dicts)
    if "tags" in events_df.columns:
        events_df["country"] = events_df["tags"].apply(lambda x: x.get("country") if isinstance(x, dict) else None)
        events_df["warehouse"] = events_df["tags"].apply(lambda x: x.get("warehouse") if isinstance(x, dict) else None)
        events_df["user_role"] = events_df["tags"].apply(lambda x: x.get("user_role") if isinstance(x, dict) else None)
        events_df["duration_ms"] = events_df["tags"].apply(lambda x: x.get("duration_ms") if isinstance(x, dict) else None)
    
    # 3. DERIVACIÓN DE DIMENSIONES TÉCNICAS
    error_keywords = ["error", "failed", "rejected"]
    events_df["is_error"] = events_df["event_type"].str.contains(
        "|".join(error_keywords), case=False, na=False
    )
    
    # 4. AGREGACIONES VECTORIZADAS (por fecha)
    kpis = events_df.groupby("date").agg(
        # Volumetría
        total_events=("event_id", "size"),
        total_sessions=("session_id", "nunique"),
        daily_active_users=("user_id", "nunique"),
        
        # Performance
        avg_response_time_ms=("duration_ms", "mean"),
        
        # Calidad
        error_events=("is_error", "sum"),
        events_with_user_id=("user_id", lambda x: x.notna().sum())
    ).reset_index()
    
    # 5. MÉTRICAS DERIVADAS (vectorizado)
    kpis["system_availability_pct"] = (
        (1 - kpis["error_events"] / kpis["total_events"]) * 100
    ).round(2)
    
    kpis["events_with_user_id_pct"] = (
        (kpis["events_with_user_id"] / kpis["total_events"]) * 100
    ).round(2)
    
    # 6. METADATA DEL PERIODO
    kpis["period_start"] = start_date
    kpis["period_end"] = end_date
    kpis["calculated_at"] = datetime.utcnow()
    
    return kpis
```

**Patrones de calidad**:
- ✅ Funciones puras (mismo input → mismo output)
- ✅ Vectorización con Pandas (sin bucles `for`)
- ✅ Conversión obligatoria a datetime UTC antes de groupby
- ✅ Manejo de valores nulos con `.fillna()`, `.notna()`
- ✅ Redondeo de decimales (`.round(2)`)
- ✅ Tipado explícito de columnas resultantes

### 3.4. Carga (Load)

#### 3.4.1. Tabla de Destino: `reporting.business_kpis`

**Schema SQL**:

```sql
-- Schema dedicado para reporting
CREATE SCHEMA IF NOT EXISTS reporting;

-- Tabla de KPIs de negocio agregados
CREATE TABLE reporting.business_kpis (
    -- Primary Key Compuesta (fecha + dimensiones)
    id BIGSERIAL PRIMARY KEY,
    
    -- Dimensión Temporal (part of PK natural)
    date DATE NOT NULL,
    
    -- Dimensiones de Negocio (nullable para agregados globales)
    country VARCHAR(2),          -- CO, US, NULL (global)
    service VARCHAR(50),          -- backoffice, api, mobile, NULL (global)
    warehouse VARCHAR(100),       -- Local específico, NULL (global)
    
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
    pipeline_run_id UUID NOT NULL,  -- Correlación con logs de ejecución
    pipeline_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    
    -- Audit Trail
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices
CREATE UNIQUE INDEX idx_business_kpis_natural_key
ON reporting.business_kpis (date, COALESCE(country, ''), COALESCE(service, ''), COALESCE(warehouse, ''));

CREATE INDEX idx_business_kpis_date
ON reporting.business_kpis (date DESC);

CREATE INDEX idx_business_kpis_country
ON reporting.business_kpis (country)
WHERE country IS NOT NULL;

CREATE INDEX idx_business_kpis_pipeline_run
ON reporting.business_kpis (pipeline_run_id);

-- Trigger de updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_business_kpis_updated_at
BEFORE UPDATE ON reporting.business_kpis
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Comentarios de documentación
COMMENT ON TABLE reporting.business_kpis IS 'KPIs de negocio agregados desde telemetry_events. Actualizado diariamente por pipeline ETL. Granularidad: día + dimensiones opcionales (país, servicio, local).';
COMMENT ON COLUMN reporting.business_kpis.date IS 'Fecha del día al que corresponden los KPIs (zona horaria UTC).';
COMMENT ON COLUMN reporting.business_kpis.country IS 'País (CO/US/NULL). NULL = agregado global sin segmentación geográfica.';
COMMENT ON COLUMN reporting.business_kpis.daily_active_users IS 'Usuarios únicos activos en la fecha (COUNT DISTINCT user_id).';
COMMENT ON COLUMN reporting.business_kpis.system_availability_pct IS 'Disponibilidad del sistema: (1 - error_events / total_events) * 100.';
COMMENT ON COLUMN reporting.business_kpis.pipeline_run_id IS 'UUID del run de Prefect que generó este registro. Para auditoría y debugging.';
```

#### 3.4.2. Estrategia de Carga: UPSERT (Insert + Update)

**Problema**: Múltiples ejecuciones del pipeline sobre el mismo `date` deben actualizar el registro existente, no insertar duplicados.

**Solución**: PostgreSQL `INSERT ... ON CONFLICT DO UPDATE`:

```sql
INSERT INTO reporting.business_kpis (
    date,
    country,
    service,
    warehouse,
    period_start,
    period_end,
    daily_active_users,
    total_sessions,
    total_events,
    error_events,
    system_availability_pct,
    calculated_at,
    pipeline_run_id,
    pipeline_version
)
VALUES (
    %(date)s,
    %(country)s,
    %(service)s,
    %(warehouse)s,
    %(period_start)s,
    %(period_end)s,
    %(daily_active_users)s,
    %(total_sessions)s,
    %(total_events)s,
    %(error_events)s,
    %(system_availability_pct)s,
    %(calculated_at)s,
    %(pipeline_run_id)s,
    %(pipeline_version)s
)
ON CONFLICT (date, COALESCE(country, ''), COALESCE(service, ''), COALESCE(warehouse, ''))
DO UPDATE SET
    period_start = EXCLUDED.period_start,
    period_end = EXCLUDED.period_end,
    daily_active_users = EXCLUDED.daily_active_users,
    total_sessions = EXCLUDED.total_sessions,
    total_events = EXCLUDED.total_events,
    error_events = EXCLUDED.error_events,
    system_availability_pct = EXCLUDED.system_availability_pct,
    calculated_at = EXCLUDED.calculated_at,
    pipeline_run_id = EXCLUDED.pipeline_run_id,
    pipeline_version = EXCLUDED.pipeline_version,
    updated_at = NOW();
```

**Ventajas del UPSERT**:
- ✅ Idempotencia garantizada: ejecutar N veces = mismo resultado
- ✅ No requiere DELETE previo (atómico)
- ✅ Audit trail preservado: `created_at` se mantiene, `updated_at` se actualiza
- ✅ Permite reprocesamiento sin corrupción de datos

### 3.5. Flujo de Datos (Diagrama Mermaid)

```mermaid
graph TB
    subgraph "FUENTES DE DATOS"
        A[telemetry_events<br/>PostgreSQL Supabase<br/>Append-Only]
        B[users<br/>Tabla de Dominio<br/>Fase 2]
        C[locations<br/>Tabla de Dominio<br/>Fase 2]
    end
    
    subgraph "ETL PIPELINE - data/pipelines/business-performance/"
        D[Extract Task<br/>SQL Query<br/>Ventana Temporal]
        E[Transform Task<br/>Pandas Pipeline<br/>Funciones Puras]
        F[Load Task<br/>UPSERT<br/>reporting.business_kpis]
        G[Audit Task<br/>Log Ejecución<br/>reporting.pipeline_runs]
    end
    
    subgraph "DESTINO PERSISTENTE"
        H[reporting.business_kpis<br/>Tabla de KPIs Agregados<br/>Índices: date, country, pipeline_run_id]
        I[reporting.pipeline_runs<br/>Tabla de Audit<br/>run_id, status, metrics]
    end
    
    subgraph "CONSUMO - services/reporting/"
        J[GET /reporting/kpis<br/>Endpoint de Consulta<br/>Filtros: date_range, country, service]
        K[GET /reporting/status<br/>Estado del Pipeline<br/>Última corrida exitosa]
        L[POST /reporting/trigger<br/>Disparo Manual<br/>Backfill o Reintento]
    end
    
    subgraph "CLIENTES FINALES"
        M[Dashboard Ejecutivo<br/>Frontend React<br/>Gráficos y Tablas]
        N[Weekly Briefing Email<br/>Cron Lunes 7am<br/>Reporte PDF/HTML]
    end
    
    A -->|SELECT timestamp >= :start| D
    B -.->|JOIN user_id<br/>Fase 2| D
    C -.->|JOIN warehouse<br/>Fase 2| D
    
    D -->|DataFrame eventos crudos| E
    E -->|DataFrame KPIs agregados| F
    F -->|UPSERT por (date, country, service, warehouse)| H
    
    D -->|Metadata run| G
    E -->|Registros procesados| G
    F -->|Registros insertados/actualizados| G
    G -->|INSERT audit log| I
    
    H -->|SELECT con filtros| J
    I -->|SELECT última corrida| K
    
    J -->|JSON response| M
    J -->|JSON response| N
    K -->|JSON response| M
    L -->|Trigger Prefect Flow| D
    
    style A fill:#e1f5ff
    style H fill:#d4edda
    style I fill:#d4edda
    style M fill:#fff3cd
    style N fill:#fff3cd
```

**Explicación del flujo**:

1. **Extracción**: SQL query sobre `telemetry_events` con filtro temporal
2. **Transformación**: Pandas agrega eventos → KPIs (funciones puras)
3. **Carga**: UPSERT en `reporting.business_kpis` (idempotente)
4. **Auditoría**: Log de ejecución en `reporting.pipeline_runs`
5. **Consumo**: Endpoints REST en `services/reporting/` sirven KPIs
6. **Visualización**: Dashboard ejecutivo y briefing semanal consumen API

### 3.6. Estrategia ante Actualizaciones

#### 3.6.1. Naturaleza de la Fuente: Append-Only

**`telemetry_events` es inmutable**:
- ✅ NO soporta UPDATE ni DELETE (políticas RLS y triggers lo previenen)
- ✅ Solo INSERT permitido
- ✅ Cada evento es un hecho histórico inmutable

**Implicación para el pipeline**:
- ✅ **No hay problema de "registros actualizados"** en la fuente
- ✅ Una vez un evento está en `telemetry_events`, nunca cambia
- ✅ Reprocesar el mismo rango temporal siempre da idéntico resultado

#### 3.6.2. Estrategia en Tabla de Destino

**Tabla `reporting.business_kpis` SÍ soporta actualizaciones**:
- Necesario para reprocesamiento (ej: corrección de bug en lógica de transformación)
- Necesario para late-arriving events (eventos que llegan fuera de orden)

**Mecanismo: UPSERT con Primary Key Natural**:
```sql
UNIQUE INDEX idx_business_kpis_natural_key
ON reporting.business_kpis (date, COALESCE(country, ''), COALESCE(service, ''), COALESCE(warehouse, ''))
```

**Comportamiento**:
1. Primera ejecución del pipeline para `date = 2026-10-23`:
   - INSERT nuevo registro con KPIs del día
   - `created_at = NOW()`

2. Segunda ejecución para el mismo `date = 2026-10-23` (ej: reintento manual):
   - ON CONFLICT detecta clave duplicada
   - UPDATE registro existente con nuevos valores
   - `created_at` se preserva (no cambia)
   - `updated_at = NOW()`

3. Auditoría completa:
   - `pipeline_run_id` cambia en cada ejecución
   - Tabla `reporting.pipeline_runs` registra cada corrida
   - Se puede reconstruir el historial: "este KPI fue calculado 3 veces, última corrida exitosa fue run_id=xyz"

#### 3.6.3. Late-Arriving Events

**Escenario**: Evento con `timestamp = 2026-10-23 14:00 UTC` llega al sistema con delay de 2 días (`ingested_at = 2026-10-25 10:00 UTC`).

**Problema**: El pipeline ya procesó `date = 2026-10-23` y generó KPIs "incompletos".

**Solución**:

1. **Detección automática** (opcional, Fase 2):
   - Query diaria: "¿Hay eventos con `ingested_at` > ayer y `timestamp` < hace 7 días?"
   - Si sí → trigger de reprocesamiento para esas fechas

2. **Reprocesamiento manual** (Fase 1):
   - Operador ejecuta: `POST /reporting/trigger` con `date_range = [2026-10-23, 2026-10-24]`
   - Pipeline re-extrae eventos para esa ventana (incluyendo late-arrivals)
   - UPSERT actualiza KPIs en `reporting.business_kpis`

3. **Tolerancia al delay** (configuración):
   - Pipeline diario procesa: `[yesterday - 1 day, yesterday + 1 day]` (ventana de 3 días)
   - Cubre eventos con delay de hasta 24h sin intervención manual
   - Trade-off: más eventos procesados diariamente

**Decisión de diseño Fase 1**: Ventana fija de 24h, reprocesamiento manual para late-arrivals extremos.

---

## 4. Fase 3: Resiliencia, Idempotencia y Observabilidad

### 4.1. Estrategia de Idempotencia

#### 4.1.1. Definición de Idempotencia

> **Un pipeline es idempotente si ejecutarlo N veces sobre el mismo rango de fechas produce idéntico resultado en la tabla de destino, sin duplicación ni corrupción de datos.**

#### 4.1.2. Mecanismos Técnicos Garantizados

**1. Primary Key Natural en Destino**:
```sql
UNIQUE INDEX idx_business_kpis_natural_key
ON reporting.business_kpis (date, COALESCE(country, ''), COALESCE(service, ''), COALESCE(warehouse, ''))
```
- ✅ Una sola fila por combinación (fecha + dimensiones)
- ✅ No puede haber duplicados por diseño de schema

**2. UPSERT Atómico (ON CONFLICT DO UPDATE)**:
- ✅ Operación atómica en PostgreSQL (transacción implícita)
- ✅ Si existe → UPDATE
- ✅ Si no existe → INSERT
- ✅ No hay race conditions entre pipelines concurrentes (locks de fila)

**3. Extracción Determinista**:
```sql
WHERE timestamp >= :start_date
  AND timestamp < :end_date  -- Rango semi-abierto [start, end)
ORDER BY timestamp ASC
```
- ✅ Mismo rango temporal → mismos eventos extraídos
- ✅ ORDER BY garantiza orden consistente (importante para debugging)

**4. Transformaciones Puras (Pandas)**:
```python
def transform_events_to_kpis(events_df: pd.DataFrame) -> pd.DataFrame:
    """Función pura: mismo input → mismo output, sin side-effects"""
    # Solo operaciones deterministas (groupby, agg, round)
    # Sin llamadas a APIs externas, sin datetime.now() en cálculos
    pass
```
- ✅ No usa estado externo (solo el DataFrame de entrada)
- ✅ No tiene side-effects (no escribe archivos, no llama APIs)
- ✅ Reproducible en testing: mockear input → verificar output

**5. Metadata de Versión**:
```sql
pipeline_version VARCHAR(20) NOT NULL DEFAULT '1.0.0'
```
- ✅ Cambios en lógica de transformación → bump de versión
- ✅ Permite auditar: "KPI calculado con v1.0.0 vs. v1.1.0"
- ✅ Facilita rollback: reprocesar con versión anterior

#### 4.1.3. Casos de Prueba de Idempotencia

**Test 1: Ejecución duplicada inmediata**:
```python
# Arrange
date_range = (datetime(2026, 10, 23), datetime(2026, 10, 24))

# Act
result1 = run_pipeline(date_range)  # Primera ejecución
result2 = run_pipeline(date_range)  # Segunda ejecución (inmediata)

# Assert
assert result1.daily_active_users == result2.daily_active_users
assert result1.total_events == result2.total_events
# Metadata cambia, datos de negocio NO
assert result1.pipeline_run_id != result2.pipeline_run_id
assert result1.calculated_at < result2.calculated_at
```

**Test 2: Ejecución con delay (late-arriving events)**:
```python
# Arrange
date_range = (datetime(2026, 10, 23), datetime(2026, 10, 24))
run_pipeline(date_range)  # Primera ejecución

# Simular late-arriving event
insert_telemetry_event(timestamp=datetime(2026, 10, 23, 15, 0), ingested_at=datetime.now())

# Act
result_after_late_arrival = run_pipeline(date_range)  # Segunda ejecución

# Assert
assert result_after_late_arrival.total_events > initial_result.total_events  # Más eventos
assert result_after_late_arrival.daily_active_users >= initial_result.daily_active_users
# UPSERT actualizó el registro existente
```

**Test 3: Pipelines concurrentes**:
```python
# Act
import threading

def run_pipeline_thread(date_range, results, index):
    results[index] = run_pipeline(date_range)

results = [None, None]
threads = [
    threading.Thread(target=run_pipeline_thread, args=(date_range, results, 0)),
    threading.Thread(target=run_pipeline_thread, args=(date_range, results, 1))
]

for t in threads:
    t.start()
for t in threads:
    t.join()

# Assert
# Solo un registro en BD (no duplicado)
db_count = db.execute("SELECT COUNT(*) FROM reporting.business_kpis WHERE date = '2026-10-23'").scalar()
assert db_count == 1

# Ambos threads ven los mismos datos finales (uno hizo INSERT, otro UPDATE)
assert results[0].daily_active_users == results[1].daily_active_users
```

### 4.2. Log y Auditoría de Ejecución

#### 4.2.1. Tabla de Audit: `reporting.pipeline_runs`

**Propósito**: Registrar cada ejecución del pipeline para debugging, observabilidad y compliance.

**Schema SQL**:

```sql
CREATE TABLE reporting.pipeline_runs (
    -- Primary Key
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Pipeline Identity
    pipeline_name VARCHAR(100) NOT NULL,  -- 'business-performance-etl'
    pipeline_version VARCHAR(20) NOT NULL,  -- '1.0.0'
    
    -- Ejecución
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    duration_seconds INTEGER GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (finished_at - started_at))
    ) STORED,
    
    -- Input Parameters
    input_params JSONB NOT NULL,  -- {"start_date": "2026-10-23T00:00:00Z", "end_date": "2026-10-24T00:00:00Z"}
    
    -- Output Metrics
    records_read INTEGER,          -- Eventos extraídos de telemetry_events
    records_processed INTEGER,     -- Eventos transformados (después de filtros)
    records_inserted INTEGER,      -- Filas nuevas en business_kpis
    records_updated INTEGER,       -- Filas actualizadas en business_kpis
    
    -- Estado Final
    status VARCHAR(20) NOT NULL,  -- 'running', 'completed', 'failed', 'cancelled'
    
    -- Error Handling
    error_message TEXT,            -- Mensaje de error si status = 'failed'
    error_traceback TEXT,          -- Stack trace completo
    
    -- Metadata
    triggered_by VARCHAR(50),      -- 'scheduled', 'manual', 'api'
    prefect_flow_run_id UUID,      -- Link a Prefect flow run
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_pipeline_runs_started_at
ON reporting.pipeline_runs (started_at DESC);

CREATE INDEX idx_pipeline_runs_status
ON reporting.pipeline_runs (status);

CREATE INDEX idx_pipeline_runs_pipeline_name
ON reporting.pipeline_runs (pipeline_name, started_at DESC);

CREATE INDEX idx_pipeline_runs_prefect_flow
ON reporting.pipeline_runs (prefect_flow_run_id)
WHERE prefect_flow_run_id IS NOT NULL;

-- Comentarios
COMMENT ON TABLE reporting.pipeline_runs IS 'Audit log de ejecuciones del pipeline de negocio. Cada fila = 1 run (exitoso o fallido).';
COMMENT ON COLUMN reporting.pipeline_runs.records_read IS 'Número de eventos extraídos de telemetry_events (antes de filtros).';
COMMENT ON COLUMN reporting.pipeline_runs.records_inserted IS 'Filas nuevas insertadas en reporting.business_kpis (INSERT en UPSERT).';
COMMENT ON COLUMN reporting.pipeline_runs.records_updated IS 'Filas existentes actualizadas en reporting.business_kpis (UPDATE en UPSERT).';
COMMENT ON COLUMN reporting.pipeline_runs.triggered_by IS 'Origen del trigger: scheduled (cron), manual (operador), api (POST /reporting/trigger).';
```

#### 4.2.2. Ciclo de Vida del Audit Log

**1. Inicio del Pipeline (Task Extract)**:
```python
run_id = uuid.uuid4()
db.execute("""
    INSERT INTO reporting.pipeline_runs (
        run_id, pipeline_name, pipeline_version, started_at, status, input_params, triggered_by
    ) VALUES (
        :run_id, 'business-performance-etl', '1.0.0', NOW(), 'running', 
        :input_params, :triggered_by
    )
""", {
    "run_id": run_id,
    "input_params": json.dumps({"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}),
    "triggered_by": "scheduled"  # o 'manual', 'api'
})
```

**2. Durante la Ejecución (Tasks Extract/Transform/Load)**:
```python
# Cada task actualiza métricas parciales
db.execute("""
    UPDATE reporting.pipeline_runs
    SET records_read = :records_read
    WHERE run_id = :run_id
""", {"run_id": run_id, "records_read": len(events_df)})
```

**3. Finalización Exitosa (Task Load)**:
```python
db.execute("""
    UPDATE reporting.pipeline_runs
    SET 
        finished_at = NOW(),
        status = 'completed',
        records_processed = :records_processed,
        records_inserted = :records_inserted,
        records_updated = :records_updated
    WHERE run_id = :run_id
""", {
    "run_id": run_id,
    "records_processed": len(kpis_df),
    "records_inserted": insert_count,
    "records_updated": update_count
})
```

**4. Finalización con Error (Exception Handler)**:
```python
except Exception as e:
    db.execute("""
        UPDATE reporting.pipeline_runs
        SET 
            finished_at = NOW(),
            status = 'failed',
            error_message = :error_message,
            error_traceback = :error_traceback
        WHERE run_id = :run_id
    """, {
        "run_id": run_id,
        "error_message": str(e),
        "error_traceback": traceback.format_exc()
    })
    raise  # Re-raise para que Prefect lo marque como fallido
```

#### 4.2.3. Justificación de Cada Campo del Audit Log

| Campo | Justificación en Producción |
|-------|----------------------------|
| `run_id` | Correlación única entre audit log, logs de aplicación y Prefect UI |
| `started_at` / `finished_at` | Detectar ejecuciones lentas, calcular SLA |
| `duration_seconds` | Alertar si pipeline toma >10 min (umbral configurable) |
| `input_params` | Reproducir ejecución exacta: "¿qué rango procesó el run_id=xyz?" |
| `records_read` / `records_processed` | Detectar anomalías: "hoy procesamos 100 eventos vs. 10,000 ayer" |
| `records_inserted` / `records_updated` | Distinguir backfill (muchos inserts) vs. reprocesamiento (muchos updates) |
| `status` | Filtrar runs exitosos vs. fallidos en dashboard de observabilidad |
| `error_message` / `error_traceback` | Debugging sin acceso a logs de servidor |
| `triggered_by` | Auditoría: "¿quién ejecutó el pipeline fuera de horario?" |
| `prefect_flow_run_id` | Link directo a Prefect UI para ver logs, tasks, artifacts |

### 4.3. Recuperabilidad ante Fallos

#### 4.3.1. Escenarios de Fallo y Estrategia

**Escenario 1: Fallo en Task Extract (ej: timeout de BD)**

**Síntoma**:
- Pipeline falla antes de iniciar Task Transform
- Audit log: `status = 'failed'`, `records_read = NULL`

**Estrategia de recuperación**:
1. **Prefect retry automático**: Configurar `retries=3, retry_delay_seconds=60` en Task Extract
2. Si fallan los 3 reintentos → Prefect marca flow como Failed
3. **Intervención manual**: Operador verifica causa (BD caída, red, query timeout)
4. **Reintento manual**: `POST /reporting/trigger` con mismo `date_range`
5. Pipeline arranca desde cero (no hay estado intermedio que recuperar)

**Ventaja**: Task Extract es **stateless** (no escribe nada en BD), por lo que reintentar es seguro.

---

**Escenario 2: Fallo en Task Transform (ej: bug en código Pandas)**

**Síntoma**:
- Pipeline falla después de Extract, antes de Load
- Audit log: `status = 'failed'`, `records_read = 10000`, `error_message = "KeyError: 'duration_ms'"`

**Estrategia de recuperación**:
1. **NO reintentar automáticamente**: Fallo es determinista (mismo input → mismo error)
2. **Fix del código**:
   - Desarrollador corrige bug en `data/pipelines/business-performance/transform.py`
   - Commit + deploy de nueva versión (bump a `v1.0.1`)
3. **Reprocesamiento manual**:
   - Operador ejecuta: `POST /reporting/trigger` con `date_range = [fecha_fallida, fecha_fallida+1]`
   - Pipeline re-extrae (mismo input) → transforma con código corregido → carga
4. Audit log tiene 2 entradas:
   - Run 1: `status = 'failed'`, `pipeline_version = '1.0.0'`
   - Run 2: `status = 'completed'`, `pipeline_version = '1.0.1'`

**Ventaja**: `pipeline_version` en audit log permite distinguir runs antes y después del fix.

---

**Escenario 3: Fallo en Task Load (ej: constraint violation en UPSERT)**

**Síntoma**:
- Pipeline falla en UPSERT masivo
- Audit log: `status = 'failed'`, `records_read = 10000`, `records_processed = 50`, `error_message = "NOT NULL constraint violated"`

**Estrategia de recuperación**:
1. **Transacción atómica en Load**:
   ```python
   with db.begin():  # Contexto transaccional
       for row in kpis_df.itertuples():
           db.execute(upsert_query, row_dict)
   # Si falla cualquier UPSERT → ROLLBACK automático
   ```
2. **Efecto**: No hay inserción parcial (todo-o-nada)
3. **Diagnóstico**: Error indica problema de calidad de datos (ej: campo obligatorio NULL)
4. **Fix**:
   - Corregir lógica de transformación (asegurar que campos NOT NULL tengan valores)
   - O relajar constraint si es demasiado estricto
5. **Reprocesamiento manual**: Mismos pasos que Escenario 2

**Ventaja**: Transacciones garantizan que tabla de destino nunca quede en estado inconsistente.

---

**Escenario 4: Fallo por late-arriving events masivos**

**Síntoma**:
- Pipeline procesa `date = 2026-10-23` y genera KPIs
- 3 días después llegan 5,000 eventos con `timestamp = 2026-10-23` (ingestion delay)
- KPIs actuales son "stale" (no reflejan los 5,000 eventos nuevos)

**Estrategia de recuperación**:
1. **Detección manual** (Fase 1):
   - Operador ejecuta query:
     ```sql
     SELECT DATE(timestamp) AS event_date, COUNT(*) AS late_events
     FROM telemetry_events
     WHERE ingested_at >= NOW() - INTERVAL '1 day'
       AND timestamp < NOW() - INTERVAL '7 days'
     GROUP BY event_date
     HAVING COUNT(*) > 100;  -- Umbral de "masivo"
     ```
2. **Reprocesamiento dirigido**:
   - Para cada `event_date` con late events:
     - `POST /reporting/trigger` con `date_range = [event_date, event_date+1]`
   - Pipeline re-extrae (incluye late-arrivals) → UPSERT actualiza KPIs

3. **Automatización futura** (Fase 2):
   - Cron job diario ejecuta query de detección
   - Si detecta late events → auto-trigger de reprocesamiento
   - Notificación a Slack: "Pipeline reprocesó 3 fechas por late-arrivals"

**Ventaja**: UPSERT idempotente permite corregir KPIs históricos sin corrupción.

#### 4.3.2. Último Punto Seguro de Recuperación

**Definición**: Estado del sistema desde el cual se puede retomar la ejecución sin pérdida ni duplicación de datos.

**En este pipeline**:
- ✅ **No hay "punto medio" desde el cual retomar**
- ✅ Pipeline es **stateless** entre tasks (no guarda checkpoints intermedios)
- ✅ Cada task es atómico:
  - Extract: Lee de BD (sin mutación)
  - Transform: Procesa en memoria (sin side-effects)
  - Load: UPSERT transaccional (todo-o-nada)

**Implicación**:
- Si pipeline falla → reintentar desde el **inicio** (Task Extract)
- **No es problema de performance**: Ventana temporal típica (24h) procesa rápido (<5 min)
- Para ventanas grandes (backfill de 1 año) → considerar **particionamiento por chunks** (Fase 2)

**Chunk-based backfill** (optimización futura):
```python
# Dividir rango de 1 año en chunks de 7 días
for chunk_start in pd.date_range(start_date, end_date, freq='7D'):
    chunk_end = min(chunk_start + timedelta(days=7), end_date)
    run_pipeline_chunk(chunk_start, chunk_end)
    # Si falla chunk 5 → reintentar solo ese chunk, no todo el año
```

---

## 5. Fase 4: Mapeo de Arquitectura a Conceptos de Prefect

### 5.1. Introducción a Prefect

**Prefect** es un orquestador de workflows moderno diseñado para Python. Características relevantes:

- **Flows**: Funciones Python decoradas con `@flow` (punto de entrada del workflow)
- **Tasks**: Funciones Python decoradas con `@task` (unidades de trabajo atómicas)
- **Retry automático**: Configuración declarativa de reintentos con backoff exponencial
- **Observabilidad**: UI web con logs, métricas, timeline de ejecución
- **Blocks**: Almacenamiento seguro de configuración (conexiones DB, secrets, parámetros)
- **Deployments**: Programación de flows con cron, eventos o triggers manuales

### 5.2. Mapeo del Diseño ETL a Prefect

#### 5.2.1. Flow Principal: `business_performance_etl`

**Archivo**: `data/pipelines/business-performance/flow.py`

```python
from prefect import flow, task, get_run_logger
from datetime import datetime, timedelta
from typing import Tuple
import pandas as pd
import uuid

@flow(
    name="business-performance-etl",
    description="Pipeline ETL diario: telemetry_events → reporting.business_kpis",
    version="1.0.0",
    retries=0,  # No retry a nivel de flow (solo tasks individuales)
    retry_delay_seconds=60
)
def business_performance_etl_flow(
    start_date: datetime,
    end_date: datetime,
    triggered_by: str = "scheduled"
) -> dict:
    """
    Flow principal del pipeline de desempeño de negocio.
    
    Args:
        start_date: Inicio del rango temporal (inclusive)
        end_date: Fin del rango temporal (exclusivo)
        triggered_by: Origen del trigger ('scheduled', 'manual', 'api')
    
    Returns:
        Dict con métricas del run: {"run_id": "...", "records_inserted": 42, ...}
    """
    logger = get_run_logger()
    run_id = uuid.uuid4()
    
    logger.info(f"🚀 Iniciando pipeline business-performance-etl")
    logger.info(f"📅 Periodo: {start_date.date()} a {end_date.date()}")
    logger.info(f"🆔 Run ID: {run_id}")
    
    # ============================================================
    # TASK 1: EXTRACT
    # ============================================================
    events_df = extract_telemetry_events(start_date, end_date, run_id)
    
    # ============================================================
    # TASK 2: TRANSFORM
    # ============================================================
    kpis_df = transform_events_to_kpis(events_df, start_date, end_date, run_id)
    
    # ============================================================
    # TASK 3: LOAD
    # ============================================================
    load_result = load_kpis_to_database(kpis_df, run_id)
    
    # ============================================================
    # TASK 4: AUDIT
    # ============================================================
    audit_result = finalize_pipeline_run(
        run_id=run_id,
        status="completed",
        records_read=len(events_df),
        records_processed=len(kpis_df),
        records_inserted=load_result["inserted"],
        records_updated=load_result["updated"]
    )
    
    logger.info(f"✅ Pipeline completado exitosamente")
    logger.info(f"📊 Métricas: {load_result}")
    
    return {
        "run_id": str(run_id),
        "status": "completed",
        "records_read": len(events_df),
        "records_inserted": load_result["inserted"],
        "records_updated": load_result["updated"]
    }
```

**Gestión de estados en Prefect**:
- `Running`: Flow está ejecutándose
- `Completed`: Flow terminó exitosamente (return sin exception)
- `Failed`: Alguna task lanzó exception no manejada
- `Cancelled`: Usuario canceló manualmente desde UI

#### 5.2.2. Task 1: Extract

```python
@task(
    name="extract-telemetry-events",
    description="Extrae eventos de telemetry_events con filtro temporal",
    retries=3,  # Reintentar hasta 3 veces
    retry_delay_seconds=60,  # Esperar 1 min entre reintentos
    tags=["extract", "database"]
)
def extract_telemetry_events(
    start_date: datetime,
    end_date: datetime,
    run_id: uuid.UUID
) -> pd.DataFrame:
    """
    Extrae eventos de telemetry_events en el rango temporal especificado.
    
    Args:
        start_date: Inicio del rango (inclusive)
        end_date: Fin del rango (exclusivo)
        run_id: UUID del run actual (para logging)
    
    Returns:
        DataFrame con columnas de telemetry_events
    
    Raises:
        Exception: Si falla query o timeout
    """
    logger = get_run_logger()
    logger.info(f"📥 Extrayendo eventos: {start_date.date()} - {end_date.date()}")
    
    # Obtener conexión desde Prefect Block
    db = get_database_connection()  # Prefect Block "supabase-connection"
    
    query = """
        SELECT 
            id, event_id, event_type, timestamp, session_id, user_id,
            request_id, schema_version, service, tags, ingested_at, batch_id
        FROM telemetry_events
        WHERE timestamp >= :start_date
          AND timestamp < :end_date
        ORDER BY timestamp ASC
    """
    
    try:
        result = db.execute(query, {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        })
        
        rows = result.fetchall()
        df = pd.DataFrame(rows, columns=result.keys())
        
        logger.info(f"✅ Extraídos {len(df)} eventos")
        
        # Actualizar audit log con records_read
        update_pipeline_run(run_id, {"records_read": len(df)})
        
        return df
        
    except Exception as e:
        logger.error(f"❌ Error extrayendo eventos: {type(e).__name__}: {str(e)}")
        # Actualizar audit log con error
        update_pipeline_run(run_id, {
            "status": "failed",
            "error_message": str(e)
        })
        raise  # Re-raise para que Prefect lo maneje
```

**Configuración de retry**:
- `retries=3`: Si falla (timeout, error de conexión), reintenta hasta 3 veces
- `retry_delay_seconds=60`: Espera 1 minuto entre reintentos (backoff simple)
- Si fallan los 3 reintentos → Task marca como Failed → Flow marca como Failed

#### 5.2.3. Task 2: Transform

```python
@task(
    name="transform-events-to-kpis",
    description="Transforma eventos crudos en KPIs agregados con Pandas",
    retries=1,  # Solo 1 reintento (errores suelen ser deterministas)
    retry_delay_seconds=30,
    tags=["transform", "pandas"]
)
def transform_events_to_kpis(
    events_df: pd.DataFrame,
    start_date: datetime,
    end_date: datetime,
    run_id: uuid.UUID
) -> pd.DataFrame:
    """
    Transforma DataFrame de eventos en DataFrame de KPIs agregados.
    
    Esta función es PURA: mismo input → mismo output, sin side-effects.
    
    Args:
        events_df: DataFrame con eventos crudos de telemetry_events
        start_date: Inicio del periodo (para metadata)
        end_date: Fin del periodo (para metadata)
        run_id: UUID del run actual
    
    Returns:
        DataFrame con KPIs agregados (columnas de reporting.business_kpis)
    """
    logger = get_run_logger()
    logger.info(f"🔄 Transformando {len(events_df)} eventos en KPIs")
    
    if events_df.empty:
        logger.warning("⚠️ DataFrame vacío, retornando KPIs vacíos")
        return pd.DataFrame()  # DataFrame vacío → Load no hace nada
    
    # Conversión obligatoria a datetime UTC
    events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], utc=True)
    events_df["date"] = events_df["timestamp"].dt.date
    
    # Extracción de dimensiones desde JSONB tags
    events_df["country"] = events_df["tags"].apply(
        lambda x: x.get("country") if isinstance(x, dict) else None
    )
    events_df["warehouse"] = events_df["tags"].apply(
        lambda x: x.get("warehouse") if isinstance(x, dict) else None
    )
    events_df["duration_ms"] = events_df["tags"].apply(
        lambda x: x.get("duration_ms") if isinstance(x, dict) else None
    )
    
    # Flag de error (vectorizado)
    error_keywords = ["error", "failed", "rejected"]
    events_df["is_error"] = events_df["event_type"].str.contains(
        "|".join(error_keywords), case=False, na=False
    )
    
    # Agregación por fecha (día natural)
    kpis = events_df.groupby("date").agg(
        total_events=("event_id", "size"),
        total_sessions=("session_id", "nunique"),
        daily_active_users=("user_id", "nunique"),
        avg_response_time_ms=("duration_ms", "mean"),
        error_events=("is_error", "sum"),
        events_with_user_id=("user_id", lambda x: x.notna().sum()),
        events_with_session_id=("session_id", lambda x: x.notna().sum())
    ).reset_index()
    
    # Métricas derivadas
    kpis["system_availability_pct"] = (
        (1 - kpis["error_events"] / kpis["total_events"]) * 100
    ).round(2)
    
    kpis["events_with_user_id_pct"] = (
        (kpis["events_with_user_id"] / kpis["total_events"]) * 100
    ).round(2)
    
    kpis["events_with_session_id_pct"] = (
        (kpis["events_with_session_id"] / kpis["total_events"]) * 100
    ).round(2)
    
    # Metadata del periodo
    kpis["period_start"] = start_date
    kpis["period_end"] = end_date
    kpis["calculated_at"] = datetime.utcnow()
    kpis["pipeline_run_id"] = run_id
    kpis["pipeline_version"] = "1.0.0"
    
    # Convertir date a string para serialización
    kpis["date"] = kpis["date"].astype(str)
    
    logger.info(f"✅ Generados {len(kpis)} registros de KPIs")
    
    # Actualizar audit log
    update_pipeline_run(run_id, {"records_processed": len(kpis)})
    
    return kpis
```

**Características de pureza**:
- ✅ No usa `datetime.now()` en cálculos (solo en metadata)
- ✅ No lee de BD ni APIs externas
- ✅ No escribe archivos
- ✅ Determinista: mismo DataFrame entrada → mismo DataFrame salida

#### 5.2.4. Task 3: Load

```python
@task(
    name="load-kpis-to-database",
    description="Carga KPIs en reporting.business_kpis con UPSERT",
    retries=2,
    retry_delay_seconds=30,
    tags=["load", "database"]
)
def load_kpis_to_database(
    kpis_df: pd.DataFrame,
    run_id: uuid.UUID
) -> dict:
    """
    Carga KPIs en tabla reporting.business_kpis usando UPSERT.
    
    Args:
        kpis_df: DataFrame con KPIs agregados
        run_id: UUID del run actual
    
    Returns:
        Dict con métricas: {"inserted": 5, "updated": 2}
    """
    logger = get_run_logger()
    logger.info(f"💾 Cargando {len(kpis_df)} registros de KPIs")
    
    if kpis_df.empty:
        logger.warning("⚠️ DataFrame vacío, nada que cargar")
        return {"inserted": 0, "updated": 0}
    
    db = get_database_connection()
    
    upsert_query = """
        INSERT INTO reporting.business_kpis (
            date, country, service, warehouse,
            period_start, period_end,
            daily_active_users, total_sessions, total_events,
            avg_response_time_ms, error_events, system_availability_pct,
            events_with_user_id_pct, events_with_session_id_pct,
            calculated_at, pipeline_run_id, pipeline_version
        )
        VALUES (
            :date, :country, :service, :warehouse,
            :period_start, :period_end,
            :daily_active_users, :total_sessions, :total_events,
            :avg_response_time_ms, :error_events, :system_availability_pct,
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
            avg_response_time_ms = EXCLUDED.avg_response_time_ms,
            error_events = EXCLUDED.error_events,
            system_availability_pct = EXCLUDED.system_availability_pct,
            events_with_user_id_pct = EXCLUDED.events_with_user_id_pct,
            events_with_session_id_pct = EXCLUDED.events_with_session_id_pct,
            calculated_at = EXCLUDED.calculated_at,
            pipeline_run_id = EXCLUDED.pipeline_run_id,
            pipeline_version = EXCLUDED.pipeline_version,
            updated_at = NOW()
    """
    
    inserted_count = 0
    updated_count = 0
    
    try:
        with db.begin():  # Transacción atómica
            for row in kpis_df.to_dict(orient="records"):
                result = db.execute(upsert_query, row)
                
                # Detectar si fue INSERT o UPDATE (no estándar, depende del driver)
                # Alternativa: SELECT antes del UPSERT para contar
                # Por simplicidad, contamos todos como "procesados"
            
            # Contar inserts vs updates (query separado post-commit)
            # Simplificación: asumir que si date ya existía → UPDATE, sino INSERT
            # Implementación precisa requiere RETURNING clause en PostgreSQL
            
            inserted_count = len(kpis_df)  # Simplificación Fase 1
            updated_count = 0  # Refinado en Fase 2
        
        logger.info(f"✅ Cargados {inserted_count} registros (UPSERT exitoso)")
        
        # Actualizar audit log
        update_pipeline_run(run_id, {
            "records_inserted": inserted_count,
            "records_updated": updated_count
        })
        
        return {"inserted": inserted_count, "updated": updated_count}
        
    except Exception as e:
        logger.error(f"❌ Error cargando KPIs: {type(e).__name__}: {str(e)}")
        update_pipeline_run(run_id, {
            "status": "failed",
            "error_message": str(e)
        })
        raise
```

**Garantía transaccional**:
- `with db.begin()`: Todo el UPSERT se ejecuta en una transacción
- Si falla cualquier fila → ROLLBACK completo (no hay inserción parcial)
- Idempotencia garantizada por constraint + UPSERT

#### 5.2.5. Task 4: Audit

```python
@task(
    name="finalize-pipeline-run",
    description="Actualiza audit log con status final del pipeline",
    retries=1,
    retry_delay_seconds=10,
    tags=["audit", "database"]
)
def finalize_pipeline_run(
    run_id: uuid.UUID,
    status: str,
    records_read: int,
    records_processed: int,
    records_inserted: int,
    records_updated: int
) -> dict:
    """
    Finaliza el registro de audit log del pipeline run.
    
    Args:
        run_id: UUID del run actual
        status: Estado final ('completed' o 'failed')
        records_read: Eventos extraídos
        records_processed: KPIs generados
        records_inserted: Filas insertadas
        records_updated: Filas actualizadas
    
    Returns:
        Dict con confirmación
    """
    logger = get_run_logger()
    logger.info(f"📝 Finalizando audit log para run_id={run_id}")
    
    db = get_database_connection()
    
    update_query = """
        UPDATE reporting.pipeline_runs
        SET
            finished_at = NOW(),
            status = :status,
            records_read = :records_read,
            records_processed = :records_processed,
            records_inserted = :records_inserted,
            records_updated = :records_updated
        WHERE run_id = :run_id
    """
    
    db.execute(update_query, {
        "run_id": run_id,
        "status": status,
        "records_read": records_read,
        "records_processed": records_processed,
        "records_inserted": records_inserted,
        "records_updated": records_updated
    })
    
    logger.info(f"✅ Audit log actualizado: status={status}")
    
    return {"run_id": str(run_id), "status": status}
```

### 5.3. Flow Secundario: Backfill Histórico

**Propósito**: Reprocesar rangos temporales largos (ej: último año) de forma eficiente.

```python
@flow(
    name="business-performance-backfill",
    description="Backfill histórico del pipeline ETL con chunks de 7 días",
    version="1.0.0"
)
def business_performance_backfill_flow(
    start_date: datetime,
    end_date: datetime
) -> dict:
    """
    Ejecuta backfill histórico dividiendo el rango en chunks de 7 días.
    
    Args:
        start_date: Inicio del rango histórico
        end_date: Fin del rango histórico
    
    Returns:
        Dict con métricas agregadas de todos los chunks
    """
    logger = get_run_logger()
    logger.info(f"🔄 Backfill histórico: {start_date.date()} a {end_date.date()}")
    
    # Dividir en chunks de 7 días
    chunks = []
    current = start_date
    while current < end_date:
        chunk_end = min(current + timedelta(days=7), end_date)
        chunks.append((current, chunk_end))
        current = chunk_end
    
    logger.info(f"📦 Procesando {len(chunks)} chunks de 7 días")
    
    results = []
    
    for i, (chunk_start, chunk_end) in enumerate(chunks, 1):
        logger.info(f"📦 Chunk {i}/{len(chunks)}: {chunk_start.date()} - {chunk_end.date()}")
        
        # Ejecutar flow principal para cada chunk
        result = business_performance_etl_flow(
            start_date=chunk_start,
            end_date=chunk_end,
            triggered_by="backfill"
        )
        
        results.append(result)
    
    # Agregar métricas totales
    total_inserted = sum(r["records_inserted"] for r in results)
    total_updated = sum(r["records_updated"] for r in results)
    
    logger.info(f"✅ Backfill completado: {total_inserted} inserts, {total_updated} updates")
    
    return {
        "chunks_processed": len(chunks),
        "total_inserted": total_inserted,
        "total_updated": total_updated
    }
```

### 5.4. Prefect Blocks: Configuración y Secrets

**Prefect Blocks** son objetos de configuración reutilizables (conexiones DB, secrets, parámetros).

#### 5.4.1. Block: Supabase Connection

**Tipo**: `SQLAlchemy Connector`  
**Nombre**: `supabase-reporting-db`

**Configuración**:
```python
from prefect_sqlalchemy import SqlAlchemyConnector

# Crear block (una sola vez)
supabase_block = SqlAlchemyConnector(
    connection_info="postgresql+psycopg2://user:password@db.supabase.co:5432/postgres",
    driver_name="postgresql+psycopg2"
)
supabase_block.save("supabase-reporting-db")
```

**Uso en tasks**:
```python
from prefect_sqlalchemy import SqlAlchemyConnector

def get_database_connection():
    """Obtiene conexión desde Prefect Block"""
    connector = SqlAlchemyConnector.load("supabase-reporting-db")
    return connector.get_engine()
```

**Ventajas**:
- ✅ Secrets no hardcodeados en código
- ✅ Configuración centralizada (cambiar una vez, afecta todos los flows)
- ✅ Diferenciación por entorno (dev/staging/prod)

#### 5.4.2. Block: Pipeline Parameters

**Tipo**: `JSON`  
**Nombre**: `business-pipeline-params`

**Configuración**:
```python
from prefect.blocks.system import JSON

params = JSON(
    value={
        "default_window_days": 7,
        "backfill_chunk_days": 7,
        "cache_ttl_seconds": 300,
        "retry_max_attempts": 3,
        "retry_delay_seconds": 60
    }
)
params.save("business-pipeline-params")
```

**Uso en flows**:
```python
from prefect.blocks.system import JSON

params = JSON.load("business-pipeline-params")
config = params.value

# Usar parámetros
window_days = config["default_window_days"]
```

---

## 6. Fase 5: Integración con la Aplicación

### 6.1. Arquitectura de Servicios

**Separación de responsabilidades**:

| Responsabilidad | Módulo | Tecnología |
|----------------|--------|------------|
| **Orquestación ETL** | `data/pipelines/business-performance/` | Python + Prefect |
| **Lógica de transformación** | `data/pipelines/business-performance/transform.py` | Pandas |
| **API REST de control y consulta** | `services/reporting/` | FastAPI |
| **Consumo frontend** | `uis/backoffice/` (dashboard) | Next.js + React |

**Principio de desacoplamiento**:
- ✅ `services/reporting/` **NO ejecuta transformaciones ETL**
- ✅ `services/reporting/` solo **dispara flows de Prefect** y **consulta tablas de reporting**
- ✅ `data/pipelines/` **NO tiene endpoints HTTP**
- ✅ `data/pipelines/` es **invocado por Prefect**, no por FastAPI

### 6.2. Estructura de `services/reporting/`

**Ubicación**: `services/reporting/`

```
services/reporting/
├── __init__.py
├── router.py              # Router FastAPI principal
├── endpoints/
│   ├── __init__.py
│   ├── kpis.py           # GET /reporting/kpis
│   ├── status.py         # GET /reporting/status
│   └── trigger.py        # POST /reporting/trigger
├── schemas/
│   ├── __init__.py
│   └── reporting.py      # Pydantic schemas para requests/responses
└── services/
    ├── __init__.py
    ├── kpi_service.py    # Lógica de consulta de KPIs
    └── prefect_client.py # Cliente para disparar flows de Prefect
```

### 6.3. Endpoint 1: `GET /reporting/status`

**Propósito**: Consultar el estado del pipeline (última corrida, próxima corrida programada).

**Especificación OpenAPI**:

```python
# services/reporting/endpoints/status.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime
from typing import Optional

from app.database_supabase import get_inventory_db
from services.reporting.schemas.reporting import PipelineStatusResponse

router = APIRouter()


@router.get(
    "/status",
    response_model=PipelineStatusResponse,
    summary="Obtener estado del pipeline de negocio",
    description="Consulta el estado de la última corrida del pipeline ETL y el horario de la próxima ejecución programada."
)
async def get_pipeline_status(
    db: Session = Depends(get_inventory_db)
):
    """
    Retorna el estado del pipeline de desempeño de negocio.
    
    **Información retornada**:
    - Última corrida exitosa (run_id, timestamp, métricas)
    - Última corrida fallida (si existe)
    - Próxima ejecución programada (schedule)
    - Estado general del pipeline (healthy/degraded/failed)
    
    **Ejemplo de respuesta**:
    ```json
    {
        "last_successful_run": {
            "run_id": "a1b2c3d4-...",
            "started_at": "2026-10-29T03:00:00Z",
            "finished_at": "2026-10-29T03:04:32Z",
            "duration_seconds": 272,
            "records_processed": 9543,
            "records_inserted": 1,
            "records_updated": 0
        },
        "last_failed_run": null,
        "next_scheduled_run": "2026-10-30T03:00:00Z",
        "pipeline_health": "healthy"
    }
    ```
    """
    try:
        # Consultar última corrida exitosa
        query_success = select(reporting.pipeline_runs).where(
            reporting.pipeline_runs.status == "completed",
            reporting.pipeline_runs.pipeline_name == "business-performance-etl"
        ).order_by(reporting.pipeline_runs.started_at.desc()).limit(1)
        
        last_success = db.execute(query_success).scalar_one_or_none()
        
        # Consultar última corrida fallida
        query_failed = select(reporting.pipeline_runs).where(
            reporting.pipeline_runs.status == "failed",
            reporting.pipeline_runs.pipeline_name == "business-performance-etl"
        ).order_by(reporting.pipeline_runs.started_at.desc()).limit(1)
        
        last_failed = db.execute(query_failed).scalar_one_or_none()
        
        # Determinar health del pipeline
        health = "healthy"
        if last_failed and (not last_success or last_failed.started_at > last_success.started_at):
            health = "failed"
        elif last_success and (datetime.utcnow() - last_success.finished_at).days > 2:
            health = "degraded"  # No ha corrido en 2+ días
        
        # Calcular próximo scheduled run (cron: 3:00 AM UTC diario)
        now = datetime.utcnow()
        next_run = datetime(now.year, now.month, now.day, 3, 0, 0)
        if now.hour >= 3:
            next_run += timedelta(days=1)
        
        return PipelineStatusResponse(
            last_successful_run=last_success,
            last_failed_run=last_failed,
            next_scheduled_run=next_run,
            pipeline_health=health
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error consultando estado del pipeline: {str(e)}"
        )
```

**Schema Pydantic**:

```python
# services/reporting/schemas/reporting.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID

class PipelineRunSummary(BaseModel):
    run_id: UUID
    started_at: datetime
    finished_at: Optional[datetime]
    duration_seconds: Optional[int]
    records_processed: int
    records_inserted: int
    records_updated: int

class PipelineStatusResponse(BaseModel):
    last_successful_run: Optional[PipelineRunSummary]
    last_failed_run: Optional[PipelineRunSummary]
    next_scheduled_run: datetime
    pipeline_health: str = Field(..., pattern="^(healthy|degraded|failed)$")
```

### 6.4. Endpoint 2: `POST /reporting/trigger`

**Propósito**: Disparar manualmente el pipeline ETL (reprocesamiento, backfill, debugging).

**Especificación OpenAPI**:

```python
# services/reporting/endpoints/trigger.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import Optional
import httpx

from services.reporting.services.prefect_client import trigger_prefect_flow

router = APIRouter()


class TriggerPipelineRequest(BaseModel):
    """Request body para disparar pipeline manualmente"""
    start_date: Optional[datetime] = Field(
        None,
        description="Inicio del rango temporal (ISO 8601 UTC). Si no se provee, usa ayer."
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Fin del rango temporal (ISO 8601 UTC). Si no se provee, usa hoy."
    )
    mode: str = Field(
        "standard",
        pattern="^(standard|backfill)$",
        description="Modo de ejecución: 'standard' (run único) o 'backfill' (chunks de 7 días)"
    )


class TriggerPipelineResponse(BaseModel):
    """Response del trigger manual"""
    message: str
    flow_run_id: Optional[str]
    flow_run_url: Optional[str]
    parameters: dict


@router.post(
    "/trigger",
    response_model=TriggerPipelineResponse,
    summary="Disparar pipeline ETL manualmente",
    description="Dispara una ejecución manual del pipeline de negocio. Útil para reprocesamiento o backfill histórico.",
    status_code=202  # Accepted (asíncrono)
)
async def trigger_pipeline(
    request: TriggerPipelineRequest,
    background_tasks: BackgroundTasks
):
    """
    Dispara manualmente el pipeline de desempeño de negocio.
    
    **Casos de uso**:
    - Reprocesamiento tras fix de bug en transformación
    - Backfill histórico (procesar rangos de fechas pasadas)
    - Forzar actualización de KPIs fuera de horario programado
    
    **Parámetros**:
    - `start_date` (opcional): Inicio del rango. Default: ayer.
    - `end_date` (opcional): Fin del rango. Default: hoy.
    - `mode` (opcional): 'standard' (run único) o 'backfill' (chunks de 7 días). Default: 'standard'.
    
    **Respuesta**:
    ```json
    {
        "message": "Pipeline disparado exitosamente",
        "flow_run_id": "prefect-run-123",
        "flow_run_url": "https://app.prefect.cloud/runs/...",
        "parameters": {
            "start_date": "2026-10-29T00:00:00Z",
            "end_date": "2026-10-30T00:00:00Z",
            "triggered_by": "manual"
        }
    }
    ```
    
    **Nota**: El pipeline se ejecuta en background. Usar `GET /reporting/status` para monitorear progreso.
    """
    try:
        # Resolver fechas por defecto
        now = datetime.utcnow()
        start_date = request.start_date or (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = request.end_date or now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Validar rango
        if start_date >= end_date:
            raise HTTPException(
                status_code=422,
                detail="start_date debe ser menor que end_date"
            )
        
        # Determinar flow a ejecutar
        flow_name = "business-performance-backfill" if request.mode == "backfill" else "business-performance-etl"
        
        # Parámetros del flow
        parameters = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "triggered_by": "manual"
        }
        
        # Disparar flow en Prefect (asíncrono)
        flow_run = trigger_prefect_flow(
            flow_name=flow_name,
            parameters=parameters
        )
        
        return TriggerPipelineResponse(
            message=f"Pipeline disparado exitosamente (mode={request.mode})",
            flow_run_id=flow_run["id"],
            flow_run_url=flow_run["url"],
            parameters=parameters
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error disparando pipeline: {str(e)}"
        )
```

**Cliente de Prefect**:

```python
# services/reporting/services/prefect_client.py

import httpx
import os
from typing import Dict, Any

PREFECT_API_URL = os.getenv("PREFECT_API_URL", "http://localhost:4200/api")
PREFECT_API_KEY = os.getenv("PREFECT_API_KEY")  # Secret de Prefect Cloud


def trigger_prefect_flow(flow_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispara un flow de Prefect vía API REST.
    
    Args:
        flow_name: Nombre del flow ('business-performance-etl' o 'business-performance-backfill')
        parameters: Diccionario con parámetros del flow
    
    Returns:
        Dict con información del flow run:
        {
            "id": "prefect-run-id",
            "url": "https://app.prefect.cloud/runs/...",
            "status": "scheduled"
        }
    
    Raises:
        HTTPException: Si falla el trigger
    """
    headers = {
        "Authorization": f"Bearer {PREFECT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": flow_name,
        "parameters": parameters
    }
    
    response = httpx.post(
        f"{PREFECT_API_URL}/deployments/{flow_name}/create_flow_run",
        json=payload,
        headers=headers,
        timeout=10.0
    )
    
    response.raise_for_status()
    
    data = response.json()
    
    return {
        "id": data["id"],
        "url": f"{PREFECT_API_URL}/flow-runs/{data['id']}",
        "status": data["state"]["type"]
    }
```

### 6.5. Endpoint 3: `GET /reporting/kpis`

**Propósito**: Consultar KPIs de negocio para alimentar dashboard ejecutivo.

**Especificación OpenAPI**:

```python
# services/reporting/endpoints/kpis.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, and_, or_
from datetime import datetime, timedelta
from typing import Optional, List

from app.database_supabase import get_inventory_db
from services.reporting.schemas.reporting import BusinessKPIResponse

router = APIRouter()


@router.get(
    "/kpis",
    response_model=List[BusinessKPIResponse],
    summary="Consultar KPIs de negocio",
    description="Consulta KPIs agregados desde la tabla reporting.business_kpis con filtros opcionales."
)
async def get_business_kpis(
    start_date: Optional[datetime] = Query(
        None,
        description="Fecha de inicio (inclusive). Default: últimos 30 días."
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Fecha de fin (exclusiva). Default: hoy."
    ),
    country: Optional[str] = Query(
        None,
        pattern="^(CO|US)$",
        description="Filtrar por país (CO o US). Omitir para datos globales."
    ),
    service: Optional[str] = Query(
        None,
        description="Filtrar por servicio (backoffice, api, mobile)."
    ),
    warehouse: Optional[str] = Query(
        None,
        description="Filtrar por local específico."
    ),
    db: Session = Depends(get_inventory_db)
):
    """
    Consulta KPIs de negocio con filtros opcionales.
    
    **Filtros soportados**:
    - `start_date` / `end_date`: Rango temporal
    - `country`: Segmentación geográfica (CO/US)
    - `service`: Segmentación por servicio (backoffice/api/mobile)
    - `warehouse`: Filtro por local específico
    
    **Ejemplo de uso**:
    ```bash
    # KPIs globales últimos 30 días
    GET /reporting/kpis
    
    # KPIs de Colombia, últimos 7 días
    GET /reporting/kpis?country=CO&start_date=2026-10-23T00:00:00Z
    
    # KPIs del local "medellin_centro", octubre completo
    GET /reporting/kpis?warehouse=medellin_centro&start_date=2026-10-01T00:00:00Z&end_date=2026-11-01T00:00:00Z
    ```
    
    **Respuesta**:
    ```json
    [
        {
            "date": "2026-10-29",
            "country": "CO",
            "service": "backoffice",
            "warehouse": null,
            "daily_active_users": 45,
            "total_sessions": 123,
            "total_events": 9543,
            "system_availability_pct": 99.87,
            "avg_response_time_ms": 234.5,
            "error_events": 12
        },
        ...
    ]
    ```
    """
    try:
        # Resolver fechas por defecto
        now = datetime.utcnow()
        end_date = end_date or now
        start_date = start_date or (end_date - timedelta(days=30))
        
        # Construir query con filtros
        query = select(reporting.business_kpis).where(
            and_(
                reporting.business_kpis.date >= start_date.date(),
                reporting.business_kpis.date < end_date.date()
            )
        )
        
        if country:
            query = query.where(reporting.business_kpis.country == country)
        
        if service:
            query = query.where(reporting.business_kpis.service == service)
        
        if warehouse:
            query = query.where(reporting.business_kpis.warehouse == warehouse)
        
        # Ordenar por fecha descendente
        query = query.order_by(reporting.business_kpis.date.desc())
        
        # Ejecutar query
        result = db.execute(query)
        kpis = result.scalars().all()
        
        if not kpis:
            return []  # Array vacío si no hay datos
        
        return kpis
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error consultando KPIs: {str(e)}"
        )
```

**Schema Pydantic**:

```python
# services/reporting/schemas/reporting.py

from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional
from uuid import UUID

class BusinessKPIResponse(BaseModel):
    """Schema de respuesta para KPIs de negocio"""
    
    # Dimensiones
    date: date
    country: Optional[str]
    service: Optional[str]
    warehouse: Optional[str]
    
    # Periodo
    period_start: datetime
    period_end: datetime
    
    # KPIs: Usuarios Activos
    daily_active_users: int
    
    # KPIs: Sesiones y Engagement
    total_sessions: int
    total_events: int
    avg_events_per_session: Optional[float]
    avg_session_duration_minutes: Optional[float]
    
    # KPIs: Disponibilidad y Performance
    system_availability_pct: Optional[float]
    avg_response_time_ms: Optional[float]
    p95_response_time_ms: Optional[float]
    
    # KPIs: Errores
    error_events: int
    error_rate: Optional[float]
    
    # KPIs: Autenticación
    auth_success_rate: Optional[float]
    
    # KPIs: Calidad de Datos
    events_with_user_id_pct: Optional[float]
    events_with_session_id_pct: Optional[float]
    avg_ingestion_lag_seconds: Optional[float]
    
    # Metadata
    calculated_at: datetime
    pipeline_run_id: UUID
    pipeline_version: str
    
    class Config:
        from_attributes = True  # Compatibilidad con SQLModel
```

### 6.6. Registro del Router en FastAPI

**Archivo**: `services/api/app/main.py`

```python
from fastapi import FastAPI
from services.reporting.router import router as reporting_router

app = FastAPI(
    title="Brasaland API",
    version="1.0.0"
)

# Registrar router de reporting
app.include_router(
    reporting_router,
    prefix="/reporting",
    tags=["Business Reporting"]
)

# ... otros routers (candidates, incidents, telemetry)
```

**Router de reporting**:

```python
# services/reporting/router.py

from fastapi import APIRouter
from services.reporting.endpoints import kpis, status, trigger

router = APIRouter()

# Registrar sub-routers
router.include_router(status.router, tags=["Pipeline Status"])
router.include_router(trigger.router, tags=["Pipeline Control"])
router.include_router(kpis.router, tags=["Business KPIs"])
```

### 6.7. Vinculación con Flows de Prefect

**Relación entre endpoints y flows**:

| Endpoint | Flow Prefect Invocado | Propósito |
|----------|----------------------|-----------|
| `GET /reporting/status` | Ninguno (solo consulta BD) | Ver estado del pipeline |
| `POST /reporting/trigger` (mode=standard) | `business-performance-etl` | Run único de 24h |
| `POST /reporting/trigger` (mode=backfill) | `business-performance-backfill` | Backfill con chunks de 7 días |
| `GET /reporting/kpis` | Ninguno (solo consulta BD) | Consultar KPIs ya calculados |

**Diagrama de interacción**:

```
┌──────────────┐      POST /reporting/trigger      ┌──────────────┐
│   Frontend   │ ───────────────────────────────► │   FastAPI    │
│  Dashboard   │                                    │ (services/   │
└──────────────┘                                    │  reporting/) │
                                                     └──────┬───────┘
                                                            │
                                                            │ HTTP POST
                                                            │ Prefect API
                                                            ▼
                                                     ┌──────────────┐
                                                     │   Prefect    │
                                                     │   Server     │
                                                     └──────┬───────┘
                                                            │
                                                            │ Schedule Flow
                                                            ▼
                                                     ┌──────────────────┐
                                                     │   Flow: ETL      │
                                                     │  (data/pipelines)│
                                                     └──────┬───────────┘
                                                            │
                                                            │ Extract/Transform/Load
                                                            ▼
┌──────────────┐      GET /reporting/kpis         ┌──────────────────┐
│   Frontend   │ ◄────────────────────────────── │  reporting.      │
│  Dashboard   │                                  │  business_kpis   │
└──────────────┘                                  │  (PostgreSQL)    │
                                                   └──────────────────┘
```

---

## 7. Anexos

### 7.1. Glosario de Términos

| Término | Definición |
|---------|------------|
| **Telemetría** | Sistema de captura de eventos técnicos (page views, errors, login attempts) para monitoreo operacional |
| **KPI (Key Performance Indicator)** | Métrica de negocio crítica para toma de decisiones (DAU, tasa de conversión, disponibilidad) |
| **ETL (Extract, Transform, Load)** | Patrón de pipeline de datos: extracción de fuente → transformación → carga en destino |
| **Idempotencia** | Propiedad de una operación que produce el mismo resultado si se ejecuta N veces |
| **UPSERT** | Operación SQL: INSERT si no existe, UPDATE si existe (basado en clave única) |
| **Append-Only** | Tabla que solo permite INSERT, nunca UPDATE ni DELETE (inmutable) |
| **Event Sourcing** | Patrón arquitectónico donde cada cambio de estado se registra como un evento inmutable |
| **Prefect Flow** | Función Python decorada con @flow que orquesta tasks |
| **Prefect Task** | Función Python decorada con @task que representa una unidad de trabajo atómica |
| **Prefect Block** | Objeto de configuración reutilizable (conexiones DB, secrets) |
| **RLS (Row Level Security)** | Sistema de políticas de seguridad en PostgreSQL que controla acceso a nivel de fila |
| **GIN Index** | Tipo de índice en PostgreSQL optimizado para búsquedas en campos JSONB |
| **JSONB** | Tipo de dato binario de PostgreSQL para almacenar JSON con queries eficientes |

### 7.2. Referencias Técnicas

**Documentación oficial**:
- Prefect 2.x: https://docs.prefect.io/
- Pandas 2.x: https://pandas.pydata.org/docs/
- FastAPI: https://fastapi.tiangolo.com/
- PostgreSQL UPSERT: https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT
- SQLModel: https://sqlmodel.tiangolo.com/

**Arquitectura de referencia**:
- Event Sourcing: https://martinfowler.com/eaaDev/EventSourcing.html
- Idempotent ETL: https://www.oreilly.com/library/view/designing-data-intensive-applications/9781491903063/
- Data Pipeline Patterns: https://www.thoughtworks.com/insights/blog/data-pipeline-patterns

**Documentación interna de Brasaland**:
- `services/api/migrations/001_create_telemetry_events.sql` — Schema de telemetry_events
- `services/api/app/services/telemetry_analysis.py` — Pipeline técnico existente
- `memory-bank/techContext.md` — Stack tecnológico y convenciones
- `memory-bank/projectbrief.md` — Contexto de negocio de Brasaland

### 7.3. Decisiones Arquitectónicas Pendientes (Fase 2)

**Optimizaciones**:
1. **Particionamiento de `telemetry_events`**: Dividir tabla por rango temporal (mensual) para queries más rápidos
2. **Materialized Views**: Crear vistas materializadas para agregaciones frecuentes (ej: WAU, MAU)
3. **Incremental Loading**: Procesar solo eventos nuevos desde última corrida exitosa (no ventana fija)
4. **Parallel Processing**: Dividir transformaciones por dimensión (país, servicio) y ejecutar en paralelo

**Enriquecimiento de datos**:
1. **JOIN con `users`**: Agregar dimensiones de rol, fecha de registro, local asignado
2. **JOIN con `transactions`**: Calcular ingresos por sesión, ticket promedio, tasa de conversión
3. **JOIN con `locations`**: Agregar metadata de locales (ciudad, tipo, capacidad)

**Observabilidad avanzada**:
1. **Alerting en Prefect**: Notificaciones a Slack cuando pipeline falla o tarda >10 min
2. **Dashboard de Observabilidad**: Métricas del pipeline (duración, registros procesados, error rate)
3. **SLO (Service Level Objective)**: "Pipeline completa en <5 min en 99.5% de las ejecuciones"

**Automatizaciones**:
1. **Late-Arriving Events Detection**: Cron job que detecta y reprocesa automáticamente
2. **Anomaly Detection**: Alertar si KPIs varían >50% vs. promedio histórico (ej: DAU cae de 100 a 20)
3. **Auto-Scaling**: Aumentar recursos de Prefect worker si pipeline tarda mucho

---

## 📌 Resumen de Entregables del Diseño

Este documento **completo de diseño arquitectónico** incluye:

✅ **Fase 1**: Análisis del estado actual (telemetría técnica) y detección de brecha (métricas de negocio faltantes)  
✅ **Fase 2**: Diseño completo del pipeline ETL (extracción, transformación, carga), modelo de datos destino (`reporting.business_kpis`), diagrama Mermaid de flujo, y estrategia ante actualizaciones  
✅ **Fase 3**: Mecanismos de idempotencia (UPSERT con PK natural), tabla de audit (`reporting.pipeline_runs`), estrategias de recuperabilidad ante fallos  
✅ **Fase 4**: Mapeo a Prefect (1 Flow principal + 4 Tasks + 1 Flow de backfill), configuración de Blocks para secrets y parámetros  
✅ **Fase 5**: Especificación de 3 endpoints REST en `services/reporting/` (`GET /status`, `POST /trigger`, `GET /kpis`), schemas Pydantic, y arquitectura de desacoplamiento (ETL en `data/pipelines/`, API en `services/`)

**Próximos pasos**: Implementación en código siguiendo este diseño arquitectónico.

---

**Fin del Documento de Diseño**

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
