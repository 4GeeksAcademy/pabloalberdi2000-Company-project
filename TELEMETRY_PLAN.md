# 📊 PLAN DE TELEMETRÍA EMPRESARIAL - BRASALAND DIGITAL PLATFORM
## Event-Driven Architecture & Business Intelligence Strategy

**Fecha**: 30 de octubre, 2026  
**Arquitecto Principal**: Claude Sonnet 4.5 (Lead Data Architect & Distributed Systems Engineer)  
**Alcance**: Monorepo completo (FastAPI + Next.js 15 + Supabase + TinyDB)  
**Empresa**: Brasaland (14 restaurantes, 115 empleados, $6M anuales)

---

## 📋 RESUMEN EJECUTIVO

### Contexto del RFI

El equipo de gestión de Brasaland ha solicitado formalmente a tecnología un sistema de telemetría empresarial que proporcione **información de negocio accionable** sobre toda la plataforma digital. La empresa opera 14 restaurantes en dos países (Colombia y Florida), gestiona 115 empleados y factura $6M anuales, pero carece de visibilidad en tiempo real sobre:

- Operaciones de inventario y uso de materia prima
- Comportamiento de usuarios en el backoffice
- Salud técnica del sistema (performance, errores, downtime)
- Patrones de uso que permitan optimizar procesos operativos

Este documento establece la **arquitectura de eventos fundacional** para capturar, procesar y actuar sobre datos operacionales críticos.

---

### Principios Rectores

1. **Event-First Design**: Cada evento debe responder a una hipótesis de negocio específica
2. **Privacy by Design**: Datos sensibles (PII, credenciales) nunca en payloads sin anonimización
3. **Distributed Systems Reliability**: Correlación de eventos entre frontend, API y bases de datos
4. **Actionable Intelligence**: Métricas que permitan tomar decisiones concretas, no vanity metrics

---

### Arquitectura de Doble Base de Datos

**Stack actual**:
- **TinyDB**: Autenticación (users, profiles, reset_tokens, JWT sessions)
- **Supabase/PostgreSQL**: Datos operacionales (inventario, incidencias)

**Implicaciones para telemetría**:
- `user_uuid` es string (referencia lógica a TinyDB, sin FK relacional)
- Eventos deben correlacionar IDs entre sistemas sin romper aislamiento
- `sessionId` en frontend mapea a JWT token en backend

---

## 🎯 FASE 1: CATÁLOGO EXHAUSTIVO DE OPORTUNIDADES DE DATOS

---

### 1.1. Métricas Obligatorias del Dominio

#### Según `CONTEXT.md` y `projectbrief.md`

**Dirección Ejecutiva (Mariana Restrepo)**:
- Dashboard ejecutivo con ventas totales (USD/COP) → **FUTURO** (no aplica ahora)
- Asistente IA con queries en lenguaje natural → **FUTURO**
- Informe semanal automatizado (lunes 7am) → **FUTURO**

**Operaciones (Felipe Guerrero)**:
- Dashboard de ventas en tiempo real por local → **FUTURO**
- Sistema inteligente de pedidos basado en históricos → **APLICA AHORA** (inventario)
- Alertas cuando un local no registra ventas → **FUTURO**

**Compras (Lucía Fernández)**:
- Plataforma de gestión de proveedores → **FUTURO**
- Historial de precios y alertas → **FUTURO**

**Tecnología (Nicolás Park)**:
- **Telemetría en tiempo real** → ✅ **APLICA AHORA** (este documento)
- **Pipeline de datos para dashboards** → ✅ **APLICA AHORA**

**Conclusión**: El sistema actual (inventario + incidencias + ATS) es la **base operacional**. Las métricas obligatorias se enfocan en:
1. Gestión de inventario (ingredientes, órdenes inbound/outbound)
2. Salud técnica del sistema
3. Comportamiento de usuarios en backoffice

---

### 1.2. Mapeo del Flujo de Inventario (Mínimo 5 Puntos)

#### Flujo Completo: Desde Autenticación hasta Compleción de Órdenes

```
┌────────────────────────────────────────────────────────────────┐
│ JOURNEY DEL USUARIO EN GESTIÓN DE INVENTARIO                  │
└────────────────────────────────────────────────────────────────┘

1. [ENTRADA] → Usuario autentica (JWT) en backoffice
2. [NAVEGACIÓN] → Accede a /inventory/ingredients
3. [LECTURA] → Lista ingredientes con stock calculado
4. [ALERTA] → Sistema detecta stock bajo de ingrediente X
5. [ESCRITURA] → Registra orden de entrada (inbound)
6. [VALIDACIÓN CRÍTICA] → Intenta modificar stock directamente (RECHAZADO)
7. [ESCRITURA] → Registra orden de salida (outbound)
8. [VALIDACIÓN CRÍTICA] → Salida excede stock disponible (RECHAZADO)
9. [ÉXITO] → Stock actualizado correctamente
10. [SALIDA] → Sesión expira o logout
```

#### Eventos de Instrumentación Obligatorios

##### 📍 **Punto 1: Intentos de Modificación Directa de Stock (Rechazos)**

**Evento**: `direct_stock_edit_rejected`

**Regla de Oro**:
> *Capturamos `direct_stock_edit_rejected` porque necesitamos **detectar intentos de bypassing del flujo de órdenes** (inbound/outbound), lo que nos permite **identificar usuarios que no comprenden el modelo de negocio** y diseñar mejor onboarding o prevenir fraude interno.*

**Clasificación**: 🔴 **Obligatorio** (Seguridad + Educación de usuarios)

**Hipótesis**: Si un usuario intenta editar stock directamente en lugar de usar órdenes, indica:
- Falta de formación en el flujo correcto
- Intento de manipular stock (fraude)
- UX confusa que sugiere edición directa

**Decisión concreta**: Disparar entrenamiento adicional a usuarios con >3 rechazos en 7 días, auditoría de seguridad si >10 rechazos.

---

##### 📍 **Punto 2: Validaciones Fallidas de Stock Negativo**

**Evento**: `outbound_stock_insufficient`

**Regla de Oro**:
> *Capturamos `outbound_stock_insufficient` porque necesitamos **identificar desajustes entre stock registrado y stock real físico**, lo que nos permite **detectar errores de registro previos, mermas no reportadas o problemas de sincronización entre almacenes**.*

**Clasificación**: 🔴 **Obligatorio** (Integridad de datos)

**Hipótesis**: Si una orden de salida falla por stock insuficiente, indica:
- Órdenes de entrada no registradas correctamente
- Consumo real > consumo registrado (mermas no documentadas)
- Problema de concurrencia (2 usuarios intentan usar mismo stock)

**Decisión concreta**: Enviar alerta al supervisor del almacén para auditoría física, investigar últimas 10 órdenes del ingrediente.

---

##### 📍 **Punto 3: Activación de Umbral de Stock Mínimo**

**Evento**: `stock_threshold_triggered`

