# Sistemas Técnicos de Brasaland Digital

## Stack Tecnológico Actual

### Frontend
- **Framework**: Next.js 15 (App Router)
- **Lenguaje**: TypeScript (strict mode)
- **Estilos**: Tailwind CSS
- **UI Components**: shadcn/ui
- **Estado**: React hooks + Context API
- **Modo**: Soporte light/dark theme

### Backend
- **Framework**: FastAPI (Python 3.9+)
- **Base de datos**: PostgreSQL (Supabase)
- **ORM**: SQLAlchemy
- **Async**: Celery + Redis
- **Validación**: Pydantic
- **API**: RESTful

### Infraestructura
- **Servicios Async**: Redis, Celery Worker, Flower
- **Containerización**: Docker Compose
- **Tareas programadas**: Cron
- **Telemetría**: Sistema de eventos en tiempo real

### Machine Learning
- **Framework**: scikit-learn
- **Análisis**: pandas, numpy
- **Visualización**: matplotlib, seaborn
- **Modelos**: Random Forest (predicción de ventas)

---

## Sistemas Implementados

### 1. Sistema de Análisis de Incidencias (ATS)
**Estado**: ✅ Completado (100%)

#### Componentes
- **CLI**: `scripts/analyze.py` - Análisis por línea de comandos
- **API**: `POST /analyze-csv` - Endpoint FastAPI
- **Frontend**: `/incidents` - Interfaz web con drag-and-drop

#### Funcionalidades
- Carga de CSV con incidencias
- Clasificación de severidad (alta, media, baja)
- Detección de categorías (técnico, servicio, logística, RRHH)
- Análisis temporal con visualización
- Exportación de resultados
- Soporte multiidioma (español/inglés)

#### Métricas Calculadas
- Total de incidencias
- Distribución por severidad
- Categorías más frecuentes
- Tendencias temporales
- Días con mayor actividad

---

