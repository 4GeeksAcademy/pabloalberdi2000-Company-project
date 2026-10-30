## 🌙 Sistema de Exportación Nocturna - Brasaland Digital

**Ticket**: #DEV-53  
**Versión**: 1.0.0  
**Fecha**: 30 de Octubre, 2026  
**Estado**: ✅ **IMPLEMENTADO - LISTO PARA DEPLOYMENT**

---

## 📋 Resumen Ejecutivo

Se ha implementado un sistema de ejecución nocturna automatizada que:

1. **Exporta telemetría** del día anterior a CSV (backup/auditoría)
2. **Ejecuta el pipeline de datos** como subproceso independiente
3. **Garantiza idempotencia** (no reprocesar fechas ya completadas)
4. **Implementa lock distribuido** (prevenir ejecuciones paralelas)
5. **Registra auditoría completa** en tabla `job_runs`

---

## 🏗️ Arquitectura del Sistema

### Separación de Capas

```
┌─────────────────────────────────────────────────────────────┐
│  CAPA DE ORQUESTACIÓN (job_runs)                            │
│  - Lock distribuido                                          │
│  - Idempotencia por fecha                                    │
│  - Auditoría de ejecuciones                                  │
│  - Exportación CSV                                           │
│  - Disparo de subproceso                                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  CAPA ETL INTERNA (pipeline_runs)                           │
│  - Extract/Transform/Load                                    │
│  - Marcas de agua                                            │
│  - Cálculo de KPIs                                           │
│  - Persistencia en reporting.business_kpis                   │
└─────────────────────────────────────────────────────────────┘
```

**Principio de Separación**:
- `job_runs`: Orquestación externa (¿cuándo?, ¿se ejecutó ya?, ¿está corriendo?)
- `pipeline_runs`: ETL interno (¿qué se procesó?, ¿qué KPIs se calcularon?)

---

## 📁 Archivos Implementados

```
services/api/migrations/
└── 002_create_job_runs.sql          # ⭐ Migración SQL (tabla job_runs)

services/api/app/services/
└── job_runner.py                     # ⭐ Módulo de control de estado

scripts/
└── nightly_export.py                 # ⭐ Script principal nocturno

/ (raíz)
└── NIGHTLY_EXPORT_SYSTEM.md         # ⭐ Esta documentación
```

---

## 🗄️ Modelo de Datos: Tabla `job_runs`

### Schema

```sql
CREATE TABLE job_runs (
    id BIGSERIAL PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,
    target_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    error_message TEXT,
    error_traceback TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Índices

- **`idx_job_runs_unique_date`** (UNIQUE): `(job_name, target_date)`
  - Garantiza idempotencia: 1 job × 1 fecha
  
- **`idx_job_runs_status`** (WHERE status='processing'): `(job_name, status)`
  - Optimiza consultas de lock distribuido

### Ciclo de Vida del Estado

```
pending → processing → completed
                    └→ failed
```

**Lock Distribuido**: Cualquier job en estado `processing` actúa como lock.

**Idempotencia**: No se puede crear segundo job para misma fecha si ya existe uno `completed`.

---

## 🔧 Módulo de Control: `job_runner.py`

### Funciones Públicas

#### 1. `has_processing_lock(job_name: str) -> bool`

Detecta si existe un job en ejecución.

```python
if has_processing_lock("nightly_export"):
    print("Job ya corriendo, abortar")
    return
```

**Comportamiento fail-safe**: Si falla query de BD → retorna `True` (asumir que SÍ hay lock)

---

#### 2. `has_completed_for_date(job_name: str, target_date: date) -> bool`

Verifica si ya se procesó exitosamente una fecha.

```python
from datetime import date

if has_completed_for_date("nightly_export", date(2026, 10, 29)):
    print("Ya procesado, omitir")
    return
```

**Comportamiento fail-safe**: Si falla query → retorna `False` (permitir reintento)

---

#### 3. `create_job_run(job_name: str, target_date: date) -> JobRun`

Crea registro en estado `processing` (activa lock distribuido).

```python
job_run = create_job_run("nightly_export", target_date)
print(f"Job run creado: {job_run.id}")
```

**Raises**: `Exception` si falla (ej: duplicate key por constraint único)

---

#### 4. `update_job_status(run_id: int, status: str, error_message: str | None = None)`

Finaliza job con estado `completed` o `failed`.

```python
try:
    # ... trabajo ...
    update_job_status(job_run.id, "completed")
except Exception as e:
    update_job_status(
        job_run.id,
        "failed",
        str(e),
        traceback.format_exc()
    )
```

**Validación**: Solo acepta `completed` o `failed`. Si `failed` → `error_message` obligatorio.

---

## 🚀 Script Principal: `nightly_export.py`

### Flujo de Ejecución

```
1. Resolver fecha objetivo
   ↓