**Regla de Oro**:
> *Capturamos `stock_threshold_triggered` porque necesitamos **alertar proactivamente antes de quedarnos sin materia prima crítica**, lo que nos permite **generar órdenes de compra automáticas o alertas a proveedores** antes de impactar operaciones de restaurante.*

**Clasificación**: 🔴 **Obligatorio** (Continuidad operacional)

**Hipótesis**: Cuando `current_stock < min_stock`, el ingrediente está en riesgo de agotarse en 24-48h según consumo histórico.

**Decisión concreta**: Notificación push a área de Compras (Lucía Fernández), generación automática de borrador de orden de compra basada en `reorder_point`.

---

##### 📍 **Punto 4: Tiempo de Respuesta de Cálculo de Stock**

**Evento**: `stock_calculation_latency`

**Regla de Oro**:
> *Capturamos `stock_calculation_latency` porque necesitamos **monitorear el performance de la operación más costosa del sistema** (SUM(inbound) - SUM(outbound)), lo que nos permite **optimizar queries SQL o agregar caché** antes de que la latencia afecte UX.*

**Clasificación**: 🟡 **Oportunidad Identificada** (Performance Engineering)

**Hipótesis**: Si el cálculo de stock tarda >500ms, la experiencia de usuario se degrada en la vista de ingredientes con paginación.

**Decisión concreta**: Si latencia p95 > 500ms durante 1 hora, activar investigación de query optimization o considerar desnormalización con caché.

---

##### 📍 **Punto 5: Creación Exitosa de Órdenes**

**Evento**: `inbound_order_created` / `outbound_order_created`

**Regla de Oro**:
> *Capturamos `inbound_order_created` y `outbound_order_created` porque necesitamos **rastrear flujo completo de materia prima** (entrada → uso → reorden), lo que nos permite **construir modelo predictivo de demanda** y optimizar niveles de inventario.*

**Clasificación**: 🔴 **Obligatorio** (Operaciones + ML futuro)

**Hipótesis**: Patrones de consumo (outbound) por almacén y día de semana permiten predecir necesidades de inbound con 85%+ precisión.

**Decisión concreta**: Alimentar sistema de predicción de demanda, generar recomendaciones de compra semanales.

---

##### 📍 **Punto 6: Acceso a Ingrediente con Stock Crítico**

**Evento**: `ingredient_viewed_critical_stock`

**Regla de Oro**:
> *Capturamos `ingredient_viewed_critical_stock` porque necesitamos **confirmar que operadores están viendo alertas de stock bajo**, lo que nos permite **medir efectividad de notificaciones** y ajustar UI para priorizar ingredientes críticos.*

**Clasificación**: 🟡 **Oportunidad Identificada** (UX + Alertas)

**Hipótesis**: Si ingrediente con stock crítico no se visualiza en 24h post-alerta, las notificaciones no están siendo atendidas.

**Decisión concreta**: Escalar alerta a supervisor si ingrediente crítico no es visualizado en 24h.

---

### 1.3. Exploración Multicategoría del Backoffice

#### 🔐 **Categoría 1: Autenticación y Seguridad**

##### Evento 7: `login_attempt_failed`

**Regla de Oro**:
> *Capturamos `login_attempt_failed` porque necesitamos **detectar ataques de fuerza bruta o credenciales comprometidas**, lo que nos permite **bloquear IPs maliciosas** o forzar reset de password en cuentas bajo ataque.*

**Clasificación**: 🔴 **Obligatorio** (Seguridad)

**Hipótesis**: >5 intentos fallidos desde misma IP en 10 minutos = ataque automatizado.

**Decisión concreta**: Implementar rate limiting temporal (5 min lockout), notificar al usuario si >3 intentos desde IP desconocida.

---

##### Evento 8: `session_expired`

**Regla de Oro**:
> *Capturamos `session_expired` porque necesitamos **entender si TTL de sesión (default 15-30min) es adecuado para flujos de trabajo reales**, lo que nos permite **ajustar timeout sin comprometer seguridad**.*

**Clasificación**: 🟡 **Oportunidad Identificada** (UX + Seguridad)

**Hipótesis**: Si >30% de sesiones expiran con usuario activo (clicks en ventana), el TTL es muy corto.

**Decisión concreta**: Si tasa de expiración activa >30%, extender TTL a 45min con refresh automático.

---

##### Evento 9: `password_reset_requested`

**Regla de Oro**:
> *Capturamos `password_reset_requested` porque necesitamos **detectar picos anómalos de resets** (posible phishing masivo), lo que nos permite **alertar al equipo de seguridad**.*

**Clasificación**: 🟡 **Oportunidad Identificada** (Seguridad)

**Hipótesis**: >10 resets en 1 hora sin correlación con cambio de políticas = campaña de phishing.

**Decisión concreta**: Notificación al CTO (Nicolás Park) si pico >3σ de media histórica.

---

#### ⚡ **Categoría 2: Rendimiento y Salud del Sistema**

##### Evento 10: `api_latency_recorded`

**Regla de Oro**:
> *Capturamos `api_latency_recorded` porque necesitamos **monitorear degradación de performance en tiempo real**, lo que nos permite **identificar endpoints lentos antes de que afecten a usuarios**.*

**Clasificación**: 🔴 **Obligatorio** (Performance Engineering)

**Hipótesis**: Si latencia p95 de endpoint crítico aumenta >50% en 1 hora, hay problema de infraestructura o query.

**Decisión concreta**: Alerta a tecnología si p95 >200ms para endpoints con caché, >500ms para endpoints sin caché.

---

##### Evento 11: `database_query_slow`

**Regla de Oro**:
> *Capturamos `database_query_slow` porque necesitamos **identificar queries N+1 o missing indexes**, lo que nos permite **optimizar esquema de BD antes de que escale el problema**.*

**Clasificación**: 🟡 **Oportunidad Identificada** (Database Optimization)

**Hipótesis**: Query >1 segundo indica falta de índice o full table scan en Supabase.

**Decisión concreta**: Logging de query SQL + explain plan, revisión semanal de queries lentas.

---

##### Evento 12: `cache_hit_rate_measured`

**Regla de Oro**:
> *Capturamos `cache_hit_rate_measured` porque necesitamos **validar efectividad de estrategia de caching** (ver CACHING_REPORT.md), lo que nos permite **ajustar TTLs o identificar cache invalidation bugs**.*

**Clasificación**: 🟡 **Oportunidad Identificada** (Performance)

**Hipótesis**: Hit rate <50% indica TTL muy corto o patrón de acceso muy disperso.

**Decisión concreta**: Si hit rate <50% durante 48h, revisar TTLs y patrones de invalidación.

---

#### 🚨 **Categoría 3: Errores y Excepciones**

##### Evento 13: `frontend_error_uncaught`

**Regla de Oro**:
> *Capturamos `frontend_error_uncaught` porque necesitamos **detectar bugs en producción que QA no identificó**, lo que nos permite **priorizar fixes basado en frecuencia y usuarios afectados**.*

**Clasificación**: 🔴 **Obligatorio** (Reliability)

**Hipótesis**: Error recurrente (>10 ocurrencias en 1h) indica bug sistemático vs. caso edge.

