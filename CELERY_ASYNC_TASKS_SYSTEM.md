## 🚀 Sistema de Tareas Asíncronas con Celery y Redis - Brasaland Digital

**Ticket**: #DEV-55  
**Versión**: 1.0.0  
**Fecha**: 30 de Octubre, 2026  
**Estado**: ✅ **IMPLEMENTADO - LISTO PARA TESTING**

---

## 📋 Resumen Ejecutivo

Se ha implementado un sistema completo de procesamiento asíncrono de tareas para desacoplar operaciones pesadas del ciclo request-response de FastAPI usando el patrón Productor/Consumidor.

### Componentes Implementados

1. **Redis**: Broker de mensajes + result backend
2. **Celery**: Motor de procesamiento asíncrono con workers independientes
3. **Flower**: UI web de monitoreo en tiempo real (puerto 5555)
4. **FastAPI Endpoints**: Productores que encolan tareas (202 Accepted)
5. **Dead Letter Queue**: Persistencia de tareas fallidas en PostgreSQL
6. **Docker Compose**: Orquestación de servicios con healthchecks

---

## 🏗️ Arquitectura del Sistema

### Patrón Productor/Consumidor

```
┌─────────────────────────────────────────────────────────────────┐
│  CLIENTE (Frontend / API Consumer)                              │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTP POST
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASTAPI - PRODUCTOR                                            │
│  - Endpoint encola tarea                                         │
│  - Retorna 202 Accepted + task_id en <200ms                     │
│  - NO espera resultado                                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │ .delay()
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  REDIS - BROKER & RESULT BACKEND                                │
│  - Almacena mensajes en cola (ligeros: solo IDs)                │
│  - Persiste resultados tras completar                            │
│  - Política: noeviction (no perder tareas)                       │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Consume mensaje
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  CELERY WORKERS - CONSUMIDORES (Procesos Independientes)       │
│  - Procesan tareas en background                                 │
│  - 3 reintentos con backoff exponencial                          │
│  - Timeout: 30 min por tarea                                     │
│  - ACK solo tras éxito                                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ├─ Éxito → Resultado a Redis
                       │
                       └─ Fallo tras 3 intentos → DLQ (PostgreSQL)
                       
┌─────────────────────────────────────────────────────────────────┐
│  FLOWER - MONITOREO WEB (http://localhost:5555)                │
│  - Estado de workers                                             │
│  - Tareas activas, completadas, fallidas                         │
│  - Gráficos de throughput                                        │
│  - Logs en tiempo real                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Archivos Implementados

```
services/api/
├── app/
│   ├── celery_app.py                    # ⭐ Configuración Celery + Tareas
│   └── routers/
│       └── tasks.py                     # ⭐ Endpoints FastAPI (Productor)
├── migrations/
│   └── 003_create_failed_tasks.sql      # ⭐ Dead Letter Queue (DLQ)
└── requirements.txt                      # ⭐ Dependencias (celery, redis, flower)

/ (raíz)
├── docker-compose.yml                    # ⭐ Servicios Redis, Celery, Flower
└── CELERY_ASYNC_TASKS_SYSTEM.md         # ⭐ Esta documentación
```

---

## 🐳 Infraestructura Docker

### Servicios Configurados

#### 1. Redis (Broker & Result Backend)

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  command: redis-server --maxmemory-policy noeviction --appendonly yes
  volumes:
    - redis-data:/data
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
```

**Características**:
- Política `noeviction`: No eliminar claves bajo presión de memoria (previene pérdida de tareas)
- AOF (Append Only File): Persistencia en disco
- Healthcheck: Verifica conectividad antes de levantar workers

---

#### 2. Celery Worker

```yaml
celery-worker:
  command: celery -A app.celery_app.celery_app worker --loglevel=info --concurrency=4
  environment:
    - REDIS_URL=redis://redis:6379/0
    - CELERY_BROKER_URL=redis://redis:6379/0
    - CELERY_RESULT_BACKEND=redis://redis:6379/0
  depends_on:
    redis:
      condition: service_healthy
```

**Características**:
- **Proceso independiente**: NO corre dentro de FastAPI
- **Concurrency**: 4 workers paralelos
- **Reinicio automático**: `restart: unless-stopped`
- **Healthcheck dependency**: Solo inicia tras confirmar Redis activo

---

#### 3. Flower (Monitoring UI)

```yaml
flower:
  command: celery -A app.celery_app.celery_app flower --port=5555
  ports:
    - "5555:5555"
```

**Acceso**: http://localhost:5555

**Features**:
- Dashboard de workers activos
- Estado de tareas (pending, active, succeeded, failed)
- Gráficos de throughput
- Logs en tiempo real
- Retry manual de tareas