2. Validar idempotencia (¿ya completado?)
   ↓ No
3. Validar lock distribuido (¿ya en ejecución?)
   ↓ No
4. Crear job run (estado: processing)
   ↓
5. Exportar CSV a data/raw/
   ↓
6. Ejecutar pipeline como subproceso
   ↓
7. Actualizar job run (estado: completed/failed)
```

### Resolución de Fecha Objetivo

**Modo Automático** (ayer):
```bash
python scripts/nightly_export.py
# Procesa: ayer en UTC
```

**Modo Manual** (fecha específica):
```bash
TARGET_DATE=2026-10-29 python scripts/nightly_export.py
# Procesa: 2026-10-29
```

### Exportación CSV

**Destino**: `data/raw/telemetry_YYYY-MM-DD.csv`

**Propósito**: 
- ✅ Snapshot de backup/auditoría
- ✅ Recuperación en frío si BD falla
- ❌ **NO** es input del pipeline (pipeline lee directamente de BD)

**Comportamiento**:
- Si CSV ya existe → omitir exportación
- Si no hay eventos para la fecha → crear CSV vacío

### Ejecución del Pipeline

**Comando generado**:
```bash
python data/pipelines/business-performance/pipeline_v2.py \
  --start-date 2026-10-29 \
  --end-date 2026-10-30 \
  --triggered-by scheduled
```

**Características**:
- Timeout: 30 minutos (1800 segundos)
- Captura stdout/stderr
- Exit code 0 = éxito, != 0 = fallo

**Dry-Run Mode** (solo exportar CSV, sin pipeline):
```bash
DRY_RUN=true python scripts/nightly_export.py
```

---

## ⏰ Programación con Cron

### Opción 1: Crontab del Host

```bash
# Editar crontab
crontab -e

# Agregar línea (ejecutar diariamente a las 2:00 AM UTC)
0 2 * * * cd /path/to/project && /path/to/venv/bin/python scripts/nightly_export.py >> logs/nightly.log 2>&1
```

### Opción 2: Systemd Timer (Linux)

**Archivo: `/etc/systemd/system/nightly-export.service`**
```ini
[Unit]
Description=Brasaland Nightly Export

[Service]
Type=oneshot
WorkingDirectory=/path/to/project
Environment="SUPABASE_DATABASE_URL=postgresql://..."
ExecStart=/path/to/venv/bin/python scripts/nightly_export.py
StandardOutput=append:/var/log/nightly-export.log
StandardError=append:/var/log/nightly-export.log
```

**Archivo: `/etc/systemd/system/nightly-export.timer`**
```ini
[Unit]
Description=Brasaland Nightly Export Timer

[Timer]
OnCalendar=02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Habilitar**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable nightly-export.timer
sudo systemctl start nightly-export.timer
```

### Opción 3: Contenedor Docker con Cron

**Dockerfile adicional** (opcional):
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt

# Instalar cron
RUN apt-get update && apt-get install -y cron

# Agregar crontab
RUN echo "0 2 * * * cd /app && python scripts/nightly_export.py >> /var/log/nightly.log 2>&1" | crontab -

CMD ["cron", "-f"]
```

---

## 📊 Monitoreo y Observabilidad

### Consultas SQL Útiles

#### Últimas 10 ejecuciones
```sql
SELECT
    id,
    target_date,
    status,
    started_at,
    finished_at,
    EXTRACT(EPOCH FROM (finished_at - started_at)) AS duration_seconds
FROM job_runs
WHERE job_name = 'nightly_export'
ORDER BY started_at DESC
LIMIT 10;
```

#### Ejecuciones fallidas (últimos 7 días)
```sql
SELECT
    id,
    target_date,
    started_at,
    error_message
FROM job_runs
WHERE job_name = 'nightly_export'
  AND status = 'failed'
  AND started_at >= NOW() - INTERVAL '7 days'
ORDER BY started_at DESC;
```

#### Detección de locks zombie (jobs en processing > 1 hora)
```sql
SELECT
    id,
    target_date,
    started_at,
    AGE(NOW(), started_at) AS stuck_for
FROM job_runs
WHERE job_name = 'nightly_export'
  AND status = 'processing'
  AND started_at < NOW() - INTERVAL '1 hour';
```

### Función de Emergencia: Liberar Locks Zombie

**⚠️ Solo usar manualmente tras crash del script**

```sql
-- Liberar locks de jobs atascados > 1 hora
SELECT * FROM cleanup_zombie_locks(1);
```

---

## 🛡️ Características de Resiliencia

### 1. Idempotencia Garantizada

**Mecanismo**: Constraint único `(job_name, target_date)`

**Resultado**: Ejecutar N veces el script = misma fecha se procesa solo 1 vez

