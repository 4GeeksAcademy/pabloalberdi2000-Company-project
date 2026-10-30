# Brasaland MCP Server

**Model Context Protocol Server** para exponer herramientas de Brasaland como servicio independiente con autenticación OAuth.

## 📋 Descripción

Servidor MCP que expone tools de consulta y gestión de:
- **Incidentes**: Crear, consultar y actualizar estado de tickets
- **Inventario**: Consultar productos y stock (SOLO LECTURA)

### Características

✅ **Transporte HTTP/SSE**: Conexiones remotas vía Server-Sent Events  
✅ **OAuth 2.1 / OIDC**: Autenticación con scopes (`incidents:read`, `incidents:write`, `inventory:read`)  
✅ **Schemas tipados**: Contratos Pydantic para todas las tools  
✅ **Solo lectura estricta**: Inventario rechaza mutaciones con error explícito  
✅ **Audit logging**: Identidades y operaciones logueadas con structlog  
✅ **Timeouts**: 5s default para llamadas al backend  

## 🛠️ Tools Disponibles

| Tool | Scope | Operación | Endpoint Backend |
|------|-------|-----------|------------------|
| `create_incident` | `incidents:write` | Crea incidente | `POST /api/incidents` |
| `update_incident_status` | `incidents:write` | Actualiza estado | `PATCH /api/incidents/{id}/status` |
| `get_incident_status` | `incidents:read` | Consulta ticket | `GET /api/incidents/{id}` |
| `get_inventory_stock` | `inventory:read` | Consulta stock | `GET /inventory/products` |
| `health_check` | - | Verifica servidor | - |

## 📦 Instalación

### 1. Instalar dependencias

```bash
pip install -r mcps/requirements.txt
```

**Dependencias principales**:
- `fastmcp==0.2.0` - Framework MCP
- `mcpauth==0.1.0` - Middleware OAuth
- `httpx==0.25.2` - Cliente HTTP async
- `pydantic==2.5.3` - Schemas tipados
- `structlog==23.2.0` - Logging estructurado

### 2. Configurar variables de entorno

```bash
cp mcps/.env.example mcps/.env
```

Editar `mcps/.env`:

```bash
# Backend API
API_BASE_URL=http://localhost:8000
API_TIMEOUT=5

# OAuth 2.1 / OIDC
OAUTH_ISSUER=https://auth.brasaland.com
OAUTH_AUDIENCE=brasaland-mcp-server

# MCP Server
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8100
```

## 🚀 Uso

### Iniciar servidor

```bash
cd /Users/alberdi/Desktop/4Geeks/pabloalberdi2000-Company-project

python3 mcps/server.py
```

**Output esperado**:

```
======================================================================
🚀 Brasaland MCP Server
======================================================================
Transport: HTTP/SSE
Host: 0.0.0.0:8100
Backend: http://localhost:8000
OAuth: Enabled
======================================================================

Tools disponibles:
  - create_incident (scope: incidents:write)
  - update_incident_status (scope: incidents:write)
  - get_incident_status (scope: incidents:read)
  - get_inventory_stock (scope: inventory:read) [SOLO LECTURA]
  - health_check

======================================================================
Servidor listo para conexiones MCP remotas vía HTTP/SSE
======================================================================
```

### Conectar desde cliente

#### Opción 1: Cliente Python (MCP Adapter)

```python
from services.agent.mcp_adapter import get_mcp_client

# Conectar
client = get_mcp_client()

# Consultar ticket
result = client.get_incident_by_id(ticket_id=482)
print(result)
```

#### Opción 2: LangGraph Agent (integrado)

```python
from services.agent.graph import query_with_agent

# El agente usa MCP automáticamente si mcp_adapter.py está importado
result = query_with_agent("¿En qué estado está el ticket 482?")
print(result["answer"])
```

#### Opción 3: MCP Inspector (Playground)

```bash
npx @modelcontextprotocol/inspector
```

Configurar en el Inspector:
- **Transport**: HTTP/SSE
- **URL**: `http://localhost:8100`
- **Headers** (si OAuth habilitado):
  ```json
  {
    "Authorization": "Bearer <your_token>"
  }
  ```

## 🔐 Autenticación OAuth

### ⚠️ CRÍTICO: Seguridad en Producción

**El servidor MCP implementa validación OAuth OBLIGATORIA en producción**:

- ✅ **Producción**: OAuth 2.1 es **REQUERIDO**. El servidor NO inicia sin configuración OAuth válida.
- ⚠️ **Desarrollo**: OAuth puede deshabilitarse con `OAUTH_DISABLED=true` en `.env`.
- 🔴 **PROHIBIDO**: Usar `OAUTH_DISABLED=true` en producción resultará en rechazo de inicio.

**Comportamiento del servidor**:

```python
# Sin OAUTH_DISABLED=true y sin OAuth configurado
❌ ERROR CRÍTICO: OAuth es OBLIGATORIO pero mcpauth no está instalado
→ Servidor se detiene con exit code 1

# Con OAUTH_DISABLED=true (solo desarrollo)
⚠️  DESARROLLO: OAuth deshabilitado. NUNCA usar en producción
→ Servidor inicia sin autenticación

# Con OAuth configurado correctamente
✅ OAuth configured: issuer=https://auth.brasaland.com
→ Servidor inicia con validación de tokens
```