---

## 📝 Configuración de Celery

### Configuración Avanzada (`celery_app.py`)

```python
celery_app.conf.update(
    # Serialización
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timeouts
    task_time_limit=1800,         # 30 min hard limit
    task_soft_time_limit=1620,    # 27 min soft limit (warning)
    
    # Reintentos
    task_acks_late=True,           # ACK solo tras éxito
    task_reject_on_worker_lost=True,  # Re-encolar si worker muere
    
    # Result backend
    result_expires=3600,           # 1 hora
    result_persistent=True,        # Persistir en Redis AOF
    
    # Worker
    worker_prefetch_multiplier=1,  # 1 tarea por worker
    worker_max_tasks_per_child=1000,  # Reciclar cada 1000 tareas
)
```

---

## 🔧 Tareas Implementadas

### 1. `process_telemetry_batch`

**Propósito**: Procesar lote de eventos de telemetría y calcular KPIs.

**Configuración**:
- **Max retries**: 3
- **Base delay**: 60 segundos
- **Backoff**: Exponencial (60s → 120s → 240s)
- **Jitter**: Aleatorio para evitar thundering herd
- **Timeout**: 30 minutos

**Flujo**:
```python
# 1. Encolar desde FastAPI
task = process_telemetry_batch.delay(batch_id=123)
# Retorna: {"task_id": "uuid", "status": "pending"}

# 2. Worker carga datos desde BD (no del mensaje)
events = query("SELECT * FROM telemetry_events WHERE batch_id = ?", batch_id)

# 3. Procesar (calcular KPIs)
kpis = calculate_kpis(events)

# 4. Persistir resultados
insert_kpis(kpis)

# 5. Retornar resultado
return {"batch_id": 123, "events_processed": 1500, "kpis_calculated": 45}
```

**Reintentos**:
- **Intento 1**: Inmediato
- **Intento 2**: +60 segundos
- **Intento 3**: +120 segundos
- **Intento 4**: +240 segundos
- **Tras 4 intentos**: Persiste en DLQ (`failed_tasks`)

---

### 2. `generate_business_report`

**Propósito**: Generar reporte de negocio (PDF/Excel) con agregaciones de KPIs.

**Configuración**:
- **Max retries**: 3
- **Base delay**: 120 segundos
- **Backoff**: Exponencial
- **Timeout**: 30 minutos

**Flujo**:
```python
# 1. Encolar
task = generate_business_report.delay(
    report_id=456,
    start_date="2026-10-01",
    end_date="2026-10-31"
)

# 2. Worker consulta KPIs
kpis = query("SELECT * FROM business_kpis WHERE date BETWEEN ? AND ?", ...)

# 3. Generar PDF/Excel
file_path = generate_pdf(kpis)

# 4. Retornar ruta del archivo
return {"report_id": 456, "file_path": "/reports/business_report_456.pdf"}
```

---

## 🌐 Endpoints FastAPI

### POST /tasks/telemetry/batch

**Request**:
```json
{
  "batch_id": 123
}
```

**Response** (202 Accepted en <200ms):
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "message": "Lote 123 encolado. Usa task_id para consultar progreso."
}
```

---

### POST /tasks/reports/generate

**Request**:
```json
{
  "report_id": 456,
  "start_date": "2026-10-01",
  "end_date": "2026-10-31"
}
```

**Response** (202 Accepted):
```json
{
  "task_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "status": "pending",
  "message": "Reporte 456 encolado. Usa task_id para consultar progreso."
}
```

---

### GET /tasks/{task_id}

**Response - Pending**:
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "result": null,
  "error": null
}
```

**Response - Success**:
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "success",
  "result": {
    "batch_id": 123,
    "events_processed": 1500,
    "kpis_calculated": 45,
    "duration_seconds": 120.5,
    "completed_at": "2026-10-30T12:00:00Z"
  },
  "error": null
}
```

**Response - Failure**:
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "failure",
  "result": null,
  "error": "Connection timeout: Unable to reach database after 3 retries"
}
```

---

## 🗄️ Dead Letter Queue (DLQ)

### Tabla `failed_tasks`

```sql
CREATE TABLE failed_tasks (
    id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL UNIQUE,
    task_name VARCHAR(255) NOT NULL,
    args TEXT,
    kwargs TEXT,
    error_message TEXT NOT NULL,
    error_traceback TEXT,
    retries INT NOT NULL DEFAULT 0,
    failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reprocessed_at TIMESTAMPTZ,
    reprocess_status VARCHAR(20),
    reprocess_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Flujo de Persistencia

```python
# Tras agotar 3 reintentos
if self.request.retries >= self.max_retries:
    persist_failed_task(
        task_id=self.request.id,
        task_name=self.name,
        args=(batch_id,),
        kwargs={},
        exception=e,
        retries=self.request.retries
    )