**Decisión concreta**: Crear ticket automático en issue tracker si mismo error ocurre >10 veces/hora.

---

##### Evento 14: `api_request_failed`

**Regla de Oro**:
> *Capturamos `api_request_failed` porque necesitamos **distinguir entre errores de cliente (4xx) y servidor (5xx)**, lo que nos permite **priorizar investigación** (5xx = bug nuestro, 4xx = validación o UX).*

**Clasificación**: 🔴 **Obligatorio** (Reliability)

**Hipótesis**: Pico de 5xx errors indica deploy roto o problema de infraestructura.

**Decisión concreta**: Rollback automático si tasa de 5xx >5% durante 5 minutos post-deploy.

---

##### Evento 15: `network_request_timeout`

**Regla de Oro**:
> *Capturamos `network_request_timeout` porque necesitamos **detectar problemas de conectividad entre frontend y API**, lo que nos permite **identificar si es problema de red, CDN o backend overwhelmed**.*

**Clasificación**: 🟡 **Oportunidad Identificada** (Network Engineering)

**Hipótesis**: Timeouts >5% en región específica (ej. Florida) indican problema de CDN edge.

**Decisión concreta**: Si timeouts concentrados en región geográfica, investigar CDN edge server.

---

#### 🧭 **Categoría 4: Navegación y UX**

##### Evento 16: `page_view`

**Regla de Oro**:
> *Capturamos `page_view` porque necesitamos **identificar secciones del backoffice más usadas**, lo que nos permite **priorizar optimizaciones de performance y UX** en páginas críticas.*

**Clasificación**: 🟡 **Oportunidad Identificada** (Product Analytics)

**Hipótesis**: 80% del tiempo se pasa en 20% de las páginas (Pareto).

**Decisión concreta**: Optimizar (caché, lazy loading) páginas que representan >50% del tráfico.

---

##### Evento 17: `form_submission_abandoned`

**Regla de Oro**:
> *Capturamos `form_submission_abandoned` porque necesitamos **identificar fricciones en formularios de órdenes**, lo que nos permite **simplificar campos obligatorios o mejorar validaciones**.*

**Clasificación**: 🟡 **Oportunidad Identificada** (Conversion Optimization)

**Hipótesis**: Abandono >30% en formulario de outbound order indica complejidad excesiva o confusión.

**Decisión concreta**: A/B testing de formulario simplificado si abandono >30%.

---

##### Evento 18: `search_query_zero_results`

**Regla de Oro**:
> *Capturamos `search_query_zero_results` porque necesitamos **mejorar búsqueda de ingredientes** (fuzzy matching, sinónimos), lo que nos permite **reducir frustración de usuarios**.*

**Clasificación**: 🟡 **Oportunidad Identificada** (Search UX)

**Hipótesis**: Queries sin resultados indican naming inconsistente en ingredientes o falta de fuzzy search.

**Decisión concreta**: Si >10% de searches dan 0 resultados, implementar fuzzy matching o sugerir términos similares.

---

### 1.4. Resumen del Catálogo

#### Tabla de Priorización

| # | Evento | Categoría | Clasificación | Decisión de Negocio |
|---|--------|-----------|---------------|----------------------|
| 1 | `direct_stock_edit_rejected` | Inventario | 🔴 Obligatorio | Formación + auditoría fraude |
| 2 | `outbound_stock_insufficient` | Inventario | 🔴 Obligatorio | Auditoría física de almacén |
| 3 | `stock_threshold_triggered` | Inventario | 🔴 Obligatorio | Orden de compra automática |
| 4 | `stock_calculation_latency` | Performance | 🟡 Oportunidad | Optimización de queries SQL |
| 5 | `inbound_order_created` | Inventario | 🔴 Obligatorio | Predicción de demanda (ML) |
| 6 | `outbound_order_created` | Inventario | 🔴 Obligatorio | Predicción de demanda (ML) |
| 7 | `ingredient_viewed_critical_stock` | UX | 🟡 Oportunidad | Escalar alerta si no atendida |
| 8 | `login_attempt_failed` | Seguridad | 🔴 Obligatorio | Rate limiting + bloqueo IP |
| 9 | `session_expired` | Seguridad | 🟡 Oportunidad | Ajuste de TTL de sesión |
| 10 | `password_reset_requested` | Seguridad | 🟡 Oportunidad | Detección de phishing |
| 11 | `api_latency_recorded` | Performance | 🔴 Obligatorio | Alertas de degradación |
| 12 | `database_query_slow` | Performance | 🟡 Oportunidad | Optimización de índices |
| 13 | `cache_hit_rate_measured` | Performance | 🟡 Oportunidad | Ajuste de TTLs |
| 14 | `frontend_error_uncaught` | Reliability | 🔴 Obligatorio | Auto-ticketing de bugs |
| 15 | `api_request_failed` | Reliability | 🔴 Obligatorio | Rollback automático |
| 16 | `network_request_timeout` | Network | 🟡 Oportunidad | Investigación de CDN |
| 17 | `page_view` | Analytics | 🟡 Oportunidad | Priorización de optimizaciones |
| 18 | `form_submission_abandoned` | UX | 🟡 Oportunidad | Simplificación de formularios |
| 19 | `search_query_zero_results` | UX | 🟡 Oportunidad | Fuzzy search |

**Total**: 19 eventos
- 🔴 **Obligatorios**: 9 (47%)
- 🟡 **Oportunidades**: 10 (53%)

**Cobertura por categoría**:
- Inventario: 7 eventos (37%)
- Seguridad: 3 eventos (16%)
- Performance: 3 eventos (16%)
- Reliability: 2 eventos (10%)
- UX: 3 eventos (16%)
- Network: 1 evento (5%)

---

## 🏗️ FASE 2: DISEÑO DEL ESTÁNDAR EVENT ENVELOPE Y ESQUEMAS

---

### 2.1. Estructura Estándar del Event Envelope

#### JSON Schema del Envelope Universal

Todos los eventos del monorepo Brasaland **DEBEN** seguir esta estructura:

```json
{
  "eventId": "uuid-v4",
  "timestamp": "ISO-8601-UTC",
  "sessionId": "string | null",
  "userId": "string | null",
  "event_type": "entidad_accion",
  "schemaVersion": "semver",
  "requestId": "correlation-uuid",
  "properties": {
    // Payload específico del evento
  }
}
```

#### Especificación de Campos Obligatorios

