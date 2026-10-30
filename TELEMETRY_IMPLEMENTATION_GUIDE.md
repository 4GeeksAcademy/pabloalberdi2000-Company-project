# 📊 Guía de Implementación de Telemetría End-to-End

**Versión**: 1.0.0  
**Fecha**: 30 de octubre, 2026  
**Autor**: Claude Sonnet 4.5 (Lead Software Architect & Observability Specialist)

---

## 📋 Resumen Ejecutivo

Sistema de telemetría completo implementado según el estándar **Event Envelope** aprobado en `TELEMETRY_PLAN.md` y validado en `TELEMETRY_AUDIT_REPORT.md`.

**Estado**: ✅ **MVP Completado** (Fase 1 - Stub sin persistencia)

**Componentes entregados**:
1. ✅ **Backend**: Router FastAPI `/telemetry/events` con validación Pydantic
2. ✅ **Frontend**: `TelemetryService` con batching, retries y sendBeacon
3. ✅ **Instrumentación**: Error Boundaries, hooks de navegación/auth, Web Vitals
4. ✅ **Ejemplos**: Login, inventario, layout integrado

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Components                                         │   │
│  │  - Page views                                       │   │
│  │  - Auth events                                      │   │
│  │  - Inventory actions                                │   │
│  │  - Error Boundaries                                 │   │
│  └────────────────┬────────────────────────────────────┘   │
│                   │                                         │
│                   │ track(event_type, properties)          │
│                   ▼                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  TelemetryService (Singleton)                       │   │
│  │  - Enriquecimiento automático (eventId, timestamp)  │   │
│  │  - Cola en memoria (batch: 20 eventos / 10s)       │   │
│  │  - Reintentos con backoff exponencial (3x)         │   │
│  │  - sendBeacon al ocultar/cerrar pestaña            │   │
│  └────────────────┬────────────────────────────────────┘   │
│                   │                                         │
│                   │ POST /telemetry/events                  │
│                   │ {events: [{Event Envelope}, ...]}      │
└───────────────────┼─────────────────────────────────────────┘
                    │
                    │ HTTP (JSON)
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  POST /telemetry/events                             │   │
│  │  - Validación Pydantic (Event Envelope)            │   │
│  │  - Logging agregado (event_type counts)            │   │
│  │  - Respuesta: {received: N, status: "success"}     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  MVP: Stub (no persistencia)                               │
│  Fase 2: PostgreSQL JSONB + Kafka/S3                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 Archivos Creados

### Backend (`services/api/`)

```
app/
├── schemas/
│   └── telemetry.py                  # Pydantic models (Event Envelope)
├── routers/
│   └── telemetry.py                  # Router /telemetry con POST /events
└── main.py                           # [MODIFICADO] Registrar router
```

### Frontend (`uis/backoffice/`)

```
lib/
├── telemetry.ts                      # TelemetryService (singleton)
├── telemetry-hooks.ts                # Hooks (auth, navigation, performance)
└── telemetry-inventory.ts            # Domain events (inventario)

components/
├── ErrorBoundary.tsx                 # Error Boundary con tracking
└── TelemetryProvider.tsx             # Wrapper global (page views + errors)

app/
├── layout-with-telemetry.example.tsx # Ejemplo de layout integrado
└── .env.example                      # Config NEXT_PUBLIC_TELEMETRY_ENDPOINT

examples/
└── login-with-telemetry.example.tsx  # Ejemplo de auth tracking
```

---

## 🚀 Setup y Testing

### 1. Backend Setup

```bash
cd services/api

# Activar venv
source venv/bin/activate

# El router ya está registrado en main.py, no requiere cambios

# Iniciar servidor
python -m uvicorn app.main:app --reload --port 8000
```

**Verificar**:
```bash
# Health check
curl http://localhost:8000/telemetry/health

# Respuesta esperada:
{
  "status": "healthy",
  "service": "telemetry-ingestion",
  "version": "1.0.0-stub",
  "mode": "MVP (no persistence)"
}
```

---

### 2. Frontend Setup

```bash
cd uis/backoffice

# Crear .env.local con endpoint de telemetría
echo "NEXT_PUBLIC_TELEMETRY_ENDPOINT=http://localhost:8000/telemetry/events" > .env.local

# Instalar dependencias (si no están)
npm install

# Iniciar dev server
npm run dev
```

