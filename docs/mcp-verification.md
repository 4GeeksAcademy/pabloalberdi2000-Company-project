# Guía de Verificación MCP - Brasaland

**Objetivo**: Verificar funcionamiento end-to-end del MCP Server y cliente integrado en LangGraph Agent.

## 📋 Pre-requisitos

### 1. Dependencias instaladas

```bash
# MCP Server
pip install -r mcps/requirements.txt

# Cliente MCP (incluido en requirements-rag.txt)
pip install langchain-mcp-adapters==0.1.0

# Verificar instalación
python3 -c "from fastmcp import FastMCP; print('FastMCP OK')"
python3 -c "from langchain_mcp_adapters import MCPToolAdapter; print('MCP Adapters OK')"
```

### 2. Backend corriendo

El servidor MCP necesita el backend de incidentes corriendo:

```bash
# Verificar backend
curl http://localhost:8000/health

# Esperado: 200 OK
```

Si no está corriendo, iniciar backend primero:

```bash
# Según tu configuración, puede ser:
python3 backend/main.py
# o
uvicorn backend.main:app --reload
```

### 3. Variables de entorno

Crear `mcps/.env`:

```bash
cp mcps/.env.example mcps/.env
```

**Mínimo requerido** (sin OAuth para dev):

```bash
API_BASE_URL=http://localhost:8000
API_TIMEOUT=5
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8100
```

## 🚀 Fase 1: Verificar MCP Server

### 1.1 Iniciar servidor

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
OAuth: Disabled (dev mode)
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

**✅ Criterio de éxito**: Servidor inicia sin errores y muestra 5 tools.

### 1.2 Health check

En **otro terminal**:

```bash
curl -X POST http://localhost:8100/mcp/tools/health_check \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Respuesta esperada**:

```json
{
  "status": "healthy",
  "server": "brasaland-mcp-server",
  "version": "1.0.0",
  "backend_url": "http://localhost:8000",
  "oauth_enabled": false
}
```

**✅ Criterio de éxito**: Status 200 y `"status": "healthy"`.

### 1.3 Consultar incidente (tool read)

```bash
curl -X POST http://localhost:8100/mcp/tools/get_incident_status \
  -H "Content-Type: application/json" \
  -d '{"ticket_id": 482}'
```

**Respuesta esperada** (si ticket 482 existe):

```json
{
  "success": true,
  "ticket_id": 482,
  "status": "in_progress",
  "category": "técnico",
  "origin": "cliente",
  "description": "Error en sistema de pedidos",
  "created_at": "2024-10-25T10:30:00",
  "updated_at": "2024-10-26T15:45:00"
}
```

**Si ticket no existe**:

```json
{
  "success": false,
  "error": "Ticket 482 no encontrado",
  "code": "NOT_FOUND"
}
```

**✅ Criterio de éxito**: Status 200 y respuesta estructurada (success true o false con error).

### 1.4 Consultar inventario (read-only)

```bash
curl -X POST http://localhost:8100/mcp/tools/get_inventory_stock \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'
```

**Respuesta esperada**:

```json
{
  "success": true,
  "products": [
    {"id": 1, "name": "Producto A", "stock": 100, ...},
    {"id": 2, "name": "Producto B", "stock": 50, ...}
  ],
  "count": 5,
  "readonly_note": "Esta consulta es de solo lectura. Para modificar inventario, usa el sistema de gestión."
}
```

**✅ Criterio de éxito**: Status 200, lista de productos, y `readonly_note` presente.

### 1.5 Crear incidente (tool write)

```bash
curl -X POST http://localhost:8100/mcp/tools/create_incident \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Test desde MCP",
    "category": "técnico",
    "origin": "sistema",
    "priority": "medium"
  }'
```

**Respuesta esperada**:

```json
{
  "success": true,
  "incident_id": 789,
  "status": "open",
  "message": "Incidente 789 creado exitosamente"
}
```

**✅ Criterio de éxito**: Status 201, `success: true`, y nuevo `incident_id`.

### 1.6 Actualizar estado (tool write con ciclo de vida)

```bash
curl -X POST http://localhost:8100/mcp/tools/update_incident_status \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": 789,
    "new_status": "in_progress",
    "comment": "Asignado a equipo técnico"
  }'
```

**Respuesta esperada**:

```json
{
  "success": true,
  "ticket_id": 789,
  "old_status": "open",
  "new_status": "in_progress",
  "message": "Ticket 789 actualizado a 'in_progress'"
}
```

**✅ Criterio de éxito**: Status 200, `success: true`, transición de estado correcta.

## 🧪 Fase 2: Verificar Cliente MCP

### 2.1 Test del adaptador

```bash
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
  ...
}

4️⃣  Consultando inventario...
Resultado:
{
  "success": true,
  "products": [...],
  "count": 5,
  "readonly_note": "Esta consulta es de solo lectura..."
}

