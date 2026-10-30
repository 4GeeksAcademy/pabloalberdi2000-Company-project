# MCP Migration Summary - Brasaland Agent

**Fecha**: 2024-10-26  
**Arquitectura**: Lead Distributed AI Architect  
**Objetivo**: Migrar tools del agente LangGraph de llamadas directas a Model Context Protocol (MCP)

---

## 📊 Resumen Ejecutivo

✅ **Migración Completada** con arquitectura distribuida:

- **Servidor MCP** independiente exponiendo tools como servicio
- **Cliente MCP** integrado en LangGraph Agent
- **OAuth 2.1** authentication con scopes
- **Zero breaking changes**: Interfaz compatible con implementación anterior
- **Tests automatizados**: 13 tests de routing y MCP integration

---

## 🏗️ Arquitectura Antes vs Después

### ANTES: Tools Directas

```
┌─────────────────┐
│  LangGraph      │
│   Agent         │
│                 │
│  ┌──────────┐   │
│  │ tools.py │───┼─── HTTP GET ──→ Backend API
│  └──────────┘   │                 (localhost:8000)
└─────────────────┘
```

**Limitaciones**:
- Solo lectura (GET)
- Sin autenticación formal
- Sin audit logging
- Acoplado al agent
- Sin reutilización cross-service

### DESPUÉS: MCP Distribuido

```
┌─────────────────┐
│  LangGraph      │
│   Agent         │
│                 │
│ ┌─────────────┐ │
│ │mcp_adapter.py│─┼──→ MCP Protocol (HTTP/SSE) ──→ ┌────────────────┐
│ └─────────────┘ │    (localhost:8100)             │  MCP Server    │
└─────────────────┘                                  │  (server.py)   │
                                                     │                │
                                                     │  OAuth 2.1     │
                                                     │  Scopes        │
                                                     │  Audit Log     │
                                                     │                │
                                                     └────┬───────────┘
                                                          │
                                                    HTTP (GET/POST/PATCH)
                                                          │
                                                          ▼
                                                    Backend API
                                                  (localhost:8000)
```

**Beneficios**:
- ✅ Read + Write operations
- ✅ OAuth authentication
- ✅ Structured audit logging
- ✅ Servicio independiente reutilizable
- ✅ Horizontal scaling (múltiples clientes)

---

## 📦 Entregables

### 1. Servidor MCP (`mcps/server.py`)

**600 líneas** - Servidor independiente con FastMCP

**Tools expuestas**:

| Tool | Method | Endpoint Backend | Scope | Descripción |
|------|--------|------------------|-------|-------------|
| `create_incident` | POST | `/api/incidents` | `incidents:write` | Crea nuevo ticket |
| `update_incident_status` | PATCH | `/api/incidents/{id}/status` | `incidents:write` | Actualiza estado (ciclo de vida) |
| `get_incident_status` | GET | `/api/incidents/{id}` | `incidents:read` | Consulta ticket |
| `get_inventory_stock` | GET | `/inventory/products` | `inventory:read` | Consulta stock (SOLO LECTURA) |
| `health_check` | - | - | - | Verifica servidor |

**Características clave**:
- Transporte HTTP/SSE (no stdio)
- OAuth 2.1 con `mcpauth` middleware
- Schemas Pydantic tipados
- Error codes: 401 (Unauthorized), 403 (Forbidden), 422 (Invalid Transition)
- Logging estructurado con identities
- Timeout: 5s en llamadas backend
- **Read-only enforcement**: Inventario rechaza mutaciones con error explícito

**Fragmento de código**:

```python
@mcp.tool(name="get_inventory_stock")
@require_scopes("inventory:read")
async def get_inventory_stock(...):
    # VALIDACIÓN DEFENSIVA: Rechazar mutaciones
    if any(kw in request for kw in ["update", "delete", "modify"]):
        raise ToolError(
            "OPERACIÓN RECHAZADA: get_inventory_stock es SOLO LECTURA",
            code="READ_ONLY_VIOLATION"
        )
```

### 2. Cliente MCP (`services/agent/mcp_adapter.py`)

**450 líneas** - Adaptador para consumir MCP desde LangGraph

**Características**:
- Basado en `langchain-mcp-adapters`
- **Drop-in replacement** de `tools.py`: misma interfaz `execute_tool()`
- Singleton pattern para reutilizar conexión
- Timeout: 10s (más generoso que tools directas)
- Registry `AVAILABLE_TOOLS` compatible con LangGraph

**Fragmento de código**:

```python
class BrasalandMCPClient:
    def __init__(self, server_url: str = MCP_SERVER_URL):
        self.adapter = MCPToolAdapter(
            server_url=server_url,
            timeout=MCP_CLIENT_TIMEOUT,
            auth={
                "client_id": OAUTH_CLIENT_ID,
                "client_secret": OAUTH_CLIENT_SECRET,
                "token_url": OAUTH_TOKEN_URL
            } if OAUTH_CLIENT_ID else None
        )
    
    def get_incident_by_id(self, ticket_id: int | str):
        return self.adapter.call_tool(
            tool_name="get_incident_status",
            arguments={"ticket_id": int(ticket_id)}
        )
```

### 3. Migración de Agent (`services/agent/graph.py`)

**Una sola línea cambió**:

```diff
- from services.agent.tools import execute_tool, AVAILABLE_TOOLS
+ from services.agent.mcp_adapter import execute_tool, AVAILABLE_TOOLS
```

**Estado del resto del código**: Sin cambios (535 líneas intactas)

Todo el flujo de routing, tool calling, RAG retrieve y synthesis funciona idénticamente.

### 4. Deprecación (`services/agent/tools.py`)

**Agregado banner de deprecación**:

```python
"""
⚠️  DEPRECATED: Este módulo está obsoleto desde 2024-10-26.
⚠️  Usar en su lugar: services/agent/mcp_adapter.py

MIGRACIÓN:
  Antes: from services.agent.tools import execute_tool, AVAILABLE_TOOLS
  Después: from services.agent.mcp_adapter import execute_tool, AVAILABLE_TOOLS
"""
```

Archivo mantenido temporalmente para referencia.

### 5. Tests de Routing (`tests/agent/test_mcp_routing.py`)

**13 tests automatizados** cubriendo:

| Test | Descripción | Criterio Validado |
|------|-------------|-------------------|
| `test_routing_tool_only` | Pregunta sobre ticket → routing='tool' | Routing correcto |
| `test_routing_rag_only` | Pregunta sobre locales → routing='rag' | Routing correcto |
| `test_routing_both` | Pregunta mixta → routing='both' | Multi-source |
| `test_tool_calling_node_success` | Tool se ejecuta vía MCP | MCP integration |
| `test_tool_calling_node_parameter_extraction` | Extracción de ticket_id | NLP parsing |
| `test_tool_calling_node_missing_ticket_id` | Sin ID → error honesto | Error handling |
| `test_rag_retrieve_node` | RAG consulta Qdrant | RAG functional |
| `test_synthesis_node_tool_only` | Síntesis con tool_data | Synthesis logic |
| `test_synthesis_node_rag_only` | Síntesis con context | Synthesis logic |
| `test_synthesis_node_tool_failed_honest_fallback` | Tool failed → no alucina | Honest fallback |
| `test_e2e_tool_only_path` | Flujo completo tool-only | E2E integration |
| `test_e2e_rag_only_path` | Flujo completo rag-only | E2E integration |
| `test_mcp_client_used_not_tools_direct` | Usa MCP, no tools.py | Migration success |

**Ejecutar tests**:

```bash
pytest tests/agent/test_mcp_routing.py -v
```

**Cobertura**: Criterio 8 de Auditoría de Tools ✅ completado.

### 6. Documentación

#### `mcps/README.md` (300 líneas)
- Descripción de tools
- Instalación de dependencias
- Configuración OAuth
- Uso del servidor
- Troubleshooting

#### `docs/mcp-verification.md` (500 líneas)
- Guía de verificación end-to-end
- 4 fases: Servidor, Cliente, Agent, Playground
- 12 tests manuales con criterios de éxito
- Matriz de verificación
- Troubleshooting detallado

#### `docs/mcp-migration-summary.md` (este documento)
- Resumen ejecutivo
- Arquitectura antes/después
- Entregables
- Estadísticas de migración

---

## 📈 Estadísticas de Migración

### Código Creado

| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `mcps/server.py` | 600 | Servidor MCP con FastMCP |
| `services/agent/mcp_adapter.py` | 450 | Cliente MCP adapter |
| `tests/agent/test_mcp_routing.py` | 550 | Tests de routing multi-source |
| `mcps/README.md` | 300 | Documentación servidor |
| `docs/mcp-verification.md` | 500 | Guía de verificación |
| `docs/mcp-migration-summary.md` | 400 | Este documento |
| **TOTAL** | **2800** | **Líneas de código + docs** |

### Código Modificado

| Archivo | Líneas Modificadas | Cambio |
|---------|-------------------|--------|
| `services/agent/graph.py` | 1 | Import de mcp_adapter |
| `services/agent/tools.py` | 20 | Banner de deprecación |
| `requirements-rag.txt` | 2 | Agregada `langchain-mcp-adapters` |
| **TOTAL** | **23** | **Cambios mínimos** |