---

### 3. Test Manual End-to-End

#### **Test 1: Envío Manual de Evento**

Abre la consola del navegador en `http://localhost:3000` y ejecuta:

```javascript
// Importar telemetry service
const { track } = await import('./lib/telemetry');

// Enviar evento de prueba
track('page_view', {
  page_name: 'test_manual',
  referrer: 'https://google.com',
  viewport_width: 1920,
  viewport_height: 1080
});

// Esperar 10 segundos para que el batch se envíe automáticamente
// O ejecutar 20 veces para trigger inmediato
```

**Verificar en logs del backend** (terminal de FastAPI):
```
INFO:     📊 Telemetry batch received: 1 events | Types: {'page_view': 1}
```

---

#### **Test 2: Error Boundary**

Crea un componente que lance un error:

```tsx
// En cualquier página
export default function TestErrorPage() {
  throw new Error("Test error boundary");
  return <div>Never reached</div>;
}
```

**Resultado esperado**:
1. UI muestra fallback de ErrorBoundary ("Algo salió mal")
2. Evento `frontend_error_uncaught` enviado a backend
3. Logs del backend: `{'frontend_error_uncaught': 1}`

---

#### **Test 3: Page View Tracking**

1. Integra `TelemetryProvider` en layout:

```tsx
// Copiar app/layout-with-telemetry.example.tsx a app/layout.tsx
```

2. Navega entre páginas:
   - `/` → `/inventory` → `/incidents`

**Verificar en logs del backend**:
```
📊 Telemetry batch received: 3 events | Types: {'page_view': 3}
```

---

#### **Test 4: Batching y Flush**

```javascript
// Consola del navegador
const { track } = await import('./lib/telemetry');

// Enviar 25 eventos (excede batchSize=20)
for (let i = 0; i < 25; i++) {
  track('test_event', { iteration: i });
}

// Resultado esperado:
// - Primer batch: 20 eventos (flush automático al alcanzar batchSize)
// - Segundo batch: 5 eventos (flush después de 10 segundos)
```

**Logs del backend**:
```
📊 Telemetry batch received: 20 events | Types: {'test_event': 20}
📊 Telemetry batch received: 5 events | Types: {'test_event': 5}
```

---

#### **Test 5: sendBeacon (Flush al cerrar pestaña)**

1. Abrir página en navegador
2. Enviar evento en consola:
   ```javascript
   const { track } = await import('./lib/telemetry');
   track('test_beacon', { before_close: true });
   ```
3. **Cerrar pestaña inmediatamente** (antes de 10s)

**Resultado esperado**:
- Evento se envía vía `navigator.sendBeacon` (no se pierde)
- Logs del backend: `{'test_beacon': 1}`

---

#### **Test 6: Reintentos con Backoff**

1. **Apagar el backend** (Ctrl+C en terminal de FastAPI)
2. Enviar evento desde frontend:
   ```javascript
   const { track } = await import('./lib/telemetry');
   track('test_retry', { backend_down: true });
   ```
3. **Observar en consola del navegador**:
   ```
   ❌ Telemetry send failed (attempt 1/3): TypeError: Failed to fetch
   ⏳ Retrying in 1000ms...
   ❌ Telemetry send failed (attempt 2/3): TypeError: Failed to fetch
   ⏳ Retrying in 2000ms...
   ❌ Telemetry send failed (attempt 3/3): TypeError: Failed to fetch
   ⚠️ Telemetry batch discarded after 3 attempts
   ```
4. **Reiniciar backend**
5. Enviar nuevo evento → debería enviarse correctamente

---

## 📊 Eventos Implementados (Ejemplos)

### **Eventos Obligatorios del Dominio (Inventario)**