======================================================================
✅ Tests completados
======================================================================
```

**✅ Criterio de éxito**: 4 tests completan sin errores.

### 2.2 Verificar interfaz de compatibility

```python
# Abrir REPL de Python
python3

from services.agent.mcp_adapter import execute_tool, AVAILABLE_TOOLS

# Listar tools registradas
print(list(AVAILABLE_TOOLS.keys()))
# Esperado: ['get_incident_by_id', 'list_incidents', 'get_inventory_products', 'create_incident', 'update_incident_status']

# Ejecutar tool
result = execute_tool("get_incident_by_id", ticket_id=482)
print(result)
# Esperado: {'success': True, 'ticket_id': 482, ...}
```

**✅ Criterio de éxito**: `execute_tool()` funciona con misma interfaz que `tools.py`.

## 🤖 Fase 3: Verificar Integración con LangGraph

### 3.1 Migrar graph.py a usar MCP

Editar `services/agent/graph.py`:

**Buscar línea 32**:
```python
from services.agent.tools import execute_tool, AVAILABLE_TOOLS
```

**Reemplazar por**:
```python
from services.agent.mcp_adapter import execute_tool, AVAILABLE_TOOLS
```

**✅ Verificación**: La única línea que cambia es el import.

### 3.2 Test del agent con MCP

```bash
python3 services/agent/graph.py "¿En qué estado está el ticket 482?"
```

**Output esperado**:

```
======================================================================
🤖 Ejecutando Agent Graph para: '¿En qué estado está el ticket 482?'
======================================================================

[ROUTER_NODE] Analizando intent de: '¿En qué estado está el ticket 482?'
[ROUTER_NODE] ✅ Decisión: tool

[TOOL_CALLING_NODE] Procesando pregunta para tool
[TOOL_CALLING_NODE] 🔧 Llamando tool: get_incident_by_id con params: {'ticket_id': '482'}
[TOOL_CALLING_NODE] ✅ Tool ejecutada: success=True

[SYNTHESIS_NODE] Generando respuesta final
[SYNTHESIS_NODE] ✅ Respuesta generada

======================================================================
✅ Agent Graph completado
======================================================================

📊 Metadata:
  - routing_decision: tool
  - tool_name: get_incident_by_id
  - tool_success: True

💬 Respuesta:
El ticket 482 está en estado "in_progress" (en progreso). Es un incidente técnico reportado por un cliente, con la descripción "Error en sistema de pedidos". Fue creado el 25 de octubre y actualizado por última vez el 26 de octubre.
```

**✅ Criterio de éxito**: 
- Router detecta necesidad de tool
- Tool se ejecuta via MCP (logs de `mcp_adapter.py`)
- Respuesta es coherente con datos del ticket

### 3.3 Test de routing multi-source

```bash
python3 services/agent/graph.py "¿Cuántos locales tiene Brasaland y cuál es el estado del ticket 482?"
```

**Output esperado**:

```
[ROUTER_NODE] ✅ Decisión: both

[TOOL_CALLING_NODE] 🔧 Llamando tool: get_incident_by_id
[TOOL_CALLING_NODE] ✅ Tool ejecutada: success=True

[SYNTHESIS_NODE] Generando respuesta final
[SYNTHESIS_NODE] ✅ Respuesta generada

💬 Respuesta:
Brasaland tiene 14 locales en total: 10 en USA, 2 en Colombia y 2 en España.

Respecto al ticket 482, está actualmente en estado "in_progress" (en progreso). Es un incidente técnico reportado por un cliente.
```

**✅ Criterio de éxito**: 
- Respuesta combina RAG (conocimiento de locales) + Tool (estado del ticket)
- Ambas fuentes se sintetizan correctamente

### 3.4 Test de fallback honesto

Consultar un ticket inexistente:

```bash
python3 services/agent/graph.py "¿Cuál es el estado del ticket 99999?"
```

**Output esperado**:

```
[TOOL_CALLING_NODE] ✅ Tool ejecutada: success=False

[SYNTHESIS_NODE] ⚠️  Tool falló, respuesta honesta

💬 Respuesta:
Lo siento, no pude obtener esa información en este momento. Error: Ticket 99999 no encontrado en el sistema
```

**✅ Criterio de éxito**: No alucina datos, responde honestamente con el error.

## 🎮 Fase 4: MCP Playground (Opcional)

### 4.1 Instalar MCP Inspector

```bash
npm install -g @modelcontextprotocol/inspector
```

### 4.2 Iniciar Inspector

```bash
npx @modelcontextprotocol/inspector
```

Esto abre UI en `http://localhost:5173`.

### 4.3 Configurar conexión

En el Inspector UI:

1. **Transport**: Seleccionar "HTTP/SSE"
2. **URL**: `http://localhost:8100`
3. **Headers**: (dejar vacío si OAuth deshabilitado)
4. Clic en **Connect**

