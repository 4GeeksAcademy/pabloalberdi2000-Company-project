# Guía de Instalación - MCP Server Brasaland

## 📋 Pre-requisitos

- Python 3.10 o superior
- pip o uv (gestor de paquetes)
- Backend API corriendo en `localhost:8000` (o configurar `API_BASE_URL` en `.env`)

## 🚀 Instalación Rápida

### Opción 1: Script Automático (Recomendado)

```bash
cd /Users/alberdi/Desktop/4Geeks/pabloalberdi2000-Company-project

# Ejecutar script de instalación
bash mcps/install.sh

# Activar entorno virtual
source venv-mcp/bin/activate
```

### Opción 2: Manual

```bash
cd /Users/alberdi/Desktop/4Geeks/pabloalberdi2000-Company-project

# Crear entorno virtual
python3 -m venv venv-mcp

# Activar entorno
source venv-mcp/bin/activate

# Instalar dependencias
pip install -r mcps/requirements.txt
```

## ✅ Verificación

Ejecutar verificador de dependencias:

```bash
python3 mcps/check_dependencies.py
```

**Output esperado**:

```
======================================================================
🔍 Verificador de Dependencias MCP Server - Brasaland
======================================================================

📦 Dependencias Requeridas:
----------------------------------------------------------------------
  ✅ FastMCP                                  v0.2.0
  ✅ mcpauth (OAuth middleware)               v0.1.0
  ✅ httpx (HTTP client)                      v0.25.2
  ✅ Pydantic                                 v2.5.3
  ✅ structlog                                v23.2.0
  ✅ python-dotenv                            v1.0.0

📦 Dependencias Opcionales:
----------------------------------------------------------------------
  ✅ langchain-mcp-adapters (para cliente)    v0.1.0

======================================================================
✅ Todas las dependencias requeridas están instaladas
======================================================================
```

## ⚙️ Configuración

### 1. Crear archivo `.env`

```bash
cp mcps/.env.example mcps/.env
```

### 2. Configurar variables (Desarrollo)

Editar `mcps/.env`:

```bash
# Backend API
API_BASE_URL=http://localhost:8000
API_TIMEOUT=5

# OAuth (comentar para desarrollo local)
# OAUTH_ISSUER=https://your-oauth-provider.com
# OAUTH_AUDIENCE=brasaland-mcp-server

# DESARROLLO: Deshabilitar OAuth
OAUTH_DISABLED=true

# MCP Server
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8100
```

⚠️ **IMPORTANTE**: `OAUTH_DISABLED=true` es SOLO para desarrollo local. **NUNCA** usar en producción.

### 3. Configurar variables (Producción)

Para producción, OAuth es **OBLIGATORIO**:

```bash
# Backend API
API_BASE_URL=https://api.brasaland.com
API_TIMEOUT=5

# OAuth 2.1 / OIDC (OBLIGATORIO)
OAUTH_ISSUER=https://auth.brasaland.com
OAUTH_AUDIENCE=brasaland-mcp-server

# NO incluir OAUTH_DISABLED en producción

# MCP Server
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8100
```

## 🚦 Iniciar Servidor

```bash
# Activar entorno virtual (si no está activado)
source venv-mcp/bin/activate

# Iniciar servidor
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

## 🧪 Prueba Rápida

En **otro terminal**:

```bash
# Health check
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

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'fastmcp'"

**Causa**: Dependencias no instaladas.

**Solución**:
```bash
bash mcps/install.sh
# O
pip install -r mcps/requirements.txt
```

### Error: "OAuth es OBLIGATORIO pero mcpauth no está instalado"

**Causa**: `OAUTH_DISABLED=true` no está configurado en `.env` y mcpauth no está instalado.

**Solución (desarrollo)**:
```bash
echo "OAUTH_DISABLED=true" >> mcps/.env
```

**Solución (producción)**:
```bash
pip install mcpauth
# Y configurar OAUTH_ISSUER y OAUTH_AUDIENCE en .env
```

### Error: "Backend API not responding"

**Causa**: Backend en `localhost:8000` no está corriendo.

**Solución**:
```bash
# Verificar backend
curl http://localhost:8000/health

# Si falla, iniciar backend primero
cd services/api
uvicorn app.main:app --reload --port 8000
```

### Error: "Address already in use" (puerto 8100 ocupado)

**Causa**: Otro proceso usando puerto 8100.

**Solución**:
```bash
# Cambiar puerto en .env
echo "MCP_SERVER_PORT=8101" >> mcps/.env

# O matar proceso en puerto 8100
lsof -ti:8100 | xargs kill -9
```

## 📚 Próximos Pasos

Una vez instalado y funcionando:

1. **Leer documentación**: `mcps/README.md`
2. **Ejecutar tests**: `pytest tests/agent/test_mcp_routing.py`
3. **Verificar end-to-end**: Seguir `docs/mcp-verification.md`
4. **Conectar MCP Inspector**: Ver sección de Playground

## 🔐 Nota de Seguridad

**En producción**:
- ✅ OAuth **DEBE** estar habilitado
- ✅ `OAUTH_ISSUER` debe ser válido
- ✅ `OAUTH_AUDIENCE` debe coincidir con tu proveedor OAuth
- ❌ **NUNCA** usar `OAUTH_DISABLED=true`
- ✅ Usar HTTPS (no HTTP)
- ✅ Configurar firewall para puerto 8100

**En desarrollo local**:
- ✅ Puedes usar `OAUTH_DISABLED=true`
- ✅ HTTP localhost está bien
- ⚠️ No exponer puerto 8100 públicamente sin OAuth

---

**Mantenido por**: Lead Distributed AI Architect  
**Última actualización**: 2024-10-26  
**Versión**: 1.0.0