### Scopes requeridos

| Scope | Permisos |
|-------|----------|
| `incidents:read` | Consultar tickets |
| `incidents:write` | Crear y actualizar tickets |
| `inventory:read` | Consultar inventario |

### Obtener token (ejemplo con Client Credentials)

```bash
curl -X POST https://auth.brasaland.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=<your_client_id>" \
  -d "client_secret=<your_client_secret>" \
  -d "scope=incidents:read incidents:write inventory:read"
```

### Llamar a tool con token

```bash
curl -X POST http://localhost:8100/mcp/tools/get_incident_status \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"ticket_id": 482}'
```

## 🛡️ Seguridad

### Inventario de Solo Lectura

El tool `get_inventory_stock` **rechaza explícitamente** cualquier intención de mutación:

```python
# ❌ RECHAZADO
request = "actualizar stock del producto 123 a 50 unidades"
# Tool detecta keywords ["update", "set", "change"] y retorna error:
# "OPERACIÓN RECHAZADA: get_inventory_stock es SOLO LECTURA"
```

Para modificar inventario, usar el sistema de gestión directamente.

### Ciclo de Vida de Estados

`update_incident_status` usa el endpoint correcto de ciclo de vida:

```
PATCH /api/incidents/{id}/status
```

**Transiciones válidas**:
```
open → in_progress → resolved → closed
```

Transiciones inválidas son rechazadas con **422 Unprocessable Entity**.

## 📊 Logging y Auditoría

El servidor registra:
- Identidad del usuario (OAuth `sub` claim)
- Tool invocada
- Parámetros (sin datos sensibles)
- Success/error
- Timestamp

**Ejemplo de log**:

```json
{
  "event": "incident_created",
  "incident_id": 789,
  "user": "user@brasaland.com",
  "timestamp": "2024-10-26T16:30:45.123Z"
}
```

## 🧪 Testing

### Test manual con Python

```bash
python3 mcps/server.py &  # Iniciar servidor en background

# En otro terminal:
python3 services/agent/mcp_adapter.py
```

**Output esperado**:

```
======================================================================
🧪 Testing MCP Client Adapter
======================================================================

1️⃣  Conectando a servidor MCP...
✅ Conectado exitosamente

2️⃣  Listando tools disponibles...
Tools: ['create_incident', 'update_incident_status', 'get_incident_status', 'get_inventory_stock', 'health_check']

3️⃣  Consultando ticket 482...
Resultado:
{
  "success": true,
  "ticket_id": 482,
  "status": "in_progress",
  ...
}

4️⃣  Consultando inventario...
Resultado:
{
  "success": true,
  "products": [...],
  "readonly_note": "Esta consulta es de solo lectura..."
}

======================================================================
✅ Tests completados
======================================================================
```

## 🔄 Migración desde Tools Directas

### Antes (tools.py)

```python
from services.agent.tools import execute_tool

result = execute_tool("get_incident_by_id", ticket_id=482)
```

### Después (MCP Adapter)

```python
from services.agent.mcp_adapter import execute_tool

result = execute_tool("get_incident_by_id", ticket_id=482)
```

**Drop-in replacement**: La interfaz es idéntica, solo cambiar el import.

## 📁 Estructura

```
mcps/
├── server.py           # Servidor MCP principal
├── requirements.txt    # Dependencias
├── .env.example        # Template de configuración
└── README.md          # Esta documentación

services/agent/
├── mcp_adapter.py      # Cliente MCP (consume server.py)
├── graph.py            # LangGraph agent (usa mcp_adapter.py)
└── tools.py            # [DEPRECATED] Tools directas
```

## 🚧 Limitaciones Conocidas

1. **`list_incidents` no implementado**: MCP Server v1.0 solo tiene `get_incident_status` (consulta individual). Usar `list_incidents` retorna error informativo.

2. **OAuth en desarrollo**: Si `mcpauth` no está configurado, el servidor funciona en **modo dev sin autenticación**. No usar en producción sin OAuth.

3. **Checkpointing**: El servidor MCP es stateless. Para conversaciones multi-turn con memoria, implementar checkpointing en el cliente (LangGraph con `MemorySaver`).

## 📚 Referencias

- [Model Context Protocol Spec](https://spec.modelcontextprotocol.io)
- [FastMCP Docs](https://github.com/jlowin/fastmcp)
- [mcpauth](https://github.com/modelcontextprotocol/mcpauth)
- [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-12)

## 🐛 Troubleshooting

### Error: "fastmcp no instalado"

```bash
pip install fastmcp==0.2.0
```

### Error: "No se pudo conectar a http://localhost:8000"

Verificar que el backend esté corriendo:

```bash
curl http://localhost:8000/health
```

Si no responde, iniciar backend primero.

### Error: "401 Unauthorized"

OAuth está habilitado pero no se envió token válido.

**Solución temporal (dev)**:  
Comentar configuración OAuth en `.env`:

```bash
# OAUTH_ISSUER=https://auth.brasaland.com
# OAUTH_AUDIENCE=brasaland-mcp-server
```

Reiniciar servidor → funcionará sin autenticación.

---

**Autor**: Lead Distributed AI Architect  
**Versión**: 1.0.0  
**Fecha**: 2024-10-26