| Evento | Archivo Helper | Función |
|--------|----------------|---------|
| `direct_stock_edit_rejected` | `telemetry-inventory.ts` | `trackDirectStockEditRejected()` |
| `outbound_stock_insufficient` | `telemetry-inventory.ts` | `trackOutboundStockInsufficient()` |
| `stock_threshold_triggered` | `telemetry-inventory.ts` | `trackStockThresholdTriggered()` |
| `stock_calculation_latency` | `telemetry-inventory.ts` | `trackStockCalculationLatency()` |
| `ingredient_viewed_critical_stock` | `telemetry-inventory.ts` | `trackIngredientViewedCriticalStock()` |
| `inbound_order_created` | `telemetry-inventory.ts` | `trackInboundOrderCreated()` |
| `outbound_order_created` | `telemetry-inventory.ts` | `trackOutboundOrderCreated()` |

### **Eventos Técnicos Transversales**

| Evento | Archivo Helper | Función |
|--------|----------------|---------|
| `frontend_error_uncaught` | `ErrorBoundary.tsx` + `TelemetryProvider.tsx` | Automático |
| `page_view` | `telemetry-hooks.ts` | `usePageViewTracking()` (automático) |
| `login_attempt_failed` | `telemetry-hooks.ts` | `trackLoginFailed()` |
| `login_attempt_success` | `telemetry-hooks.ts` | `trackLoginSuccess()` |
| `session_expired` | `telemetry-hooks.ts` | `trackSessionExpired()` |
| `password_reset_requested` | `telemetry-hooks.ts` | `trackPasswordResetRequested()` |
| `api_request_failed` | `telemetry-hooks.ts` | `trackApiRequestFailed()` |
| `network_request_timeout` | `telemetry-hooks.ts` | `trackNetworkTimeout()` |
| `web_vital_recorded` | `telemetry-hooks.ts` | `trackWebVital()` |

---

## 🔒 Seguridad y Privacidad

### **Reglas Estrictas (NUNCA VIOLAR)**

1. ❌ **NUNCA loguear emails en claro** → Usar SHA256 hash
2. ❌ **NUNCA loguear passwords** → Ni siquiera hasheados
3. ❌ **NUNCA loguear IPs completas** → Enmascarar último octeto (`192.168.1.0`)
4. ❌ **NUNCA loguear tokens JWT** → Credenciales nunca deben ser capturadas
5. ❌ **NUNCA loguear stack traces sin sanitizar** → Remover paths locales (`/Users/...`)

### **Sanitización Implementada**

- **ErrorBoundary**: Stack traces sanitizados (regex para remover paths locales)
- **TelemetryProvider**: Global error handler con sanitización
- **Login**: Email hasheado con SHA256 (Web Crypto API)

### **PII Allowlist**

Campos sensibles identificados en `event-schemas.json`:
- `email_hash` → SHA256 hash (NOT email en claro)
- `ip_address_masked` → Último octeto enmascarado
- `error_stack` → Sanitizado (sin paths locales)
- `notes`, `reason` → Regex sanitization en backend (Fase 2)

---

## 📈 Roadmap: Fase 2 (Producción)

### **Backend**

1. ✅ **Persistencia**: PostgreSQL table `events` con JSONB column
   ```sql
   CREATE TABLE events (
     event_id UUID PRIMARY KEY,
     timestamp TIMESTAMPTZ NOT NULL,
     event_type VARCHAR(100) NOT NULL,
     user_id UUID,
     session_id VARCHAR(100),
     properties JSONB NOT NULL,
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   
   CREATE INDEX idx_events_type ON events(event_type);
   CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
   CREATE INDEX idx_events_user_id ON events(user_id);
   ```

2. ✅ **Validación contra `event-schemas.json`**:
   - Cargar schemas en memoria al iniciar servidor
   - Validar `properties` contra allowlist estricto (`additionalProperties: false`)
   - Rechazar eventos con campos no permitidos

3. ✅ **Sanitización de PII**:
   - Regex para detectar emails/teléfonos en `notes`/`reason`
   - Hash MD5 de SQL queries sin parámetros
   - Sanitización de stack traces

4. ✅ **Enrutamiento Stream vs Batch**:
   - **Stream** (7 eventos): Kafka topic `telemetry-stream`
   - **Batch** (12 eventos): S3 bucket `telemetry-batch/` (Parquet)

5. ✅ **Métricas de ingestion**:
   - Rate limiting: 1000 eventos/segundo por usuario
   - Timeout: 5 segundos máximo
   - Alerta si tasa de rechazo >5%

