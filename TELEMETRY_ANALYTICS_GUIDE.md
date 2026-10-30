# 📊 Guía de Analytics de Telemetría
## Pipeline Analítico en Python/Pandas + Endpoint FastAPI con Caché

**Versión**: 3.0.0  
**Fecha**: 30 de octubre, 2026  
**Autor**: Claude Sonnet 4.5 (Data Engineer Senior & Backend Analytics Specialist)

---

## 📋 Resumen Ejecutivo

Sistema de analytics de telemetría que transforma datos crudos de `telemetry_events` en **métricas operativas y técnicas** para el equipo de ingeniería.

**Objetivo**: Radar operativo del sistema (volumen, latencia, tasa de errores, distribución de eventos)

**NO es**: Dashboard de negocio, métricas de producto, KPIs de conversión o ingresos

---

## 🏗️ Arquitectura del Sistema

```
┌──────────────────────────────────────────────────────────┐
│  Supabase/PostgreSQL                                     │
│  Tabla: telemetry_events (append-only)                  │
│  - Índices optimizados (B-Tree + GIN)                   │
│  - Event sourcing puro                                   │
└──────────────────────────────────────────────────────────┘
                        │
                        │ SQL Query (filtrado temporal)
                        │ WHERE timestamp >= :start AND timestamp < :end
                        ▼
┌──────────────────────────────────────────────────────────┐
│  Pipeline Analítico (Python/Pandas)                     │
│  services/api/app/services/telemetry_analysis.py        │
│                                                          │
│  1. get_events_per_day()                                │
│     - Agrupa por día con .groupby("date")               │
│     - Cuenta eventos con .size()                        │
│                                                          │
│  2. get_error_rate_by_type()                            │
│     - Detecta errores con .str.contains()               │
│     - Calcula ratio error/total por event_type          │
│                                                          │
│  3. get_auth_failure_rate()                             │
│     - Filtra eventos login_* en SQL                     │
│     - Pivotea con .pivot()                              │
│     - Calcula ratio failed/(failed+success)             │
└──────────────────────────────────────────────────────────┘
                        │
                        │ generate_telemetry_report()
                        │ Orquesta las 3 funciones
                        ▼
┌──────────────────────────────────────────────────────────┐
│  Caché en Memoria (TTL: 60 segundos)                    │
│  Key: (start_date_iso, end_date_iso)                    │
│  Value: (timestamp, report_data)                        │
└──────────────────────────────────────────────────────────┘
                        │
                        │ Cache HIT → Retorna cached_report
                        │ Cache MISS → Ejecuta pipeline
                        ▼
┌──────────────────────────────────────────────────────────┐
│  FastAPI Endpoint                                        │
│  GET /telemetry/report                                   │
│  - Ventana móvil por defecto: últimos 7 días           │
│  - Parámetros opcionales: start_date, end_date         │
│  - Respuesta estandarizada JSON                         │
└──────────────────────────────────────────────────────────┘
```

---

## 🛠️ Principios de Diseño

### **1. Separación de Responsabilidades en Filtrado**

**❌ MAL**: Cargar toda la tabla en memoria y filtrar con Pandas

```python
# ❌ NUNCA HACER ESTO
df = pd.read_sql("SELECT * FROM telemetry_events", con=db)
df = df[df["timestamp"] >= start_date]  # Filtra en memoria
```

**Consecuencia**: OOM (Out of Memory) en tablas con 1M+ eventos

---

**✅ BIEN**: Filtrar en SQL, procesar en Pandas

```python
# ✅ SQL filtra rango temporal
query = text("""
    SELECT timestamp, event_type
    FROM telemetry_events
    WHERE timestamp >= :start_date
      AND timestamp < :end_date
      AND event_type IN ('login_attempt_success', 'login_attempt_failed')
""")

result = db.execute(query, {"start_date": start_date, "end_date": end_date})
rows = result.fetchall()

# ✅ Pandas agrega y extrae propiedades
df = pd.DataFrame(rows, columns=["timestamp", "event_type"])
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)  # CRÍTICO
```

**Beneficio**: Solo se cargan datos necesarios, memoria bajo control

---

### **2. Conversión Obligatoria de Tipos**