```

### Consultas Útiles

```sql
-- Tareas fallidas recientes
SELECT * FROM get_recent_failed_tasks(10);

-- Estadísticas por tipo de tarea (últimos 7 días)
SELECT * FROM get_task_failure_stats(7);

-- Marcar para reprocesamiento
SELECT mark_task_for_reprocessing('task-uuid', 'Reintentar tras fix de BD');
```

---

## 🚀 Deployment y Operación

### Levantar Servicios

```bash
# 1. Levantar todos los servicios
docker-compose up -d

# 2. Verificar estado
docker-compose ps

# Resultado esperado:
# brasaland-backend      Up       0.0.0.0:8000->8000/tcp
# brasaland-redis        Up       0.0.0.0:6379->6379/tcp
# brasaland-celery-worker Up
# brasaland-flower       Up       0.0.0.0:5555->5555/tcp
```

---

### Verificar Conectividad

```bash
# Redis
docker exec brasaland-redis redis-cli ping
# Resultado: PONG

# Celery worker logs
docker logs brasaland-celery-worker --tail 50
# Buscar: "celery@hostname ready"

# Flower UI
curl http://localhost:5555
# O abrir en navegador: http://localhost:5555
```

---

### Comandos de Worker

```bash
# Ver workers activos
celery -A app.celery_app.celery_app inspect active

# Ver tareas registradas
celery -A app.celery_app.celery_app inspect registered

# Ver cola de tareas
celery -A app.celery_app.celery_app inspect scheduled

# Purgar cola (CUIDADO: elimina todas las tareas pendientes)
celery -A app.celery_app.celery_app purge
```

---

### Escalar Workers

```bash
# Aumentar concurrency a 8 workers
docker-compose up -d --scale celery-worker=2

# O modificar docker-compose.yml:
# command: celery -A app.celery_app.celery_app worker --loglevel=info --concurrency=8
```

---

## 🧪 Testing Manual

### Test 1: Encolar Tarea

```bash
# 1. Encolar procesamiento de lote
curl -X POST http://localhost:8000/tasks/telemetry/batch \
  -H "Content-Type: application/json" \
  -d '{"batch_id": 123}'

# Respuesta:
# {
#   "task_id": "a1b2c3d4-...",
#   "status": "pending",
#   "message": "Lote 123 encolado..."
# }
```

---

### Test 2: Consultar Estado

```bash
# Guardar task_id de respuesta anterior
TASK_ID="a1b2c3d4-e5f6-7890-abcd-ef1234567890"

# Polling cada 2 segundos
watch -n 2 "curl -s http://localhost:8000/tasks/$TASK_ID | jq"

# Estados observados:
# 1. "pending" - Encolado, esperando worker
# 2. "started" - Worker procesando
# 3. "success" - Completado (campo result disponible)
```

---

### Test 3: Monitoreo en Flower

```bash
# Abrir Flower
open http://localhost:5555

# O en Linux:
xdg-open http://localhost:5555
```

**Verificar**:
- [ ] Workers activos (mínimo 1)
- [ ] Tareas completadas (> 0)
- [ ] Gráfico de throughput
- [ ] Logs de última tarea

---

### Test 4: Forzar Fallo (DLQ)

```bash
# Encolar tarea con batch_id inexistente
curl -X POST http://localhost:8000/tasks/telemetry/batch \
  -H "Content-Type: application/json" \
  -d '{"batch_id": 999999}'

# Esperar 3 reintentos (~7 minutos total)
# 60s + 120s + 240s = 420 segundos = 7 minutos

# Verificar persistencia en DLQ
docker exec -it brasaland-postgres psql -U postgres -d postgres
```

```sql
-- Consultar tareas fallidas
SELECT * FROM failed_tasks ORDER BY failed_at DESC LIMIT 5;
```

---

## 📊 Observabilidad y Logs

### Logs de Worker

```bash
# Logs en tiempo real
docker logs -f brasaland-celery-worker

# Última tarea procesada
docker logs brasaland-celery-worker 2>&1 | grep "Task.*succeeded"
```

**Eventos clave**:
- `🚀 Iniciando procesamiento de lote...`
- `✅ Lote X procesado exitosamente`
- `❌ Error procesando lote X | Intento: 2/3`
- `❌ DLQ: Tarea X persistida tras 3 intentos`

---

### Monitoreo de Redis

```bash
# Conectar a Redis
docker exec -it brasaland-redis redis-cli

# Ver claves activas
KEYS *celery*