| Campo | Tipo | Obligatorio | Descripción | Ejemplo |
|-------|------|-------------|-------------|---------|
| `eventId` | UUID v4 | ✅ Sí | Identificador único del evento. Generado en origen (frontend o backend). Idempotencia garantizada. | `"a3f5c2d1-8b4e-4f9a-9c7d-1e2f3a4b5c6d"` |
| `timestamp` | ISO 8601 UTC | ✅ Sí | Momento exacto de ocurrencia del evento. Formato: `YYYY-MM-DDTHH:mm:ss.sssZ`. Timezone: siempre UTC. | `"2026-10-30T14:23:45.123Z"` |
| `sessionId` | String | ⚠️ Condicional | Identificador de sesión activa. En frontend: generado al cargar app. En backend sin sesión: `null`. | `"sess_9x8y7z6w5v4u3t2s1r"` |
| `userId` | String | ⚠️ Condicional | UUID del usuario autenticado (referencia a TinyDB users). `null` en flujos anónimos (login fallido, página pública). | `"550e8400-e29b-41d4-a716-446655440000"` |
| `event_type` | String | ✅ Sí | Taxonomía `entidad_acción`. Snake_case. Evita verbos genéricos ("clicked", "loaded"). Prefiere: `ingredient_viewed`, `outbound_order_created`. | `"stock_threshold_triggered"` |
| `schemaVersion` | Semver | ✅ Sí | Versión del schema del evento. Formato: `"MAJOR.MINOR.PATCH"`. Permite evolución backwards-compatible. | `"1.0.0"` |
| `requestId` | UUID v4 | ✅ Sí | Identificador de correlación. Frontend: generado por request. Backend: heredado de header `X-Request-ID`. Tracing distribuido. | `"req_1a2b3c4d5e6f7g8h9i0j"` |
| `properties` | Object | ✅ Sí | Payload específico del evento. Estructura definida por schema individual. Allowlist estricto (ver sección 2.2). | `{ "ingredient_id": 42, ... }` |

---

### 2.2. Catálogo de Esquemas (19 Eventos)

#### Esquema 1: `direct_stock_edit_rejected`

**Descripción**: Captura intentos de modificación directa de stock (bypassing flujo de órdenes).

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `ingredient_id` | Integer | ✅ | ❌ | ID del ingrediente (FK a `ingredients.id`) |
| `ingredient_name` | String | ✅ | ❌ | Nombre del ingrediente para contexto humano |
| `warehouse` | Enum | ✅ | ❌ | Almacén donde se intentó modificar (ej. `medellin_centro`) |
| `attempted_quantity` | Float | ✅ | ❌ | Cantidad que intentó establecer directamente |
| `current_stock` | Float | ✅ | ❌ | Stock actual calculado |
| `rejection_reason` | String | ✅ | ❌ | Razón del rechazo (ej. `"Direct stock edits not allowed. Use inbound/outbound orders."`) |
| `user_role` | String | ✅ | ❌ | Rol del usuario (ej. `admin`, `operator`) |

**Ejemplo JSON**:
```json
{
  "eventId": "evt_001",
  "timestamp": "2026-10-30T14:23:45.123Z",
  "sessionId": "sess_abc123",
  "userId": "user_123",
  "event_type": "direct_stock_edit_rejected",
  "schemaVersion": "1.0.0",
  "requestId": "req_xyz789",
  "properties": {
    "ingredient_id": 42,
    "ingredient_name": "Carne de res",
    "warehouse": "medellin_centro",
    "attempted_quantity": 150.0,
    "current_stock": 85.5,
    "rejection_reason": "Direct stock edits not allowed. Use inbound/outbound orders.",
    "user_role": "operator"
  }
}
```

---

#### Esquema 2: `outbound_stock_insufficient`

**Descripción**: Validación fallida de orden de salida por stock insuficiente.

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `ingredient_id` | Integer | ✅ | ❌ | ID del ingrediente |
| `ingredient_name` | String | ✅ | ❌ | Nombre del ingrediente |
| `warehouse` | Enum | ✅ | ❌ | Almacén de origen |
| `requested_quantity` | Float | ✅ | ❌ | Cantidad solicitada en orden outbound |
| `available_stock` | Float | ✅ | ❌ | Stock disponible actual |
| `deficit` | Float | ✅ | ❌ | `requested_quantity - available_stock` |
| `last_inbound_order_date` | ISO 8601 | ⚠️ | ❌ | Fecha de última entrada (para detectar desajustes) |

**Tratamiento de PII**: ❌ Sin datos sensibles. Todos los campos son operacionales.

---

#### Esquema 3: `stock_threshold_triggered`

**Descripción**: Stock de ingrediente cruza umbral mínimo (`current_stock < min_stock`).

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `ingredient_id` | Integer | ✅ | ❌ | ID del ingrediente |
| `ingredient_name` | String | ✅ | ❌ | Nombre del ingrediente |
| `warehouse` | Enum | ✅ | ❌ | Almacén afectado |
| `current_stock` | Float | ✅ | ❌ | Stock actual calculado |
| `min_stock` | Float | ✅ | ❌ | Umbral mínimo configurado |
| `reorder_point` | Float | ⚠️ | ❌ | Punto de reorden (si configurado) |
| `threshold_severity` | Enum | ✅ | ❌ | `critical` (stock < 20% min), `warning` (20-50%), `low` (50-100%) |

**Decisión técnica**: `threshold_severity` permite priorizar alertas sin calcular porcentaje en cada query.

---

#### Esquema 4: `stock_calculation_latency`

**Descripción**: Medición de performance de cálculo de stock (SUM agregación).

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `ingredient_id` | Integer | ✅ | ❌ | ID del ingrediente |
| `warehouse` | Enum | ⚠️ | ❌ | Almacén específico (si filtrado) o `null` para global |
| `duration_ms` | Float | ✅ | ❌ | Tiempo de cálculo en milisegundos |
| `inbound_count` | Integer | ✅ | ❌ | Número de registros en `inbound_orders` sumados |
| `outbound_count` | Integer | ✅ | ❌ | Número de registros en `outbound_orders` sumados |
| `query_type` | Enum | ✅ | ❌ | `single_ingredient`, `list_all`, `filtered_by_warehouse` |

**Uso**: Alimentar dashboards de performance, identificar queries N+1 o missing indexes.

---

#### Esquema 5: `inbound_order_created`

**Descripción**: Orden de entrada de stock registrada exitosamente.

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `order_id` | Integer | ✅ | ❌ | ID de la orden (`inbound_orders.id`) |
| `ingredient_id` | Integer | ✅ | ❌ | ID del ingrediente |
| `ingredient_name` | String | ✅ | ❌ | Nombre del ingrediente |
| `quantity` | Float | ✅ | ❌ | Cantidad ingresada |
| `unit` | Enum | ✅ | ❌ | Unidad de medida (kg, l, unit, etc.) |
| `warehouse` | Enum | ✅ | ❌ | Almacén de destino |
| `notes` | String | ⚠️ | ⚠️ PII Potencial | Notas del usuario. **Sanitizar**: Remover nombres propios, teléfonos. |

**Tratamiento de PII**: Campo `notes` puede contener información sensible (ej. "Proveedor Juan llamó"). Aplicar regex para detectar patrones de email/teléfono y reemplazar con `[REDACTED]`.

---

#### Esquema 6: `outbound_order_created`