**❌ MAL**: Agrupar timestamps como strings

```python
df = pd.DataFrame(rows, columns=["timestamp"])
# df["timestamp"] es string, no datetime
df.groupby(df["timestamp"].str[:10])  # ❌ Particiones erróneas
```

**Consecuencia**: Agrupaciones incorrectas, pérdida de datos

---

**✅ BIEN**: Convertir a datetime UTC antes de groupby

```python
df = pd.DataFrame(rows, columns=["timestamp"])

# CRÍTICO: Convertir a datetime UTC ANTES de cualquier groupby
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

# Ahora sí, extraer fecha y agrupar
df["date"] = df["timestamp"].dt.date
df.groupby("date").size()  # ✅ Agrupación correcta
```

**Beneficio**: Precisión temporal garantizada

---

### **3. Cero Bucles Manuales**

**❌ MAL**: Iterar sobre DataFrame con bucles

```python
# ❌ NUNCA HACER ESTO
error_count = 0
for index, row in df.iterrows():
    if "error" in row["event_type"]:
        error_count += 1
```

**Consecuencia**: 100-1000x más lento que vectorización

---

**✅ BIEN**: Usar métodos vectorizados de Pandas

```python
# ✅ Vectorizado (100-1000x más rápido)
df["is_error"] = df["event_type"].str.contains("error", case=False, na=False)
error_count = df["is_error"].sum()

# ✅ Agregación vectorizada
error_stats = df.groupby("event_type").agg(
    total=("event_type", "size"),
    errors=("is_error", "sum")
)
```

**Beneficio**: Performance 100-1000x mejor

---

### **4. Caché en Endpoint**

**❌ MAL**: Recalcular pipeline en cada request

```python
# ❌ NUNCA HACER ESTO
@router.get("/report")
async def get_report(db: Session):
    # Pipeline se ejecuta en CADA request (lento)
    report = generate_telemetry_report(start, end, db)
    return report
```

**Consecuencia**: Latencia alta, carga innecesaria en DB

---

**✅ BIEN**: Caché en memoria con TTL de 60 segundos

```python
# ✅ Caché con key (start_date_iso, end_date_iso)
_report_cache: Dict[Tuple[str, str], Tuple[float, Dict]] = {}
CACHE_TTL_SECONDS = 60

def get_cached_report(start_date, end_date, db):
    cache_key = (start_date.isoformat(), end_date.isoformat())
    
    if cache_key in _report_cache:
        timestamp, cached_report = _report_cache[cache_key]
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            return cached_report  # ✅ Cache HIT
    
    # Cache MISS: generar y almacenar
    report = generate_telemetry_report(start_date, end_date, db)
    _report_cache[cache_key] = (time.time(), report)
    return report
```

**Beneficio**: Latencia reducida 10-100x para requests repetidas

---

## 📊 Métricas Implementadas

### **1. Volumen Temporal de Eventos (`events_per_day`)**

**Propósito**: Actividad del sistema por día

**Lógica**:
```python
# SQL: Filtrar rango temporal
SELECT timestamp FROM telemetry_events
WHERE timestamp >= :start_date AND timestamp < :end_date

# Pandas: Agrupar por día
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
df["date"] = df["timestamp"].dt.date
events_per_day = df.groupby("date").size().reset_index(name="event_count")
```

**Output**:
```json
{
  "events_per_day": [
    {"date": "2026-10-23", "event_count": 150},
    {"date": "2026-10-24", "event_count": 200},
    {"date": "2026-10-25", "event_count": 180}
  ]
}
```

**Uso**: Detectar picos de actividad o caídas del sistema

---

### **2. Tasa de Errores por Tipo (`error_rate_by_type`)**

**Propósito**: Identificar event_types con mayor tasa de errores

**Lógica de detección**:
- `event_type` contiene `error`, `failed`, `rejected` → es error
- `event_type` contiene `success`, `created`, `updated` → NO es error

**Cálculo**:
```python
# Crear flag is_error (vectorizado)
error_keywords = ["error", "failed", "rejected"]
df["is_error"] = df["event_type"].str.contains(
    "|".join(error_keywords),
    case=False,
    na=False
)

# Agregar por event_type
error_stats = df.groupby("event_type").agg(
    total_events=("event_type", "size"),
    error_events=("is_error", "sum")
)

# Calcular ratio
error_stats["error_rate"] = error_stats["error_events"] / error_stats["total_events"]
```