# Ver tamaño de cola
LLEN celery

# Ver tareas en cola (primeras 10)
LRANGE celery 0 9

# Estadísticas de memoria
INFO memory
```

---

### Métricas de Flower

**Dashboard Principal**:
- **Workers**: Número activo / total
- **Tasks**: Succeeded / Failed / Retried / Active
- **Throughput**: Tareas/minuto

**Gráficos**:
- Task completion over time
- Task duration distribution
- Worker CPU/memory usage

---

## 🛡️ Características de Resiliencia

### 1. Mensajes Ligeros

❌ **Incorrecto** (payload pesado):
```python
# NO enviar datos completos
task.delay(events=[...1500 eventos...])  # 2MB en Redis
```

✅ **Correcto** (solo ID):
```python
# Solo enviar ID, worker carga datos
task.delay(batch_id=123)  # <100 bytes en Redis
```

---

### 2. ACK Tras Éxito

**Configuración**:
```python
task_acks_late=True  # ACK solo tras completar
task_reject_on_worker_lost=True  # Re-encolar si worker muere
```

**Resultado**: Si worker crashea, Redis no marca mensaje como procesado → otro worker lo retoma.

---

### 3. Reintentos con Backoff Exponencial

```python
@celery_app.task(
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,        # Exponencial: 60s, 120s, 240s
    retry_backoff_max=600,     # Máximo 10 min entre intentos
    retry_jitter=True          # +/- 10% aleatorio
)
```

**Timeline**:
- T+0s: Intento 1 (falla)
- T+60s: Intento 2 (falla)
- T+180s: Intento 3 (falla)
- T+420s: Intento 4 (falla)
- T+420s: Persiste en DLQ

---

### 4. Timeouts Obligatorios

```python
task_time_limit=1800        # 30 min hard limit (kill forzoso)
task_soft_time_limit=1620   # 27 min soft limit (raise SoftTimeLimitExceeded)
```

**Comportamiento**:
- A los 27 min: Worker lanza excepción `SoftTimeLimitExceeded` (permite cleanup)
- A los 30 min: Worker es terminado forzosamente (SIGKILL)

---

### 5. Aislamiento de Procesos

**Arquitectura**:
- **FastAPI**: Proceso 1 (PID 100)
- **Celery Worker**: Proceso 2 (PID 200)
- **Flower**: Proceso 3 (PID 300)

**Prueba de Aislamiento**:
```bash
# 1. Encolar tarea de larga duración
curl -X POST http://localhost:8000/tasks/telemetry/batch -d '{"batch_id": 123}'

# 2. Detener FastAPI
docker stop brasaland-backend

# 3. Worker sigue procesando
docker logs -f brasaland-celery-worker
# Output: "✅ Lote 123 procesado exitosamente"

# 4. Reiniciar FastAPI
docker start brasaland-backend

# 5. Consultar resultado (sigue disponible en Redis)
curl http://localhost:8000/tasks/$TASK_ID
```

---

## 🔧 Troubleshooting

### Problema: Worker no se conecta a Redis

**Síntoma**:
```
[ERROR] Cannot connect to redis://redis:6379/0
```

**Solución**:
```bash
# Verificar healthcheck de Redis
docker-compose ps redis

# Debe mostrar: (healthy)
# Si muestra (unhealthy) o (starting):
docker-compose restart redis
```

---

### Problema: Tareas no se procesan (quedan en pending)

**Síntoma**: Estado siempre "pending", nunca pasa a "started"

**Diagnóstico**:
```bash
# Ver si worker está activo
docker logs brasaland-celery-worker | grep "ready"

# Ver cola de tareas
docker exec brasaland-redis redis-cli LLEN celery
```

**Solución**:
```bash
# Reiniciar worker
docker-compose restart celery-worker

# Escalar workers
docker-compose up -d --scale celery-worker=2
```

---

### Problema: Resultados caducados (404 tras 1 hora)

**Síntoma**: `GET /tasks/{task_id}` retorna null después de 1 hora

**Razón**: Configuración `result_expires=3600` (1 hora)

**Solución**:
```python
# celery_app.py
result_expires=86400  # Cambiar a 24 horas
```

---

## 📚 Referencias

- **Celery Docs**: https://docs.celeryq.dev/
- **Flower Docs**: https://flower.readthedocs.io/
- **Redis Docs**: https://redis.io/docs/
- **FastAPI Background Tasks**: https://fastapi.tiangolo.com/tutorial/background-tasks/

---

**Implementación completada por**: Claude Sonnet 4.5  
**Fecha**: 30 de Octubre, 2026  
**Estado**: ✅ **LISTO PARA TESTING Y DEPLOYMENT**