**Descripción**: Orden de salida de stock registrada exitosamente.

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `order_id` | Integer | ✅ | ❌ | ID de la orden (`outbound_orders.id`) |
| `ingredient_id` | Integer | ✅ | ❌ | ID del ingrediente |
| `ingredient_name` | String | ✅ | ❌ | Nombre del ingrediente |
| `quantity` | Float | ✅ | ❌ | Cantidad consumida |
| `unit` | Enum | ✅ | ❌ | Unidad de medida |
| `warehouse` | Enum | ✅ | ❌ | Almacén de origen |
| `reason` | String | ⚠️ | ⚠️ PII Potencial | Razón de salida. **Sanitizar**: Similar a `notes` en inbound. |
| `remaining_stock` | Float | ✅ | ❌ | Stock calculado post-operación |

---

#### Esquema 7: `ingredient_viewed_critical_stock`

**Descripción**: Usuario visualiza ingrediente con stock por debajo del umbral.

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `ingredient_id` | Integer | ✅ | ❌ | ID del ingrediente |
| `ingredient_name` | String | ✅ | ❌ | Nombre del ingrediente |
| `current_stock` | Float | ✅ | ❌ | Stock actual |
| `min_stock` | Float | ✅ | ❌ | Umbral mínimo |
| `page_url` | String | ✅ | ❌ | Ruta de la página (ej. `/inventory/ingredients`) |
| `time_since_alert` | Integer | ✅ | ❌ | Segundos desde que se disparó `stock_threshold_triggered` |

**Uso**: Medir tiempo de respuesta de operadores a alertas de stock crítico.

---

#### Esquema 8: `login_attempt_failed`

**Descripción**: Intento fallido de autenticación (credenciales incorrectas).

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `email_hash` | String (SHA256) | ✅ | 🔒 Anonimizado | Email hasheado con SHA256 para evitar exposición. |
| `failure_reason` | Enum | ✅ | ❌ | `invalid_credentials`, `account_locked`, `account_not_found` |
| `ip_address` | String | ✅ | ⚠️ PII | IP del cliente. **Tratamiento**: Última octet enmascarada (ej. `192.168.1.XXX`) para GDPR. |
| `user_agent` | String | ✅ | ❌ | User-Agent del navegador (detección de bots) |
| `attempt_count_last_hour` | Integer | ✅ | ❌ | Conteo de intentos fallidos del mismo email en última hora |

**Tratamiento de PII**:
- **Email**: NUNCA en claro. Hashear con SHA256 + salt único por instalación.
- **IP**: Enmascarar último octeto (`192.168.1.0` en lugar de `192.168.1.123`).

---

#### Esquema 9: `session_expired`

**Descripción**: Sesión JWT expiró (TTL agotado).

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `session_duration_seconds` | Integer | ✅ | ❌ | Tiempo total de sesión (desde login hasta expiración) |
| `last_activity_seconds_ago` | Integer | ✅ | ❌ | Segundos desde última interacción del usuario |
| `page_at_expiration` | String | ✅ | ❌ | Ruta donde estaba el usuario (ej. `/inventory/orders/outbound`) |
| `was_active` | Boolean | ✅ | ❌ | `true` si usuario hizo click <1 min antes de expiración |

**Uso**: Si `was_active=true` en >30% de expiraciones, aumentar TTL.

---

#### Esquema 10: `password_reset_requested`

**Descripción**: Usuario solicitó reset de contraseña.

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `email_hash` | String (SHA256) | ✅ | 🔒 Anonimizado | Email hasheado |
| `ip_address_masked` | String | ✅ | ⚠️ PII | IP enmascarada |
| `reset_token_sent` | Boolean | ✅ | ❌ | `true` si email fue enviado exitosamente |
| `account_exists` | Boolean | ✅ | ❌ | `true` si cuenta existe (para detectar fishing de cuentas) |

**Tratamiento de PII**: Similar a `login_attempt_failed`.

---

#### Esquema 11: `api_latency_recorded`

**Descripción**: Medición de latencia de endpoint de API.

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `endpoint` | String | ✅ | ❌ | Path del endpoint (ej. `/inventory/ingredients`) |
| `method` | Enum | ✅ | ❌ | `GET`, `POST`, `PATCH`, `PUT`, `DELETE` |
| `duration_ms` | Float | ✅ | ❌ | Latencia total (request → response) |
| `status_code` | Integer | ✅ | ❌ | HTTP status code (200, 400, 500, etc.) |
| `cache_hit` | Boolean | ⚠️ | ❌ | `true` si fue servido desde caché |
| `db_query_time_ms` | Float | ⚠️ | ❌ | Tiempo de query a BD (si aplica) |

**Origen**: Middleware `TimingMiddleware` (ver `CACHING_REPORT.md`).

---

#### Esquema 12: `database_query_slow`

**Descripción**: Query a base de datos excede umbral de latencia (>1 segundo).

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `query_hash` | String (MD5) | ✅ | ❌ | Hash del SQL query (sin parámetros) para agrupación |
| `duration_ms` | Float | ✅ | ❌ | Tiempo de ejecución |
| `table_name` | String | ✅ | ❌ | Tabla principal afectada |
| `operation_type` | Enum | ✅ | ❌ | `SELECT`, `INSERT`, `UPDATE`, `DELETE` |
| `rows_examined` | Integer | ⚠️ | ❌ | Número de filas examinadas (de EXPLAIN) |
| `rows_returned` | Integer | ⚠️ | ❌ | Número de filas retornadas |

**Uso**: Identificar queries N+1, missing indexes, full table scans.

---

#### Esquema 13: `cache_hit_rate_measured`

**Descripción**: Medición periódica (cada 5min) de hit rate de caché.

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `cache_type` | Enum | ✅ | ❌ | `in_memory_backend`, `browser_localstorage` |
| `key_prefix` | String | ✅ | ❌ | Prefijo de claves (ej. `incidents:list`, `ingredients:stock`) |
| `hits` | Integer | ✅ | ❌ | Número de cache hits en ventana |
| `misses` | Integer | ✅ | ❌ | Número de cache misses |
| `hit_rate_percent` | Float | ✅ | ❌ | `(hits / (hits + misses)) * 100` |
| `ttl_seconds` | Integer | ✅ | ❌ | TTL configurado |

**Origen**: Sistema de caché implementado (ver `CACHING_AUDIT_REPORT.md`).

---

#### Esquema 14: `frontend_error_uncaught`

**Descripción**: Error no capturado en JavaScript (window.onerror, React ErrorBoundary).

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `error_message` | String | ✅ | ❌ | Mensaje de error (max 500 chars) |
| `error_stack` | String | ⚠️ | ❌ | Stack trace (max 2000 chars). **Sanitizar**: Remover paths absolutos. |
| `component_name` | String | ⚠️ | ❌ | Componente React donde ocurrió (si disponible) |
| `page_url` | String | ✅ | ❌ | Ruta de la página |
| `browser` | String | ✅ | ❌ | Navegador (de user-agent) |
| `browser_version` | String | ✅ | ❌ | Versión del navegador |

**Tratamiento de PII**: Stack trace puede contener paths locales del desarrollador. Regex para remover `/Users/...` o `C:\Users\...`.

---

#### Esquema 15: `api_request_failed`