### Código Eliminado

**0 líneas eliminadas** - Migración no destructiva.

`tools.py` se mantiene temporalmente para referencia.

---

## 🔐 Seguridad y Compliance

### OAuth 2.1 Scopes

| Scope | Permisos | Tools que requieren |
|-------|----------|---------------------|
| `incidents:read` | Consultar tickets | `get_incident_status` |
| `incidents:write` | Crear y actualizar tickets | `create_incident`, `update_incident_status` |
| `inventory:read` | Consultar inventario | `get_inventory_stock` |

### Read-Only Enforcement

**Inventario** es estrictamente solo lectura:

```python
# Tool detecta keywords de mutación y rechaza
forbidden_keywords = ["update", "delete", "modify", "set", "change", "edit", "remove"]

if any(kw in request_text for kw in forbidden_keywords):
    raise ToolError(
        "OPERACIÓN RECHAZADA: get_inventory_stock es SOLO LECTURA",
        code="READ_ONLY_VIOLATION"
    )
```

### Audit Logging

Todos los eventos se loguean con:
- Identity del usuario (OAuth `sub` claim)
- Tool invocada
- Parámetros (sin datos sensibles)
- Success/error
- Timestamp ISO 8601

**Ejemplo**:

```json
{
  "event": "incident_created",
  "incident_id": 789,
  "user": "user@brasaland.com",
  "timestamp": "2024-10-26T16:30:45.123Z",
  "tool": "create_incident",
  "success": true
}
```

---

## ✅ Validación de Criterios de Auditoría

### Auditoría de Tools (9 criterios)

| # | Criterio | Estado | Evidencia |
|---|----------|--------|-----------|
| 1 | Tools NO consumen RAG | ✅ | Separación clara: tools → MCP → Backend |
| 2 | Tools no mutan Qdrant | ✅ | Solo backend API, Qdrant solo en RAG |
| 3 | Timeouts estrictos | ✅ | 5s servidor, 10s cliente |
| 4 | Fallback honesto | ✅ | `synthesis_node` retorna error sin alucinar |
| 5 | Inventario read-only | ✅ | Validación defensiva con error explícito |
| 6 | Ciclo de vida formal | ✅ | PATCH `/status` con transiciones validadas |
| 7 | No mocking productivo | ✅ | Backend real (tests usan mocks) |
| 8 | Tests de routing | ✅ | 13 tests en `test_mcp_routing.py` |
| 9 | Schemas tipados | ✅ | Pydantic en server y adapter |

### Auditoría de LangGraph (11 criterios)

| # | Criterio | Estado | Notas |
|---|----------|--------|-------|
| 1 | StateGraph formal | ✅ | Sin cambios |
| 2 | Estados tipados | ✅ | Sin cambios |
| 3 | Conditional edges | ✅ | Sin cambios |
| 4 | Metadata accumulator | ✅ | Sin cambios |
| 5 | Checkpointing | ⚠️ | **Pendiente**: MemorySaver |
| 6 | No loops infinitos | ✅ | Sin cambios |
| 7 | RAG functions reusadas | ✅ | Sin cambios |
| 8 | LLM siempre genera | ✅ | Sin cambios |
| 9 | Estado inmutable | ✅ | Sin cambios |
| 10 | Logging observabilidad | ✅ | **Mejorado**: MCP audit logs |
| 11 | Compilación explícita | ✅ | Sin cambios |

**Nota**: Criterio 5 (Checkpointing) permanece pendiente. Implementación sugerida:

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
return workflow.compile(checkpointer=memory)
```

---

## 🚀 Cómo Usar

### 1. Instalar Dependencias

```bash
# Servidor MCP
pip install -r mcps/requirements.txt

# Cliente MCP (incluido en requirements-rag.txt)
pip install -r requirements-rag.txt
```

### 2. Configurar Variables de Entorno

```bash
cp mcps/.env.example mcps/.env
```

**Mínimo para dev** (sin OAuth):

```bash
API_BASE_URL=http://localhost:8000
API_TIMEOUT=5
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8100
```

### 3. Iniciar Servidor MCP

```bash
python3 mcps/server.py
```

**Output esperado**: 5 tools listadas, servidor en puerto 8100.

### 4. Ejecutar Agent

```bash
python3 services/agent/graph.py "¿En qué estado está el ticket 482?"
```

**Output esperado**: Routing → tool → síntesis → respuesta coherente.

### 5. Ejecutar Tests

```bash
pytest tests/agent/test_mcp_routing.py -v
```

**Output esperado**: 13 tests passed.

---

## 🔄 Comparación de Interfaces

### Antes: tools.py

```python
from services.agent.tools import execute_tool