**Output**:
```json
{
  "error_rate_by_type": [
    {
      "event_type": "frontend_error_uncaught",
      "total_events": 25,
      "error_events": 25,
      "error_rate": 1.0
    },
    {
      "event_type": "outbound_order_rejected",
      "total_events": 50,
      "error_events": 50,
      "error_rate": 1.0
    },
    {
      "event_type": "login_attempt_failed",
      "total_events": 15,
      "error_events": 15,
      "error_rate": 1.0
    },
    {
      "event_type": "page_view",
      "total_events": 500,
      "error_events": 0,
      "error_rate": 0.0
    }
  ]
}
```

**Uso**: Priorizar qué event_types necesitan investigación

---

### **3. Tasa de Fallos de Autenticación (`auth_failure_rate`)**

**Propósito**: Auditoría de seguridad y experiencia de login

**Métrica**: `failure_rate = login_attempt_failed / (login_attempt_failed + login_attempt_success)`

**Lógica**:
```python
# SQL: Filtrar solo eventos de auth
SELECT timestamp, event_type FROM telemetry_events
WHERE timestamp >= :start_date AND timestamp < :end_date
  AND event_type IN ('login_attempt_success', 'login_attempt_failed')

# Pandas: Agrupar por día y tipo
df["date"] = df["timestamp"].dt.date
auth_counts = df.groupby(["date", "event_type"]).size()

# Pivotar para tener columnas success/failed
auth_pivot = auth_counts.pivot(index="date", columns="event_type", values="count")

# Calcular ratio
auth_pivot["failure_rate"] = (
    auth_pivot["login_attempt_failed"] /
    (auth_pivot["login_attempt_failed"] + auth_pivot["login_attempt_success"])
)
```

**Output**:
```json
{
  "auth_failure_rate": [
    {
      "date": "2026-10-23",
      "total_attempts": 100,
      "failed_attempts": 15,
      "success_attempts": 85,
      "failure_rate": 0.15
    },
    {
      "date": "2026-10-24",
      "total_attempts": 120,
      "failed_attempts": 8,
      "success_attempts": 112,
      "failure_rate": 0.0667
    }
  ]
}
```

**Uso**: 
- Alertar si `failure_rate > 0.3` (posible ataque de fuerza bruta)
- Detectar problemas de UX en formulario de login

---

## 🚀 API Endpoint

### **GET /telemetry/report**

**Propósito**: Obtener reporte operativo de telemetría

**Parámetros**:

| Parámetro | Tipo | Obligatorio | Default | Ejemplo |
|-----------|------|-------------|---------|---------|
| `start_date` | string (ISO 8601 UTC) | No | NOW - 7 días | `2026-10-23T00:00:00Z` |
| `end_date` | string (ISO 8601 UTC) | No | NOW | `2026-10-30T00:00:00Z` |

**Ventana móvil por defecto**: Últimos 7 días si no se especifican fechas

---

**Ejemplos de uso**:

```bash
# 1. Últimos 7 días (ventana móvil por defecto)
curl "http://localhost:8000/telemetry/report"

# 2. Periodo específico (octubre 2026)
curl "http://localhost:8000/telemetry/report?start_date=2026-10-01T00:00:00Z&end_date=2026-10-31T00:00:00Z"

# 3. Desde fecha específica hasta ahora
curl "http://localhost:8000/telemetry/report?start_date=2026-10-25T00:00:00Z"

# 4. Últimas 24 horas
curl "http://localhost:8000/telemetry/report?start_date=$(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%SZ)"
```

---

**Respuesta estandarizada**:

```json
{
  "period": {
    "from": "2026-10-23T00:00:00+00:00",
    "to": "2026-10-30T00:00:00+00:00"
  },
  "metrics": {
    "events_per_day": [
      {"date": "2026-10-23", "event_count": 150},
      {"date": "2026-10-24", "event_count": 200}
    ],
    "error_rate_by_type": [
      {
        "event_type": "frontend_error_uncaught",
        "total_events": 25,
        "error_events": 25,
        "error_rate": 1.0
      }
    ],
    "auth_failure_rate": [
      {
        "date": "2026-10-23",
        "total_attempts": 100,
        "failed_attempts": 15,
        "success_attempts": 85,
        "failure_rate": 0.15
      }
    ]
  }
}
```