**Descripción**: Request de API falló con error 4xx o 5xx.

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `endpoint` | String | ✅ | ❌ | Path del endpoint |
| `method` | Enum | ✅ | ❌ | HTTP method |
| `status_code` | Integer | ✅ | ❌ | HTTP status code (400-599) |
| `error_type` | Enum | ✅ | ❌ | `client_error_4xx`, `server_error_5xx` |
| `error_detail` | String | ⚠️ | ❌ | Mensaje de error del servidor (max 200 chars) |
| `duration_ms` | Float | ✅ | ❌ | Latencia antes del error |

---

#### Esquema 16: `network_request_timeout`

**Descripción**: Request de frontend a API excede timeout (default 30s).

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `endpoint` | String | ✅ | ❌ | Path del endpoint |
| `method` | Enum | ✅ | ❌ | HTTP method |
| `timeout_ms` | Integer | ✅ | ❌ | Timeout configurado |
| `elapsed_ms` | Float | ✅ | ❌ | Tiempo transcurrido antes de timeout |
| `network_type` | String | ⚠️ | ❌ | Tipo de red (de navigator.connection): `4g`, `3g`, `wifi` |

**Uso**: Detectar problemas de conectividad por región o tipo de red.

---

#### Esquema 17: `page_view`

**Descripción**: Usuario navega a una página del backoffice.

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `page_url` | String | ✅ | ❌ | Ruta de la página (ej. `/inventory/ingredients`) |
| `page_title` | String | ✅ | ❌ | Título de la página |
| `referrer_url` | String | ⚠️ | ❌ | Página previa (si aplica) |
| `load_time_ms` | Float | ⚠️ | ❌ | Tiempo de carga (DOMContentLoaded) |

---

#### Esquema 18: `form_submission_abandoned`

**Descripción**: Usuario abandona formulario sin completar.

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `form_name` | String | ✅ | ❌ | Identificador del formulario (ej. `outbound_order_form`) |
| `page_url` | String | ✅ | ❌ | Ruta de la página |
| `fields_completed` | Integer | ✅ | ❌ | Número de campos completados |
| `total_fields` | Integer | ✅ | ❌ | Número total de campos |
| `time_spent_seconds` | Integer | ✅ | ❌ | Tiempo pasado en el formulario antes de abandonar |
| `last_field_interacted` | String | ⚠️ | ❌ | Último campo tocado (para identificar fricciones) |

---

#### Esquema 19: `search_query_zero_results`

**Descripción**: Búsqueda de ingredientes no retorna resultados.

**Allowlist de Propiedades**:

| Campo | Tipo | Obligatorio | PII | Descripción |
|-------|------|-------------|-----|-------------|
| `query_text` | String | ✅ | ❌ | Texto buscado (max 100 chars) |
| `search_scope` | Enum | ✅ | ❌ | `ingredients`, `orders`, `global` |
| `filters_applied` | Object | ⚠️ | ❌ | Filtros activos (ej. `{"warehouse": "medellin_centro"}`) |

---

## 🚀 FASE 3: ESTRATEGIA DE ENTREGA, INGESTION Y RIESGOS

---

### 3.1. Pipeline de Entrega: Stream vs. Batch

#### Decisión Framework

**STREAM** (Tiempo real, <1 segundo):
- ✅ Requiere acción inmediata (alerta, rollback, bloqueo)
- ✅ Alimenta dashboards en tiempo real
- ✅ Frecuencia: <100 eventos/segundo

**BATCH** (Procesamiento por lotes, cada 5-15 minutos):
- ✅ Análisis histórico, ML, reportes diarios
- ✅ Alto volumen (>1000 eventos/minuto)
- ✅ Decisión no urgente (<1 hora es aceptable)

---

#### Matriz de Clasificación

| Evento | Pipeline | Justificación |
|--------|----------|---------------|
| `direct_stock_edit_rejected` | 🔴 **Stream** | Auditoría de seguridad requiere alerta inmediata |
| `outbound_stock_insufficient` | 🔴 **Stream** | Supervisores deben ser notificados para auditoría física |
| `stock_threshold_triggered` | 🔴 **Stream** | Alerta a Compras (Lucía) debe ser inmediata para evitar desabasto |
| `stock_calculation_latency` | 🟡 **Batch** | Análisis de performance no requiere acción en segundos |
| `inbound_order_created` | 🟡 **Batch** | Predicción de demanda se ejecuta semanalmente |
| `outbound_order_created` | 🟡 **Batch** | Análisis de consumo es histórico |
| `ingredient_viewed_critical_stock` | 🟡 **Batch** | Medición de respuesta a alertas es análisis post-facto |
| `login_attempt_failed` | 🔴 **Stream** | Rate limiting debe activarse en <5 segundos |
| `session_expired` | 🟡 **Batch** | Ajuste de TTL es decisión de producto (semanal) |
| `password_reset_requested` | 🔴 **Stream** | Detección de phishing masivo requiere alerta inmediata |
| `api_latency_recorded` | 🟡 **Batch** | Monitoreo de p95 se evalúa cada 5-15min |
| `database_query_slow` | 🟡 **Batch** | Optimización de queries es revisión semanal |
| `cache_hit_rate_measured` | 🟡 **Batch** | Métrica de performance, evaluación horaria |
| `frontend_error_uncaught` | 🔴 **Stream** | Auto-ticketing de bugs debe ser inmediato |
| `api_request_failed` | 🔴 **Stream** | Rollback automático si tasa 5xx >5% |
| `network_request_timeout` | 🟡 **Batch** | Análisis de CDN no requiere acción inmediata |
| `page_view` | 🟡 **Batch** | Analytics de producto es análisis semanal |
| `form_submission_abandoned` | 🟡 **Batch** | Optimización de UX es decisión de producto |
| `search_query_zero_results` | 🟡 **Batch** | Implementación de fuzzy search es mejora planificada |

**Resumen**:
- **Stream**: 7 eventos (37%) - Seguridad, alertas operacionales, reliability
- **Batch**: 12 eventos (63%) - Analytics, performance, ML

---

### 3.2. Estrategias de Throttling y Debouncing

#### Problema: Alta Frecuencia de Eventos

Ciertos eventos pueden dispararse cientos de veces por minuto:
- `api_latency_recorded`: Cada request HTTP
- `page_view`: Cada navegación
- `stock_calculation_latency`: Cada render de `/inventory/ingredients`

**Riesgo**: Overhead de red, saturación de pipeline de ingestion, costos de almacenamiento.

---

#### Estrategia 1: Sampling Rate

**Aplicar a**: Eventos de alta frecuencia con valor agregado (no individual).

**Implementación**:
```typescript
// Frontend - Sampling 10% de page_views
if (Math.random() < 0.1) {
  trackEvent('page_view', properties);
}
```

**Eventos con sampling**:
- `api_latency_recorded`: Sample 20% (suficiente para p95)
- `page_view`: Sample 10%
- `stock_calculation_latency`: Sample 25%

---

#### Estrategia 2: Debouncing

**Aplicar a**: Eventos repetitivos del mismo usuario en corto tiempo.

