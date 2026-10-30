# Business Performance ETL Pipeline - Brasaland Digital

Pipeline de orquestación en Prefect que transforma eventos de telemetría técnica en métricas de desempeño de negocio para el dashboard ejecutivo de Brasaland.

---

## 📋 Descripción

Este pipeline implementa el diseño especificado en [`docs/business-pipeline-design.md`](../../../docs/business-pipeline-design.md) con las siguientes características:

### Arquitectura ETL
```
telemetry_events → Extract → Transform → Load → reporting.business_kpis
```

### KPIs Calculados
- **Usuarios Activos**: DAU (Daily Active Users)
- **Sesiones y Engagement**: Total de sesiones, promedio de eventos por sesión
- **Disponibilidad del Sistema**: % de uptime
- **Tasa de Errores**: % de eventos con error
- **Autenticación**: Tasa de éxito de login
- **Calidad de Datos**: % de eventos con user_id/session_id

### Stakeholders
- **CEO**: Mariana Restrepo (dashboard ejecutivo, briefing semanal)
- **Gerentes de Área**: Operaciones, Marketing, RRHH, Tecnología

---

## 🚀 Instalación

### 1. Instalar Dependencias

```bash
# Desde la raíz del monorepo
cd data/pipelines/business-performance
pip install -r requirements.txt
```

### 2. Configurar Conexión a Base de Datos

```bash
# Opción 1: Variable de entorno
export SUPABASE_DATABASE_URL="postgresql://user:pass@host:5432/dbname"

# Opción 2: Archivo .env (en raíz del monorepo)
echo "SUPABASE_DATABASE_URL=postgresql://..." >> .env
```

### 3. Inicializar Tablas (Primera Ejecución)

El pipeline crea automáticamente las tablas necesarias:
- `reporting.pipeline_runs` (auditoría)
- `reporting.business_kpis` (KPIs)

---

## 💻 Uso

### Ejecución Standalone (CLI)

```bash
# Ventana por defecto (últimas 24 horas)
python data/pipelines/business-performance/pipeline.py

# Últimos 7 días
python data/pipelines/business-performance/pipeline.py --days 7

# Rango específico (backfill)
python data/pipelines/business-performance/pipeline.py \
  --start-date 2026-10-01 \
  --end-date 2026-10-31

# Con origen del trigger
python data/pipelines/business-performance/pipeline.py \
  --triggered-by scheduled
```

### Desde Python

```python
from datetime import datetime, timezone, timedelta
from data.pipelines.business_performance.pipeline import business_performance_etl_flow

# Ejecutar flow
result = business_performance_etl_flow(
    start_date=datetime(2026, 10, 23, tzinfo=timezone.utc),
    end_date=datetime(2026, 10, 30, tzinfo=timezone.utc),
    triggered_by="manual"
)

print(f"Run ID: {result['run_id']}")
print(f"Registros procesados: {result['records_inserted']}")
```

### Deployment en Prefect (Producción)

```bash
# 1. Iniciar Prefect server (local)
prefect server start

# 2. Crear deployment
prefect deployment build \
  data/pipelines/business-performance/pipeline.py:business_performance_etl_flow \
  -n "daily-etl" \
  -q "default"

# 3. Aplicar deployment
prefect deployment apply business_performance_etl_flow-deployment.yaml

# 4. Programar ejecución diaria (3:00 AM UTC)
prefect deployment schedule create \
  business-performance-etl/daily-etl \
  --cron "0 3 * * *" \
  --timezone "UTC"
```

---

## 🔧 Configuración

### Parámetros del Flow

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `start_date` | `datetime` | Ayer 00:00 UTC | Inicio del rango temporal |
| `end_date` | `datetime` | Hoy 00:00 UTC | Fin del rango temporal |
| `triggered_by` | `str` | `"manual"` | Origen del trigger (`manual`, `scheduled`, `api`) |

### Variables de Entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `SUPABASE_DATABASE_URL` | ✅ | URL de conexión PostgreSQL/Supabase |

---

## 🛡️ Características de Resiliencia

### 1. Reintentos Inteligentes

Cada task tiene configuración de reintentos:

- **Extract Task**: 3 reintentos con 60s de delay
  - Justificación: Fallos transitorios (timeout, red)
- **Transform Task**: 1 reintento con 30s de delay
  - Justificación: Errores suelen ser deterministas
- **Load Task**: 2 reintentos con 30s de delay
  - Justificación: Deadlocks o locks de tabla

### 2. Caching de Transformaciones