### 4.4 Explorar tools

En el panel izquierdo:
- Ver lista de 5 tools
- Clic en `get_incident_status`
- Completar parámetros: `{"ticket_id": 482}`
- Clic en **Execute**

**✅ Criterio de éxito**: Inspector muestra respuesta JSON del tool.

### 4.5 Test de read-only enforcement

En Inspector:
- Seleccionar `get_inventory_stock`
- En el campo de "context" o "prompt" (si lo hay), agregar:
  ```
  I want to update the stock of product 123 to 50 units
  ```
- Ejecutar

**Respuesta esperada**:

```json
{
  "success": false,
  "error": "OPERACIÓN RECHAZADA: get_inventory_stock es SOLO LECTURA. No se permiten operaciones de modificación de inventario via MCP.",
  "code": "READ_ONLY_VIOLATION"
}
```

**✅ Criterio de éxito**: Tool rechaza intención de mutación explícitamente.

## 📊 Matriz de Verificación

| Fase | Test | Estado | Notas |
|------|------|--------|-------|
| 1.1 | Servidor inicia | ⬜ | 5 tools mostradas |
| 1.2 | Health check | ⬜ | Status 200, "healthy" |
| 1.3 | get_incident_status (read) | ⬜ | Datos de ticket o 404 |
| 1.4 | get_inventory_stock (read) | ⬜ | Lista productos + readonly_note |
| 1.5 | create_incident (write) | ⬜ | Nuevo incident_id |
| 1.6 | update_incident_status (write) | ⬜ | Transición de estado |
| 2.1 | Cliente MCP adapter | ⬜ | 4 tests completos |
| 2.2 | Interfaz compatibility | ⬜ | execute_tool() funciona |
| 3.1 | Migración graph.py | ⬜ | Solo import cambió |
| 3.2 | Agent con MCP (tool) | ⬜ | Routing + tool + síntesis |
| 3.3 | Agent multi-source (both) | ⬜ | RAG + tool combinados |
| 3.4 | Fallback honesto | ⬜ | No alucina, muestra error |
| 4.1-4.5 | MCP Inspector (opcional) | ⬜ | UI funcional |

## 🐛 Troubleshooting

### Error: "Connection refused" al conectar cliente

**Causa**: Servidor MCP no está corriendo.

**Solución**:
```bash
# Terminal 1: Iniciar servidor
python3 mcps/server.py

# Terminal 2: Ejecutar cliente
python3 services/agent/mcp_adapter.py
```

### Error: "Backend API not responding"

**Causa**: Backend de incidentes no está corriendo.

**Solución**:
```bash
# Verificar
curl http://localhost:8000/health

# Si falla, iniciar backend primero
```

### Error: "Tool 'list_incidents' not available"

**Causa**: `list_incidents` no está implementado en MCP Server v1.0.

**Solución**: Usar `get_incident_status` para consultas individuales. Implementar `list_incidents` en servidor si se necesita.

### Error: "ModuleNotFoundError: langchain_mcp_adapters"

**Causa**: Dependencia no instalada.

**Solución**:
```bash
pip install langchain-mcp-adapters==0.1.0
```

### OAuth 401 Unauthorized

**Causa**: OAuth habilitado pero no se envió token.

**Solución temporal (dev)**:
```bash
# Editar mcps/.env y comentar OAuth
# OAUTH_ISSUER=...
# OAUTH_AUDIENCE=...

# Reiniciar servidor
```

## ✅ Checklist Final

Antes de considerar MCP verificado:

- [ ] Servidor MCP inicia sin errores
- [ ] 5 tools disponibles (4 operativas + health_check)
- [ ] Health check responde OK
- [ ] Read tools funcionan (get_incident_status, get_inventory_stock)
- [ ] Write tools funcionan (create_incident, update_incident_status)
- [ ] Inventario rechaza mutaciones con error explícito
- [ ] Cliente MCP adapter conecta y ejecuta tools
- [ ] Interfaz `execute_tool()` compatible con tools.py
- [ ] LangGraph Agent usa MCP (solo cambió import)
- [ ] Routing funciona: tool, rag, both
- [ ] Fallback honesto sin alucinación
- [ ] (Opcional) MCP Inspector conecta y ejecuta tools

## 📚 Próximos Pasos

Una vez verificado MCP:

1. **Deprecar tools.py**: Agregar warning de deprecación
2. **Implementar checkpointing**: MemorySaver en graph.py
3. **Tests automatizados**: pytest para tools MCP
4. **OAuth en producción**: Configurar con proveedor real
5. **Monitoring**: Métricas de latencia y errores de tools
6. **Rate limiting**: Proteger servidor de abuso

---

**Autor**: Lead Distributed AI Architect  
**Versión**: 1.0.0  
**Última actualización**: 2024-10-26