**Implementación**:
```typescript
// Frontend - Debounce de 5 segundos para ingredient_viewed_critical_stock
const debouncedTrackView = debounce((properties) => {
  trackEvent('ingredient_viewed_critical_stock', properties);
}, 5000);
```

**Eventos con debouncing**:
- `ingredient_viewed_critical_stock`: 5 segundos (evitar duplicados si usuario refresca página)
- `search_query_zero_results`: 3 segundos (evitar disparos en cada tecla)

---

#### Estrategia 3: Aggregation en Backend

**Aplicar a**: Métricas cuantitativas que pueden agruparse.

**Ejemplo**: `cache_hit_rate_measured`
- En lugar de enviar 1 evento por cada hit/miss
- Enviar 1 evento cada 5 minutos con totales agregados

**Implementación**:
```python
# Backend - Aggregation cada 5 minutos
cache_stats = {
  "hits": cache.get_hits_count(),
  "misses": cache.get_misses_count(),
  "hit_rate_percent": calculate_hit_rate()
}
send_event_batch('cache_hit_rate_measured', cache_stats)
```

---

### 3.3. Matriz de Riesgos y Exclusiones

#### Tabla de Eventos Considerados y Descartados

| Evento Descartado | Razón de Exclusión | Justificación |
|-------------------|-------------------|---------------|
| `user_email_captured` | 🔒 **GDPR/PII** | Email es PII. Si se necesita, hashear con SHA256. Preferimos `userId` (UUID anónimo). |
| `user_password_attempt_logged` | 🔒 **Security** | NUNCA loguear passwords (ni hashes). Violación crítica de seguridad. |
| `credit_card_number_entered` | 🔒 **PCI-DSS** | Datos de pago nunca deben salir de procesador certificado (Stripe, PayPal). |
| `session_token_captured` | 🔒 **Security** | JWT tokens son credenciales. Capturar = vulnerabilidad de session hijacking. |
| `mouse_movement_tracked` | 💸 **Coste** | Millones de eventos/día. Coste de almacenamiento >$1000/mes sin valor de negocio. |
| `pixel_scroll_position` | 💸 **Coste + Ruido** | Granularidad excesiva. `page_view` es suficiente para analytics. |
| `every_api_request_logged` | 💸 **Coste + Ruido** | Sin sampling, >100K eventos/día. Sampling 20% reduce a 20K manteniendo precisión de p95. |
| `user_full_name_logged` | 🔒 **GDPR/PII** | Nombre es PII. Usar `userId` (UUID) para anonimato. |
| `ip_address_full` | 🔒 **GDPR/PII** | IP es PII según GDPR. Enmascarar último octeto (`192.168.1.XXX`). |
| `geolocation_coordinates` | 🔒 **GDPR/PII** | Coordenadas GPS son PII. País/ciudad es suficiente para analytics. |
| `browser_fingerprint` | 🔒 **Privacy** | Tracking agresivo. Violaría políticas de privacidad. |
| `clipboard_content` | 🔒 **Privacy** | Capturar clipboard es invasivo. Nunca implementar. |
| `file_upload_content` | 🔒 **Privacy + Storage** | Contenido de archivos puede ser sensible. Solo loguear metadata (nombre, tamaño, tipo). |
| `sql_query_full_text` | 🔒 **Security** | Queries pueden contener PII en WHERE clauses. Usar `query_hash` (sin parámetros). |
| `error_with_user_input` | 🔒 **Privacy** | Stack traces pueden incluir input del usuario (ej. búsquedas). Sanitizar antes de loguear. |

---

#### Categorías de Exclusión

1. **GDPR/PII** (9 eventos): Datos personales identificables
2. **Security** (3 eventos): Credenciales, tokens, passwords
3. **Coste** (3 eventos): Alto volumen sin valor proporcional
4. **Privacy** (4 eventos): Tracking invasivo sin justificación

---

#### Técnicas de Anonimización Aplicadas

| Tipo de Dato | Técnica | Ejemplo |
|--------------|---------|---------|
| Email | SHA256 hash | `user@brasaland.com` → `8d969eef6ecad3c29a3a629280e686cf...` |
| IP Address | Último octeto enmascarado | `192.168.1.123` → `192.168.1.0` |
| User ID | UUID v4 anónimo | Referencia a TinyDB users sin exponer email |
| Notas/Razones | Regex sanitización | `"Proveedor Juan 555-1234"` → `"Proveedor [REDACTED] [REDACTED]"` |
| SQL Queries | Hash MD5 sin parámetros | `SELECT * FROM users WHERE email = ?` → `md5(query_template)` |
| Stack Traces | Remover paths absolutos | `/Users/dev/project/...` → `[PROJECT_ROOT]/...` |

---

## 📊 IMPLEMENTACIÓN Y ARQUITECTURA TÉCNICA

---

### 4.1. Stack Tecnológico Propuesto

#### Recolección de Eventos

**Frontend (Next.js 15)**:
```typescript
// lib/telemetry.ts
export function trackEvent(eventType: string, properties: object) {
  const envelope = {
    eventId: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    sessionId: getSessionId(),
    userId: getCurrentUserId(),
    event_type: eventType,
    schemaVersion: "1.0.0",
    requestId: getRequestId(),
    properties: sanitize(properties)
  };
  
  // Batch events en localStorage, flush cada 10 eventos o 30 segundos
  batchAndSend(envelope);
}
```

**Backend (FastAPI)**:
```python
# app/telemetry/tracker.py
def track_event(event_type: str, properties: dict, user_id: str = None):
    envelope = {
        "eventId": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "sessionId": None,  # Backend events no tienen sesión UI
        "userId": user_id,
        "event_type": event_type,
        "schemaVersion": "1.0.0",
        "requestId": get_request_id(),
        "properties": sanitize(properties)
    }
    
    # Stream a Kafka o HTTP POST a ingestion endpoint
    send_to_pipeline(envelope)
```

---

#### Ingestion Pipeline

**Opción 1: Simple (MVP)**
- **HTTP Endpoint**: `POST /telemetry/ingest`
- **Storage**: PostgreSQL table `events` con JSONB column
- **Procesamiento**: Cron job diario para agregaciones

**Opción 2: Escalable (Producción)**
- **Stream**: Apache Kafka (eventos Stream)
- **Batch**: S3 + AWS Lambda (eventos Batch)
- **Storage**: ClickHouse (column-store para analytics)
- **Procesamiento**: Apache Spark para ML

---

### 4.2. Validación de Schemas

**JSON Schema Validation** (ver `event-schemas.json`):
```python
import jsonschema

def validate_event(envelope: dict) -> bool:
    schema = load_schema(envelope["event_type"], envelope["schemaVersion"])
    try:
        jsonschema.validate(envelope["properties"], schema)
        return True
    except jsonschema.ValidationError as e:
        log_validation_error(envelope["eventId"], str(e))
        return False
```

---

### 4.3. Retention Policies