La task `transform_events_to_kpis` tiene caching de 1 hora:
- Si procesamos el mismo rango dos veces → reutiliza transformación
- Clave de caché: Hash del DataFrame de entrada + rango de fechas

### 3. Idempotencia Garantizada

La carga usa UPSERT basado en constraint único:
```sql
ON CONFLICT (date, country, service, warehouse)
DO UPDATE SET ...
```

**Resultado**: Ejecutar N veces = mismo resultado (sin duplicados)

### 4. Tolerancia a Fallos Parciales

La notificación de completado es **opcional**:
- Se invoca con `return_state=True`
- Si falla → pipeline continúa normalmente
- Log de warning, no error crítico

### 5. Auditoría Completa

Cada ejecución registra en `reporting.pipeline_runs`:
- `run_id`, `started_at`, `finished_at`, `duration_seconds`
- `records_read`, `records_processed`, `records_inserted`
- `status` (`running`, `completed`, `failed`)
- `error_message`, `error_traceback` (si aplica)

---

## 📊 Consulta de Resultados

### KPIs de Negocio

```sql
-- KPIs últimos 7 días
SELECT 
    date,
    daily_active_users,
    total_sessions,
    total_events,
    system_availability_pct,
    error_rate
FROM reporting.business_kpis
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY date DESC;
```

### Historial de Ejecuciones

```sql
-- Últimas 10 ejecuciones
SELECT 
    run_id,
    started_at,
    finished_at,
    duration_seconds,
    status,
    records_processed
FROM reporting.pipeline_runs
ORDER BY started_at DESC
LIMIT 10;
```

### Diagnóstico de Fallos

```sql
-- Ejecuciones fallidas últimos 7 días
SELECT 
    run_id,
    started_at,
    error_message,
    SUBSTRING(error_traceback, 1, 200) AS traceback_preview
FROM reporting.pipeline_runs
WHERE status = 'failed'
  AND started_at >= NOW() - INTERVAL '7 days'
ORDER BY started_at DESC;
```

---

## 🔍 Troubleshooting

### Error: "relation telemetry_events does not exist"

**Causa**: La tabla de telemetría no está creada.

**Solución**: Ejecutar migración de telemetría:
```bash
psql $SUPABASE_DATABASE_URL < services/api/migrations/001_create_telemetry_events.sql
```

### Error: "connection refused"

**Causa**: Variable `SUPABASE_DATABASE_URL` no configurada o incorrecta.

**Solución**:
```bash
export SUPABASE_DATABASE_URL="postgresql://user:pass@host:5432/dbname"
```

### Pipeline procesa 0 eventos

**Causa**: No hay eventos en el rango temporal especificado.

**Solución**: Verificar que `telemetry_events` tiene datos:
```sql
SELECT COUNT(*), MIN(timestamp), MAX(timestamp) 
FROM telemetry_events;
```

### Caching no funciona

**Causa**: El DataFrame de entrada cambió (late-arriving events).

**Esto es correcto**: Si llegan nuevos eventos, el caché se invalida automáticamente y se recalcula la transformación.

---

## 📝 Ejemplos de Uso

### Caso 1: Run Diario Automatizado

```bash
# Cron job diario (3:00 AM UTC)
0 3 * * * cd /path/to/monorepo && python data/pipelines/business-performance/pipeline.py --triggered-by scheduled
```

### Caso 2: Backfill Histórico (Octubre Completo)

```bash
python data/pipelines/business-performance/pipeline.py \
  --start-date 2026-10-01 \
  --end-date 2026-11-01 \
  --triggered-by manual
```

### Caso 3: Reprocesamiento Tras Fix de Bug

Si se corrige un bug en la transformación:

```bash
# 1. Bump version en pipeline.py
PIPELINE_VERSION = "1.0.1"

# 2. Reprocesar últimos 30 días
python data/pipelines/business-performance/pipeline.py --days 30
```

La tabla de KPIs se actualiza (UPSERT) y la auditoría registra la nueva versión.

---

## 🔗 Referencias

- **Diseño Completo**: [`docs/business-pipeline-design.md`](../../../docs/business-pipeline-design.md)
- **Auditoría del Diseño**: Rúbrica oficial (12/12 criterios cumplidos)
- **Documentación de Prefect**: https://docs.prefect.io/
- **Documentación de Pandas**: https://pandas.pydata.org/docs/

---

## 📞 Soporte

Para dudas o issues, contactar al equipo de Brasaland Digital:
- **CTO**: Nicolás Park (Medellín)
- **Data Team**: `data@brasaland.com`

---

**Versión**: 1.0.0  
**Última actualización**: 30 de Octubre, 2026

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