**Ejemplo**:
```bash
# Primera ejecución: crea job run, procesa datos
python scripts/nightly_export.py

# Segunda ejecución (mismo día): detecta completed, omite trabajo
python scripts/nightly_export.py
# Output: "✅ Job ya completado para esta fecha. Omitir por idempotencia."
```

---

### 2. Lock Distribuido Nativo

**Mecanismo**: Estado `processing` en BD

**Resultado**: No se pueden ejecutar dos instancias del script en paralelo

**Escenario**:
```bash
# Terminal 1 (inicia script)
python scripts/nightly_export.py
# Estado: processing (lock activado)

# Terminal 2 (intenta ejecutar concurrentemente)
python scripts/nightly_export.py
# Output: "🔒 Job ya en ejecución. Abortar para prevenir ejecución paralela."
# Exit code: 0 (no es error, es comportamiento esperado)
```

---

### 3. Zero Registros Zombie

**Garantía**: Todo error transiciona a `failed`

**Implementación**:
```python
try:
    # ... trabajo ...
    update_job_status(job_run.id, "completed")
except Exception as e:
    # SIEMPRE capturar y registrar
    update_job_status(
        job_run.id,
        "failed",
        str(e),
        traceback.format_exc()
    )
```

**Resultado**: Nunca quedan jobs atorados en `processing`

---

### 4. Separación Total de FastAPI

**Principio**: Script corre como proceso INDEPENDIENTE

**Prohibido**:
- ❌ APScheduler embebido en FastAPI
- ❌ `@repeat_every` decorators
- ❌ Lifespan hooks dentro del servidor web
- ❌ Background tasks de FastAPI

**Correcto**:
- ✅ Cron del sistema operativo
- ✅ Systemd timers
- ✅ Contenedor separado con cron
- ✅ Orquestador externo (Airflow, Prefect Cloud, etc.)

**Razón**: No degradar ni bloquear la API con trabajo de batch

---

## 🧪 Testing Manual

### Test 1: Ejecución Normal

```bash
# 1. Ejecutar script
python scripts/nightly_export.py

# 2. Verificar en BD
psql $SUPABASE_DATABASE_URL -c "
SELECT * FROM job_runs
WHERE job_name = 'nightly_export'
ORDER BY started_at DESC
LIMIT 1;"

# 3. Verificar CSV exportado
ls -lh data/raw/telemetry_*.csv
```

**Resultado esperado**:
- Exit code: 0
- Estado en BD: `completed`
- CSV creado en `data/raw/`

---

### Test 2: Idempotencia

```bash
# 1. Primera ejecución
python scripts/nightly_export.py
# Output: "✅ NIGHTLY EXPORT COMPLETADO"

# 2. Segunda ejecución (inmediata)
python scripts/nightly_export.py
# Output: "✅ Job ya completado para <fecha>. Omitir por idempotencia."

# Exit code: 0 en ambos casos
```

---

### Test 3: Lock Distribuido

```bash
# Terminal 1: Iniciar script con delay artificial
# (modificar código temporalmente para agregar sleep)
python scripts/nightly_export.py &

# Terminal 2: Intentar ejecutar concurrentemente
python scripts/nightly_export.py
# Output: "🔒 Job ya en ejecución. Abortar..."
```

---

### Test 4: Fecha Específica (Backfill)

```bash
# Procesar fecha histórica
TARGET_DATE=2026-10-15 python scripts/nightly_export.py

# Verificar que se creó CSV con esa fecha
ls -lh data/raw/telemetry_2026-10-15.csv
```

---

### Test 5: Dry-Run Mode

```bash
# Exportar CSV sin ejecutar pipeline
DRY_RUN=true python scripts/nightly_export.py
# Output: "🏃 DRY_RUN mode: Omitir ejecución de pipeline"

# Verificar que CSV fue creado pero pipeline no corrió
ls data/raw/
```

---

## 🚨 Troubleshooting

### Problema: Script no encuentra módulo `job_runner`

**Error**:
```
ModuleNotFoundError: No module named 'services.api.app.services.job_runner'
```

**Solución**:
```bash
# Verificar que estás en la raíz del proyecto
cd /path/to/project

# Verificar que PYTHONPATH está correcto
export PYTHONPATH=/path/to/project:$PYTHONPATH

# Ejecutar script
python scripts/nightly_export.py
```

---

### Problema: Lock zombie (job atascado en processing)

**Síntoma**: Script siempre dice "Job ya en ejecución"

**Diagnóstico**:
```sql
SELECT * FROM job_runs
WHERE job_name = 'nightly_export'
  AND status = 'processing'
  AND started_at < NOW() - INTERVAL '1 hour';
```

**Solución**:
```sql
-- Opción 1: Liberar lock zombie manualmente
SELECT * FROM cleanup_zombie_locks(1);

-- Opción 2: Actualizar manualmente
UPDATE job_runs
SET status = 'failed',
    error_message = 'Manual cleanup: zombie lock',
    finished_at = NOW()
WHERE