| Tipo de Evento | Retention Hot Storage | Retention Cold Storage | Justificación |
|----------------|----------------------|------------------------|---------------|
| **Stream críticos** (seguridad, alertas) | 90 días | 2 años | Auditorías de seguridad, compliance |
| **Batch analytics** (page_view, etc.) | 30 días | 1 año | Análisis de producto, suficiente para trends |
| **Performance metrics** | 14 días | 6 meses | Optimizaciones recientes más relevantes |

**Cold storage**: S3 Glacier, acceso <24h si se necesita auditoría histórica.

---

## 🎯 DASHBOARDS Y ALERTAS

---

### 5.1. Dashboards Operacionales

#### Dashboard 1: Salud de Inventario

**Métricas**:
- Ingredientes con stock crítico (últimas 24h)
- Tasa de rechazos de órdenes outbound (por almacén)
- Tiempo promedio de respuesta a alertas de stock bajo
- Predicción de desabasto en próximos 7 días

**Eventos fuente**:
- `stock_threshold_triggered`
- `outbound_stock_insufficient`
- `ingredient_viewed_critical_stock`
- `inbound_order_created`, `outbound_order_created`

---

#### Dashboard 2: Seguridad y Accesos

**Métricas**:
- Intentos fallidos de login por hora
- Cuentas con >5 intentos fallidos (últimas 24h)
- Tasa de sesiones expiradas con usuario activo
- Picos anómalos de password resets

**Eventos fuente**:
- `login_attempt_failed`
- `session_expired`
- `password_reset_requested`

---

#### Dashboard 3: Performance del Sistema

**Métricas**:
- Latencia p50/p95/p99 por endpoint
- Tasa de errores 5xx (últimas 1h, 24h, 7d)
- Hit rate de caché por key_prefix
- Queries lentas (>1 segundo) top 10

**Eventos fuente**:
- `api_latency_recorded`
- `api_request_failed`
- `cache_hit_rate_measured`
- `database_query_slow`

---

### 5.2. Alertas Automatizadas

| Alerta | Condición | Canal | Acción |
|--------|-----------|-------|--------|
| **Stock Crítico** | `stock_threshold_triggered` con `severity=critical` | Email a Lucía (Compras) + Slack #compras | Generar borrador orden de compra |
| **Ataque de Fuerza Bruta** | >10 `login_attempt_failed` misma IP en 10min | Email a CTO + bloqueo IP automático | Activar rate limiting |
| **Deploy Roto** | Tasa `api_request_failed` (5xx) >5% en 5min | PagerDuty a on-call engineer | Rollback automático |
| **Query Lenta Recurrente** | Mismo `query_hash` en `database_query_slow` >3 veces en 1h | Ticket automático en Jira | Revisión de índices |
| **Stock Desajustado** | `outbound_stock_insufficient` >5 veces mismo ingrediente en 24h | Email a supervisor de almacén | Auditoría física inventario |

---

## 📝 PRÓXIMOS PASOS

---

### Fase 1: Implementación Base (Sprint 1-2, 2 semanas)

1. ✅ Aprobar este `TELEMETRY_PLAN.md` y `event-schemas.json`
2. 🔧 Implementar librería `telemetry.ts` en frontend
3. 🔧 Implementar módulo `telemetry/tracker.py` en backend
4. 🔧 Crear endpoint `/telemetry/ingest` (MVP: PostgreSQL)
5. 🔧 Instrumentar 5 eventos obligatorios de inventario

---

### Fase 2: Expansión de Cobertura (Sprint 3-4, 2 semanas)

6. 🔧 Instrumentar 9 eventos restantes obligatorios
7. 🔧 Implementar sampling/debouncing en frontend
8. 🔧 Configurar aggregation en backend para métricas cuantitativas
9. 🔧 Validación de schemas con `jsonschema` en ingestion

---

### Fase 3: Analytics y Dashboards (Sprint 5-6, 2 semanas)

10. 📊 Crear Dashboard 1: Salud de Inventario (Grafana/Metabase)
11. 📊 Crear Dashboard 2: Seguridad y Accesos
12. 📊 Crear Dashboard 3: Performance del Sistema
13. 🚨 Configurar alertas automatizadas (email, Slack, PagerDuty)

---

### Fase 4: ML y Predicción (Sprint 7+, 4 semanas)

14. 🤖 Modelo predictivo de demanda de ingredientes (basado en `outbound_order_created`)
15. 🤖 Detección de anomalías en patrones de login (phishing, bots)
16. 🤖 Recomendación automática de niveles de reorden (`reorder_point` dinámico)

---

## 📚 ANEXOS

### Anexo A: Glosario de Términos

- **Event Envelope**: Estructura JSON estándar que envuelve todos los eventos
- **Allowlist**: Lista explícita de propiedades permitidas en `properties` de un evento
- **PII (Personally Identifiable Information)**: Datos que identifican a una persona (email, IP, nombre)
- **Stream Processing**: Procesamiento en tiempo real (<1 segundo)
- **Batch Processing**: Procesamiento por lotes (5-15 minutos o más)
- **Sampling Rate**: Porcentaje de eventos que se capturan (ej. 20% = 1 de cada 5)
- **Debouncing**: Técnica para evitar disparos múltiples de eventos en corto tiempo
- **Hot Storage**: Almacenamiento de acceso rápido (SSD, RAM)
- **Cold Storage**: Almacenamiento de largo plazo (S3 Glacier)

---

### Anexo B: Referencias Técnicas

**Documentos relacionados**:
- `CACHING_REPORT.md`: Estrategia de caching implementada (TTLs, invalidación)
- `CACHING_AUDIT_REPORT.md`: Auditoría de seguridad en sistema de caché
- `COMPLIANCE_AUDIT_SERIALIZATION.md`: Auditoría de serialización de API
- `projectbrief.md`: Contexto del negocio Brasaland
- `CONTEXT.md`: Descripción completa de la empresa y stakeholders

**Modelos de datos**:
- `services/api/app/models/inventory.py`: Ingredient, InboundOrder, OutboundOrder
- `services/api/app/models/incident.py`: Sistema de análisis de incidencias (futuro)

**Arquitectura**:
- TinyDB: `services/api/app/tinydb_database.py`
- Supabase: `services/api/app/database_supabase.py`

---

### Anexo C: Compliance y Legal

**GDPR Compliance**:
- ✅ Todos los emails hasheados con SHA256
- ✅ IPs enmascaradas (último octeto)
- ✅ Sin geolocalización precisa (solo país/ciudad)
- ✅ Derecho al olvido: Endpoint `DELETE /telemetry/user/{userId}` borra todos los eventos

**Data Retention**:
- Hot storage: 14-90 días según criticidad
- Cold storage: 6 meses - 2 años
- Eliminación automática post-retention

**Auditoría**:
- Todos los eventos de seguridad retenidos 2 años (compliance)
- Logs de acceso a eventos sensibles (quién consultó qué)

---

**Documento aprobado por**: Nicolás Park (CTO Brasaland)  
**Próxima revisión**: 30 de noviembre, 2026 (post-implementación Fase 1)  
**Versión**: 1.0.0

---

**FIN DEL TELEMETRY_PLAN.MD**