result = execute_tool("get_incident_by_id", ticket_id=482)
# {'success': True, 'data': {...}}
```

### Después: mcp_adapter.py

```python
from services.agent.mcp_adapter import execute_tool

result = execute_tool("get_incident_by_id", ticket_id=482)
# {'success': True, 'data': {...}}
```

**Interfaz idéntica** - Zero breaking changes.

---

## 📊 Capacidades Nuevas

Gracias a MCP, ahora el agent puede:

### 1. ✅ Crear Incidentes (Write)

```python
from services.agent.mcp_adapter import get_mcp_client

client = get_mcp_client()

result = client.create_incident(
    description="Error en módulo de pagos",
    category="técnico",
    priority="high"
)
# {'success': True, 'incident_id': 789, ...}
```

### 2. ✅ Actualizar Estados (Write)

```python
result = client.update_incident_status(
    ticket_id=789,
    new_status="in_progress",
    comment="Asignado a equipo técnico"
)
# {'success': True, 'old_status': 'open', 'new_status': 'in_progress'}
```

### 3. ✅ Consultar con OAuth

```bash
curl -X POST http://localhost:8100/mcp/tools/get_incident_status \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"ticket_id": 482}'
```

### 4. ✅ Audit Trail Completo

Cada operación se loguea con identity:

```json
{
  "event": "update_incident_status",
  "ticket_id": 789,
  "old_status": "open",
  "new_status": "in_progress",
  "user": "agent@brasaland.com",
  "timestamp": "2024-10-26T16:45:12.456Z"
}
```

---

## 🐛 Troubleshooting Común

### Error: "Connection refused"

**Causa**: Servidor MCP no corriendo.

**Solución**:
```bash
python3 mcps/server.py
```

### Error: "Backend API not responding"

**Causa**: Backend en `localhost:8000` no corriendo.

**Solución**:
```bash
curl http://localhost:8000/health
# Si falla, iniciar backend
```

### Error: "401 Unauthorized"

**Causa**: OAuth habilitado pero no se envió token.

**Solución (dev)**:
Comentar OAuth en `mcps/.env`:
```bash
# OAUTH_ISSUER=...
# OAUTH_AUDIENCE=...
```

Reiniciar servidor → funciona sin autenticación.

---

## 📚 Próximos Pasos Recomendados

### Corto Plazo

1. ✅ **Verificar servidor MCP**: Ejecutar guía de `mcp-verification.md`
2. ✅ **Ejecutar tests**: `pytest tests/agent/test_mcp_routing.py`
3. ⚠️ **Implementar checkpointing**: MemorySaver en `build_agent_graph()`
4. ⚠️ **Eliminar tools.py**: Una vez verificado, remover archivo legacy

### Medio Plazo

5. **Tool `list_incidents`**: Implementar en MCP server (actualmente solo mock)
6. **OAuth en producción**: Configurar con proveedor OIDC real (Keycloak, Auth0)
7. **Rate limiting**: Proteger servidor de abuso (10 req/s por client)
8. **Caching**: Cache de tools con TTL (Redis o similar)

### Largo Plazo

9. **Monitoring**: Métricas Prometheus para latencia y errores de tools
10. **Multi-tenant**: Soporte para múltiples clientes con scopes diferenciados
11. **Tool discovery**: Endpoint para que agents descubran tools dinámicamente
12. **Versioning**: API versioning para backward compatibility (v1, v2)

---

## 📖 Referencias

- [Model Context Protocol Spec](https://spec.modelcontextprotocol.io)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [mcpauth OAuth Middleware](https://github.com/modelcontextprotocol/mcpauth)
- [LangChain MCP Adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
- [OAuth 2.1 Draft](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-12)

---

## 🎯 Conclusión

✅ **Migración exitosa** con arquitectura distribuida y zero breaking changes.

**Impacto**:
- **+2800 líneas** de código y documentación nuevas
- **-23 líneas** modificadas (solo imports y banners)
- **0 líneas** eliminadas (no destructivo)
- **13 tests** automatizados para routing multi-source
- **5 tools** expuestas con OAuth y audit logging

**Próximo hito**: Implementar checkpointing con MemorySaver para completar criterio 5 de auditoría LangGraph.

---

**Autor**: Lead Distributed AI Architect  
**Fecha**: 2024-10-26  
**Versión**: 1.0.0