### 2. Sistema de Exportación Nocturna (Nightly Export)
**Estado**: ✅ Completado (Ticket #DEV-53)

#### Características
- **Lock distribuido**: Control de ejecución única sin Redis
- **Idempotencia**: Garantizada por fecha objetivo
- **Exportación CSV**: Backup en `data/raw/`
- **Pipeline subprocess**: Ejecución independiente
- **Tabla de control**: `job_runs` con estados (pending, processing, completed, failed)

#### Flujo
```
1. Cron trigger (2:00 AM)
2. Verificar idempotencia (fecha ya procesada?)
3. Crear job_run en estado "processing" (activa lock)
4. Exportar telemetry a CSV
5. Ejecutar pipeline como subprocess
6. Actualizar job_run a "completed" o "failed"
```

#### Comandos
```bash
# Ejecución manual
python scripts/nightly_export.py

# Ejecución con fecha específica
TARGET_DATE=2024-10-15 python scripts/nightly_export.py

# Dry run (sin ejecución real)
DRY_RUN=true python scripts/nightly_export.py
```

---

### 3. Sistema de Tareas Asíncronas (Celery + Redis)
**Estado**: ✅ Completado (Ticket #DEV-55)

#### Arquitectura
- **Broker**: Redis (mensajes entre API y workers)
- **Workers**: Procesos independientes (no dentro de FastAPI)
- **Monitoring**: Flower UI (puerto 5555)
- **Dead Letter Queue**: Tabla `failed_tasks` para reintentos fallidos

#### Características
- Desacoplamiento total (<200ms respuesta)
- Reintentos con exponential backoff
- 3 reintentos máximo
- Timeout 30 minutos por tarea
- Mensajes ligeros (solo IDs, no payloads)

#### Endpoints
```
POST /tasks/telemetry/batch
Body: {"batch_id": 123}
Response: {"task_id": "abc-123", "status": "pending"}

GET /tasks/{task_id}
Response: {
  "task_id": "abc-123",
  "status": "SUCCESS",
  "result": {...}
}
```

#### Servicios Docker
```bash
# Levantar servicios
docker-compose up -d redis celery-worker flower

# Monitoreo Flower
open http://localhost:5555
```

---

### 4. Modelo de Predicción de Ventas (ML Forecasting)
**Estado**: ✅ Completado

#### Características
- **Algoritmo**: Random Forest
- **Split temporal**: 8 años entrenamiento / 2 años test
- **Validación**: TimeSeriesSplit (5 folds)
- **Sin data leakage**: Validado con 8 tests unitarios

#### Métricas Implementadas
1. **MSE** (Mean Squared Error)
2. **RMSE** (Root Mean Squared Error)
3. **MAPE** (Mean Absolute Percentage Error)
4. **R²** (Coeficiente de determinación)
5. **PSI** (Population Stability Index - drift detection)
6. **Gini** (Poder discriminatorio)
7. **K2** (Estabilidad predictiva)

#### Outputs
- `results/sales_forecast_plot.png` - Predicciones con intervalos de confianza
- `results/feature_importance.png` - Variables más importantes
- `results/forecast_metrics.csv` - Métricas consolidadas

#### Ejecución
```bash
# Ejecutar modelo
python models/sales_forecast.py

# Ver resultados
cat results/forecast_metrics.csv
```

---

### 5. Sistema de Evaluación de Modelos ML
**Estado**: ✅ Completado

#### Validaciones
- **Learning curves**: Diagnóstico sesgo/varianza
- **Cross-validation**: TimeSeriesSplit 5 folds con μ ± σ
- **Diagnóstico automático**: Overfitting, Underfitting, Bien Ajustado
- **Plan correctivo**: Acciones específicas según diagnóstico

#### Criterios de Diagnóstico
```
Gap > 30% → OVERFITTING
  Acción: Reducir max_depth, aumentar min_samples_split

Ambos errores > 5M COP → UNDERFITTING
  Acción: Aumentar max_depth, agregar features

Gap < 20% y errores < 5M → BIEN AJUSTADO
  Acción: Monitorear PSI, reentrenar trimestralmente
```

#### Outputs
- `data/eval/learning_curve.png` - Curvas con diagnóstico visual
- `data/eval/evaluation_report.md` - Reporte técnico completo
- `data/eval/evaluation_metrics.csv` - Métricas tabulares

---

## Arquitectura de Datos

### Base de Datos (PostgreSQL)

#### Tabla: `telemetry_events`
Eventos de telemetría en tiempo real desde locales.

```sql
CREATE TABLE telemetry_events (
  id BIGSERIAL PRIMARY KEY,
  location_id INT NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  event_data JSONB,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### Tabla: `job_runs`
Control de ejecución de jobs nocturnos.

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
  UNIQUE (job_name, target_date)
);
```

#### Tabla: `failed_tasks`
Dead Letter Queue para tareas fallidas de Celery.

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
  failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## API Endpoints

### Incidencias
```
POST /analyze-csv
  Multipart: file (CSV)
  Response: {
    "total_incidents": 42,
    "by_severity": {...},
    "by_category": {...},
    "temporal_analysis": {...}
  }
```

### Tareas Asíncronas
```
POST /tasks/telemetry/batch
  Body: {"batch_id": 123}
  Response: {"task_id": "...", "status": "pending"}

GET /tasks/{task_id}
  Response: {"task_id": "...", "status": "SUCCESS", "result": {...}}
```

### Health Check
```
GET /health
  Response: {"status": "healthy", "timestamp": "..."}
```

---

## Paleta de Colores (Brand Identity)

### Colores Principales
```typescript
primary: {
  DEFAULT: '#FF6B35',  // Naranja brasa
  light: '#FF8A5C',
  dark: '#E85A2A'
}

secondary: {
  DEFAULT: '#2C3E50',  // Gris oscuro
  light: '#34495E',
  dark: '#1A252F'
}
```

### Colores de Severidad (Incidencias)
```typescript
severity: {
  high: '#DC2626',     // Rojo
  medium: '#F59E0B',   // Ámbar
  low: '#10B981'       // Verde
}
```

### Colores Neutrales
```typescript
neutral: {
  50: '#FAFAFA',
  100: '#F5F5F5',
  ...
  900: '#171717'
}
```

---

## Patrones de Diseño

### Frontend

#### Componentes Reutilizables
- `Button` - Botón con variantes (primary, secondary, outline)
- `Card` - Contenedor con sombra y padding
- `Input` - Campo de texto con validación
- `FileUploader` - Drag-and-drop para archivos

#### Hooks Personalizados
- `useTheme()` - Gestión de modo claro/oscuro
- `useLocalStorage()` - Persistencia en navegador

### Backend

#### Patrones Async
- **Productor/Consumidor**: FastAPI produce, Celery consume
- **Mensajes ligeros**: Solo IDs, payload se recupera de DB
- **Idempotencia**: Verificación antes de procesamiento

#### Error Handling
- Try-catch en endpoints
- Logging estructurado
- Códigos HTTP semánticos (200, 202, 400, 500)

---

## Testing

### Frontend
```bash
cd uis/backoffice
npm run lint        # ESLint
npm run type-check  # TypeScript
```

### Backend
```bash
cd services/api
source venv/bin/activate
pytest              # Tests unitarios
```

### ML
```bash
pytest tests/pipelines/test_sales_split.py -v
pytest tests/pipelines/test_time_series_split.py -v
```

---

## Deployment

### Local Development
```bash
# Backend
cd services/api
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000

# Frontend
cd uis/backoffice
npm run dev  # Puerto 3000

# Servicios Async
docker-compose up -d redis celery-worker flower
```

### Production Checklist
- [ ] Variables de entorno configuradas
- [ ] Migraciones de BD ejecutadas
- [ ] Celery workers activos
- [ ] Cron job configurado (nightly export)
- [ ] Flower protegido con autenticación
- [ ] HTTPS habilitado
- [ ] Logs centralizados

---

## Métricas de Código

### Líneas de Código Implementadas
- **Python**: 1,460 líneas (backend + ML)
- **SQL**: 353 líneas (migraciones)
- **Tests**: 350 líneas (validación)
- **TypeScript**: ~1,200 líneas (frontend)
- **Total**: ~3,363 líneas

### Archivos Creados
- Scripts Python: 4
- Migraciones SQL: 2
- Tests unitarios: 2 suites (18 tests)
- Documentación Markdown: 10+
- Configuración: 3 (docker-compose, requirements)

---

## Próximos Sistemas (Roadmap)

1. **Dashboard Ejecutivo**
   - Ventas en tiempo real (COP/USD)
   - Métricas por local
   - Comparativas entre países

2. **App de Fidelización**
   - Brasa Points digital
   - Historial de pedidos
   - Ofertas personalizadas

3. **Portal de RRHH**
   - Solicitudes de vacaciones
   - Onboarding automatizado
   - Dashboard de métricas

4. **Plataforma de Formación**
   - Catálogo de recetas
   - Videos de capacitación
   - Tracking de completitud

5. **Sistema de Compras**
   - Gestión de proveedores
   - Historial de precios
   - Pedidos automatizados

---

## Documentación Adicional

Para información detallada sobre cada sistema, consultar:
- `/memory-bank/progress.md` - Estado de proyectos
- `/memory-bank/techContext.md` - Contexto técnico detallado
- `/docs/INCIDENTS_SYSTEM_GUIDE.md` - Sistema de incidencias
- `/NIGHTLY_EXPORT_SYSTEM.md` - Sistema de exportación
- `/CELERY_ASYNC_TASKS_SYSTEM.md` - Sistema de tareas async