---

**Códigos de Estado**:

| Código | Descripción | Ejemplo |
|--------|-------------|---------|
| 200 | Éxito | Reporte generado correctamente |
| 400 | Formato de fecha inválido | `start_date=invalid-date` |
| 422 | Rango inválido | `start_date >= end_date` |
| 500 | Error interno | Fallo en pipeline analítico |

---

## 🧪 Testing

### **Setup**

```bash
# 1. Iniciar backend
cd services/api
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

---

### **Test 1: Health Check**

```bash
curl "http://localhost:8000/telemetry/report/health"

# Respuesta esperada:
{
  "status": "healthy",
  "cache_entries": 0,
  "cache_ttl_seconds": 60
}
```

---

### **Test 2: Reporte con Ventana Móvil (últimos 7 días)**

```bash
curl "http://localhost:8000/telemetry/report" | python3 -m json.tool

# Verificar en logs del backend:
# ❌ Cache MISS: Generando reporte...
# 📊 Volumen temporal: 7 días con datos
# 📊 Error rate: 10 tipos de evento analizados
# 📊 Auth failure rate: 5 días con intentos de login
# ✅ Reporte generado: 7 días, 10 tipos de evento, 5 días con auth
# 💾 Reporte almacenado en caché
```

---

### **Test 3: Cache HIT (segunda request idéntica)**

```bash
# Primera request (Cache MISS)
time curl -s "http://localhost:8000/telemetry/report?start_date=2026-10-20T00:00:00Z&end_date=2026-10-27T00:00:00Z" > /dev/null
# real    0m0.250s  (Pipeline ejecutado completo)

# Segunda request (Cache HIT - debe ser mucho más rápida)
time curl -s "http://localhost:8000/telemetry/report?start_date=2026-10-20T00:00:00Z&end_date=2026-10-27T00:00:00Z" > /dev/null
# real    0m0.015s  (10-100x más rápido)

# Verificar en logs del backend:
# ✅ Cache HIT: Reporte servido desde caché (age: 5.2s)
```

---

### **Test 4: Limpieza Manual del Caché**

```bash
# Limpiar caché
curl -X DELETE "http://localhost:8000/telemetry/report/cache"

# Respuesta:
{
  "cleared_entries": 3,
  "message": "Caché limpiado exitosamente"
}

# Verificar health check (cache_entries debe ser 0)
curl "http://localhost:8000/telemetry/report/health"
```

---

### **Test 5: Script Completo**

```bash
# Ejecutar script de testing completo
./services/api/test_telemetry_report.sh

# El script ejecuta:
# - Health check
# - Reporte con ventana móvil
# - Reporte con periodo específico
# - Test de caché (MISS y HIT)
# - Error handling (formato inválido, rango inválido)
# - Limpieza de caché
```

---

## 📊 Queries SQL para Verificación

### **Query 1: Contar eventos en últimos 7 días**

```sql
SELECT COUNT(*) as total_events
FROM telemetry_events
WHERE timestamp > NOW() - INTERVAL '7 days';

-- Resultado esperado: Coincide con sum(events_per_day[].event_count)
```

---

### **Query 2: Top 10 event_types más frecuentes**

```sql
SELECT 
    event_type,
    COUNT(*) as total
FROM telemetry_events
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY event_type
ORDER BY total DESC
LIMIT 10;

-- Comparar con error_rate_by_type (suma de total_events debe coincidir)
```

---

### **Query 3: Verificar eventos de autenticación**

```sql
SELECT 
    DATE(timestamp) as date,
    event_type,
    COUNT(*) as total
FROM telemetry_events
WHERE timestamp > NOW() - INTERVAL '7 days'
  AND event_type IN ('login_attempt_success', 'login_attempt_failed')
GROUP BY DATE(timestamp), event_type
ORDER BY date, event_type;