### **Frontend**

1. ✅ **Instrumentar eventos restantes** (19 eventos totales):
   - 7 eventos obligatorios de inventario ✅ (implementados)
   - 3 eventos de seguridad ✅ (implementados)
   - 3 eventos de performance (falta: `api_latency_recorded`, `database_query_slow`, `cache_hit_rate_measured`)
   - 2 eventos de reliability ✅ (implementados)
   - 3 eventos de UX ✅ (implementados)
   - 1 evento de network ✅ (implementado)

2. ✅ **Integración con hooks existentes**:
   - `useAuth()`: Track login/logout/session expiry
   - Inventory forms: Track `inbound_order_created`, `outbound_order_created`
   - API client: Track `api_request_failed`, `network_request_timeout`

3. ✅ **Sampling configurable**:
   - `page_view`: 10% (ya implementado)
   - `api_latency_recorded`: 20%
   - `stock_calculation_latency`: 25% (ya implementado)

4. ✅ **localStorage fallback**:
   - Guardar eventos fallidos en localStorage
   - Reintento en próxima sesión (opcional)

### **Dashboards**

1. ✅ **Dashboard de Salud de Inventario** (Grafana/Metabase):
   - Ingredientes con stock crítico (últimas 24h)
   - Tasa de rechazos de órdenes outbound (por almacén)
   - Tiempo promedio de respuesta a alertas
   - Predicción de desabasto (próximos 7 días)

2. ✅ **Dashboard de Performance Backend**:
   - P95 latencia API (por endpoint)
   - Tasa de errores 5xx (últimos 7 días)
   - Cache hit rate (últimas 48h)
   - Queries SQL lentas (>1s)

3. ✅ **Dashboard de Reliability**:
   - Errores frontend por página
   - Tasa de sesiones con error
   - Tiempo medio hasta el primer error

---

## 🎯 Criterios de Éxito (MVP)

### **Backend**

- ✅ Endpoint `/telemetry/events` funcional
- ✅ Validación Pydantic de Event Envelope
- ✅ Logging agregado (event_type counts)
- ✅ Respuesta HTTP 200 con `{received: N}`
- ✅ Health check endpoint

### **Frontend**

- ✅ `TelemetryService` singleton inicializado
- ✅ Cola en memoria con batching (20 eventos / 10s)
- ✅ Reintentos con backoff exponencial (3x)
- ✅ `sendBeacon` al ocultar/cerrar pestaña
- ✅ Enriquecimiento automático (eventId, timestamp, sessionId, userId)
- ✅ API única `track()` (NO fetch/axios dispersos)

### **Instrumentación**

- ✅ Error Boundary con tracking
- ✅ Global error handlers (`window.onerror`, `unhandledrejection`)
- ✅ Page view tracking automático
- ✅ Auth events (login success/failed, session expired)
- ✅ Inventory domain events (7 eventos obligatorios)
- ✅ Helpers organizados por dominio

### **Testing**

- ✅ Envío manual de eventos (consola navegador)
- ✅ Error Boundary triggering
- ✅ Page view tracking en navegación
- ✅ Batching (20 eventos)
- ✅ sendBeacon (cierre de pestaña)
- ✅ Reintentos con backend offline

---

## 📚 Referencias

- **Plan de Telemetría**: [`TELEMETRY_PLAN.md`](./TELEMETRY_PLAN.md) (1,242 líneas)
- **Schemas de Eventos**: [`event-schemas.json`](./event-schemas.json) (1,187 líneas)
- **Auditoría de Diseño**: [`TELEMETRY_AUDIT_REPORT.md`](./TELEMETRY_AUDIT_REPORT.md) (2,577 líneas)
- **Contexto de Negocio**: [`memory-bank/projectbrief.md`](./memory-bank/projectbrief.md)

---

## 🤝 Soporte

**Arquitecto responsable**: Nicolás Park (CTO Brasaland)  
**Documentación técnica**: Claude Sonnet 4.5  
**Fecha de entrega**: 30 de octubre, 2026

---

**Estado del Sistema**: 🟢 **MVP Operacional**  
**Siguiente paso**: Instrumentar eventos restantes en páginas de inventario y auth