-- Comparar con auth_failure_rate (total_attempts debe coincidir)
```

---

## 🔧 Troubleshooting

### **Error: "No module named 'pandas'"**

**Causa**: Pandas no instalado

**Fix**:
```bash
cd services/api
source venv/bin/activate
pip install pandas
```

---

### **Error: "Cache MISS en cada request"**

**Causa**: Parámetros de fecha diferentes entre requests

**Diagnóstico**:
```python
# Key del caché:
cache_key = (start_date.isoformat(), end_date.isoformat())

# Si start_date o end_date cambia ligeramente, es Cache MISS
```

**Fix**: Usar fechas exactas idénticas o limpiar caché manualmente

---

### **Warning: "PerformanceWarning: DataFrame is highly fragmented"**

**Causa**: Concatenación excesiva de DataFrames en loop

**Fix**: Ya implementado (sin bucles, solo vectorización)

---

### **Error: "groupby error: object of type 'str' has no attribute 'dt'"**

**Causa**: Timestamp no convertido a datetime antes de groupby

**Fix**: Ya implementado (conversión obligatoria con `pd.to_datetime()`)

---

## 📈 Roadmap: Próximas Métricas

### **Fase 4: Latencia de Endpoints** (1-2 semanas)

**Métrica**: Distribución y percentiles (p50, p95, p99) de tiempos de respuesta

**Lógica**:
```python
# SQL: Filtrar eventos con latencia en tags
SELECT tags->>'latency_ms' as latency
FROM telemetry_events
WHERE timestamp >= :start_date
  AND tags ? 'latency_ms'

# Pandas: Calcular percentiles
df["latency"] = pd.to_numeric(df["latency"], errors="coerce")
percentiles = df["latency"].quantile([0.5, 0.95, 0.99])
```

---

### **Fase 5: Stock Alerts por Warehouse** (1-2 semanas)

**Métrica**: Alertas de desabasto por local

**Lógica**:
```python
# SQL: Filtrar eventos stock_threshold_triggered
SELECT tags->>'warehouse' as warehouse, COUNT(*) as alerts
FROM telemetry_events
WHERE event_type = 'stock_threshold_triggered'
  AND tags->>'threshold_severity' = 'critical'
GROUP BY warehouse
```

---

### **Fase 6: User Activity Heatmap** (2-3 semanas)

**Métrica**: Horas pico de actividad por día de semana

**Lógica**:
```python
# Pandas: Extraer día de semana y hora
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
df["weekday"] = df["timestamp"].dt.day_name()
df["hour"] = df["timestamp"].dt.hour

# Agrupar por weekday y hour
heatmap = df.groupby(["weekday", "hour"]).size()
```

---

## 📄 Archivos del Sistema

### **Backend**

- [`services/api/app/services/telemetry_analysis.py`](services/api/app/services/telemetry_analysis.py) - Pipeline analítico (327 líneas)
- [`services/api/app/routers/telemetry_report.py`](services/api/app/routers/telemetry_report.py) - Endpoint FastAPI (263 líneas)
- [`services/api/app/main.py`](services/api/app/main.py) - Registro de router (líneas 6, 81-82)

### **Testing**

- [`services/api/test_telemetry_report.sh`](services/api/test_telemetry_report.sh) - Script de testing completo (180 líneas)

### **Documentación**

- [`TELEMETRY_ANALYTICS_GUIDE.md`](TELEMETRY_ANALYTICS_GUIDE.md) - Esta guía
- [`TELEMETRY_PERSISTENCE_GUIDE.md`](TELEMETRY_PERSISTENCE_GUIDE.md) - Guía de persistencia
- [`TELEMETRY_PERSISTENCE_AUDIT.md`](TELEMETRY_PERSISTENCE_AUDIT.md) - Auditoría de persistencia

---

## 🏷️ Metadata

**Autor**: Claude Sonnet 4.5 (Data Engineer Senior)  
**Fecha de implementación**: 30 de octubre, 2026  
**Líneas de código**: 590 líneas (pipeline + endpoint)  
**Dependencias**: Pandas, SQLModel, FastAPI  
**Estado**: ✅ **Producción Ready**

---

**Próxima Revisión**: Tras implementación de Fase 4 (Latencia de Endpoints)

---

*Fin de la Guía*
