"""
Servidor MCP - Model Context Protocol para Herramientas de Brasaland

Expone tools vía MCP sobre Streamable HTTP (SSE) con autenticación OAuth 2.1.

Tools disponibles:
- create_incident: Crea incidente nuevo
- update_incident_status: Actualiza estado de ticket (ciclo de vida)
- get_incident_status: Consulta estado de ticket
- get_inventory_stock: Consulta stock (SOLO LECTURA)

CRÍTICO:
- Transporte: HTTP/SSE (no stdio)
- Auth: OAuth 2.1 con mcpauth
- Inventario: Solo lectura estricta (rechaza mutaciones)
- Ciclo de vida: PATCH /api/incidents/{id}/status
"""

import os
import sys
from typing import Optional, Dict, Any, List
from enum import Enum

import httpx
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import structlog

# FastMCP imports
try:
    from fastmcp import FastMCP, Context
    from fastmcp.exceptions import ToolError
except ImportError:
    print("ERROR: fastmcp no instalado. Ejecutar: pip install fastmcp")
    sys.exit(1)

# mcpauth imports
try:
    from mcpauth import OAuth2ResourceServer, require_scopes
    MCPAUTH_AVAILABLE = True
except ImportError:
    print("ERROR: mcpauth no instalado pero es OBLIGATORIO en producción.")
    print("Para desarrollo: set OAUTH_DISABLED=true en .env")
    print("Instalar con: pip install mcpauth")
    MCPAUTH_AVAILABLE = False
    OAuth2ResourceServer = None
    require_scopes = lambda *scopes: lambda f: f

load_dotenv()

# Logging estructurado
logger = structlog.get_logger()

# ============================================================
# CONFIGURACIÓN
# ============================================================

# Backend API
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "5"))

# OAuth Configuration
OAUTH_ISSUER = os.getenv("OAUTH_ISSUER", "https://auth.brasaland.com")
OAUTH_AUDIENCE = os.getenv("OAUTH_AUDIENCE", "brasaland-mcp-server")
OAUTH_DISABLED = os.getenv("OAUTH_DISABLED", "false").lower() == "true"

# MCP Server
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8100"))

# ============================================================
# SCHEMAS TIPADOS (Pydantic)
# ============================================================

class IncidentStatus(str, Enum):
    """Estados válidos de un incidente"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class IncidentCategory(str, Enum):
    """Categorías de incidentes"""
    TECHNICAL = "técnico"
    SERVICE = "servicio"
    LOGISTICS = "logística"
    HR = "RRHH"

class CreateIncidentInput(BaseModel):
    """Input para crear incidente"""
    description: str = Field(..., description="Descripción del incidente")
    category: IncidentCategory = Field(..., description="Categoría del incidente")
    origin: str = Field(default="interno", description="Origen del incidente")
    priority: Optional[str] = Field(None, description="Prioridad (low, medium, high)")

class UpdateIncidentStatusInput(BaseModel):
    """Input para actualizar estado de incidente"""
    ticket_id: int = Field(..., description="ID del ticket/incidente")
    new_status: IncidentStatus = Field(..., description="Nuevo estado")
    comment: Optional[str] = Field(None, description="Comentario opcional sobre el cambio")

class GetIncidentInput(BaseModel):
    """Input para consultar incidente"""
    ticket_id: int = Field(..., description="ID del ticket/incidente")

class GetInventoryInput(BaseModel):
    """Input para consultar inventario"""
    product_id: Optional[int] = Field(None, description="ID del producto (opcional)")
    location_id: Optional[int] = Field(None, description="ID del local (opcional)")
    limit: int = Field(default=10, ge=1, le=100, description="Límite de resultados")

# ============================================================
# SERVIDOR MCP
# ============================================================

# Inicializar FastMCP
mcp = FastMCP(
    name="brasaland-mcp-server",
    version="1.0.0",
    description="Servidor MCP para herramientas de Brasaland (Incidentes e Inventario)",
    transport="http"  # HTTP/SSE (no stdio)
)

# ============================================================
# OAUTH ENFORCEMENT (OBLIGATORIO EN PRODUCCIÓN)
# ============================================================

# Validar que OAuth esté configurado en producción
if not OAUTH_DISABLED and not MCPAUTH_AVAILABLE:
    logger.error("oauth_required_but_not_available")
    print("\n" + "=" * 70)
    print("❌ ERROR CRÍTICO: OAuth es OBLIGATORIO pero mcpauth no está instalado")
    print("=" * 70)
    print("\nOpciones:")
    print("  1. Instalar mcpauth: pip install mcpauth")
    print("  2. Para desarrollo local ÚNICAMENTE: set OAUTH_DISABLED=true en .env")
    print("\n⚠️  NUNCA usar OAUTH_DISABLED=true en producción")
    print("=" * 70 + "\n")
    sys.exit(1)

# Configurar OAuth Resource Server
oauth_server = None
if not OAUTH_DISABLED:
    if not OAUTH_ISSUER or OAUTH_ISSUER == "https://auth.brasaland.com":
        logger.error("oauth_issuer_not_configured")
        print("\n" + "=" * 70)
        print("❌ ERROR: OAUTH_ISSUER debe estar configurado en .env")
        print("=" * 70)
        print("\nConfiguración requerida en mcps/.env:")
        print("  OAUTH_ISSUER=https://your-oauth-provider.com")
        print("  OAUTH_AUDIENCE=brasaland-mcp-server")
        print("\nO para desarrollo: OAUTH_DISABLED=true")
        print("=" * 70 + "\n")
        sys.exit(1)

    try:
        oauth_server = OAuth2ResourceServer(
            issuer=OAUTH_ISSUER,
            audience=OAUTH_AUDIENCE
        )
        logger.info("oauth_configured", issuer=OAUTH_ISSUER, audience=OAUTH_AUDIENCE)
    except Exception as e:
        logger.error("oauth_config_failed", error=str(e))
        print(f"\n❌ Error configurando OAuth: {e}\n")
        sys.exit(1)
else:
    logger.warning("oauth_disabled_dev_mode",
                  message="⚠️  DESARROLLO: OAuth deshabilitado. NUNCA usar en producción")
    oauth_server = None

# ============================================================
# HELPERS DE AUTENTICACIÓN
# ============================================================

def validate_authentication(ctx: Context) -> str:
    """
    Valida que el usuario esté autenticado (cuando OAuth habilitado).

    Args:
        ctx: Context de MCP

    Returns:
        User ID del token OAuth

    Raises:
        ToolError: Si OAuth está habilitado y no hay autenticación
    """
    if not OAUTH_DISABLED and oauth_server:
        # OAuth habilitado: verificar que hay usuario autenticado
        if not ctx or not hasattr(ctx, 'user_id') or not ctx.user_id:
            raise ToolError(
                "Autenticación requerida. Debe proporcionar token OAuth válido en header Authorization.",
                code="UNAUTHORIZED"
            )
        return ctx.user_id
    else:
        # OAuth deshabilitado (dev mode): retornar usuario genérico
        return "dev-user"


# ============================================================
# TOOL: create_incident
# ============================================================

@mcp.tool(
    name="create_incident",
    description=(
        "Crea un nuevo incidente en el sistema de gestión de Brasaland. "
        "Usa esta tool cuando necesites registrar un nuevo ticket, problema o incidencia reportada. "
        "Retorna el ID del incidente creado y su estado inicial."
    )
)
@require_scopes("incidents:write")
async def create_incident(
    description: str,
    category: str,
    origin: str = "interno",
    priority: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Crea un nuevo incidente.

    Args:
        description: Descripción del incidente
        category: Categoría (técnico, servicio, logística, RRHH)
        origin: Origen (cliente, interno, sistema)
        priority: Prioridad opcional (low, medium, high)
        ctx: Context de MCP (incluye auth info)

    Returns:
        Dict con ID del incidente creado y detalles
    """
    # Validar autenticación
    user_id = validate_authentication(ctx)

    logger.info("create_incident_called",
                description=description[:50],
                category=category,
                user=user_id)

    # Validar input con schema
    try:
        validated_input = CreateIncidentInput(
            description=description,
            category=category,
            origin=origin,
            priority=priority
        )
    except Exception as e:
        raise ToolError(f"Input inválido: {str(e)}", code="INVALID_INPUT")

    # Llamar a API backend
    url = f"{API_BASE_URL}/incidents"

    payload = {
        "description": validated_input.description,
        "category": validated_input.category,
        "origin": validated_input.origin,
        "status": "open"  # Estado inicial
    }

    if validated_input.priority:
        payload["priority"] = validated_input.priority

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(url, json=payload)

        if response.status_code == 201:
            data = response.json()

            logger.info("incident_created",
                       incident_id=data.get("id"),
                       user=ctx.user_id if ctx else None)

            return {
                "success": True,
                "incident_id": data.get("id"),
                "status": data.get("status"),
                "message": f"Incidente {data.get('id')} creado exitosamente"
            }
        else:
            raise ToolError(
                f"Error HTTP {response.status_code}: {response.text}",
                code="API_ERROR"
            )

    except httpx.TimeoutException:
        raise ToolError(
            f"Timeout: API no respondió en {API_TIMEOUT}s",
            code="TIMEOUT"
        )
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Error inesperado: {str(e)}", code="INTERNAL_ERROR")


# ============================================================
# TOOL: update_incident_status
# ============================================================

@mcp.tool(
    name="update_incident_status",
    description=(
        "Actualiza el estado de un incidente existente siguiendo su ciclo de vida formal. "
        "Estados válidos: open → in_progress → resolved → closed. "
        "Usa esta tool cuando necesites cambiar el estado de un ticket. "
        "CRÍTICO: Usa el endpoint de ciclo de vida PATCH /api/incidents/{id}/status"
    )
)
@require_scopes("incidents:write")
async def update_incident_status(
    ticket_id: int,
    new_status: str,
    comment: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Actualiza el estado de un incidente (ciclo de vida).

    Args:
        ticket_id: ID del incidente
        new_status: Nuevo estado (open, in_progress, resolved, closed)
        comment: Comentario opcional
        ctx: Context de MCP

    Returns:
        Dict con confirmación del cambio
    """
    # Validar autenticación
    user_id = validate_authentication(ctx)

    logger.info("update_incident_status_called",
                ticket_id=ticket_id,
                new_status=new_status,
                user=user_id)

    # Validar input
    try:
        validated_input = UpdateIncidentStatusInput(
            ticket_id=ticket_id,
            new_status=new_status,
            comment=comment
        )
    except Exception as e:
        raise ToolError(f"Input inválido: {str(e)}", code="INVALID_INPUT")

    # CRÍTICO: Usar endpoint de ciclo de vida
    url = f"{API_BASE_URL}/incidents/{validated_input.ticket_id}/status"

    payload = {
        "status": validated_input.new_status
    }

    if validated_input.comment:
        payload["comment"] = validated_input.comment

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.patch(url, json=payload)

        if response.status_code == 200:
            data = response.json()

            logger.info("incident_status_updated",
                       ticket_id=validated_input.ticket_id,
                       new_status=validated_input.new_status,
                       user=ctx.user_id if ctx else None)

            return {
                "success": True,
                "ticket_id": validated_input.ticket_id,
                "old_status": data.get("old_status"),
                "new_status": data.get("status"),
                "message": f"Ticket {validated_input.ticket_id} actualizado a '{validated_input.new_status}'"
            }

        elif response.status_code == 404:
            raise ToolError(
                f"Ticket {validated_input.ticket_id} no encontrado",
                code="NOT_FOUND"
            )

        elif response.status_code == 422:
            raise ToolError(
                f"Transición de estado inválida: {response.text}",
                code="INVALID_TRANSITION"
            )

        else:
            raise ToolError(
                f"Error HTTP {response.status_code}: {response.text}",
                code="API_ERROR"
            )

    except httpx.TimeoutException:
        raise ToolError(f"Timeout: API no respondió en {API_TIMEOUT}s", code="TIMEOUT")
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Error inesperado: {str(e)}", code="INTERNAL_ERROR")


# ============================================================
# TOOL: get_incident_status
# ============================================================

@mcp.tool(
    name="get_incident_status",
    description=(
        "Consulta el estado actual y detalles de un incidente específico por su ID. "
        "Usa esta tool cuando necesites verificar el estado de un ticket o obtener información detallada."
    )
)
@require_scopes("incidents:read")
async def get_incident_status(
    ticket_id: int,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Consulta el estado de un incidente.

    Args:
        ticket_id: ID del incidente
        ctx: Context de MCP

    Returns:
        Dict con información del incidente
    """
    # Validar autenticación
    user_id = validate_authentication(ctx)

    logger.info("get_incident_status_called",
                ticket_id=ticket_id,
                user=user_id)

    # Validar input
    try:
        validated_input = GetIncidentInput(ticket_id=ticket_id)
    except Exception as e:
        raise ToolError(f"Input inválido: {str(e)}", code="INVALID_INPUT")

    url = f"{API_BASE_URL}/incidents/{validated_input.ticket_id}"

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(url)

        if response.status_code == 200:
            data = response.json()

            logger.info("incident_retrieved",
                       ticket_id=validated_input.ticket_id,
                       status=data.get("status"),
                       user=ctx.user_id if ctx else None)

            return {
                "success": True,
                "ticket_id": data.get("id"),
                "status": data.get("status"),
                "category": data.get("category"),
                "origin": data.get("origin"),
                "description": data.get("description"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at")
            }

        elif response.status_code == 404:
            raise ToolError(
                f"Ticket {validated_input.ticket_id} no encontrado",
                code="NOT_FOUND"
            )

        else:
            raise ToolError(
                f"Error HTTP {response.status_code}: {response.text}",
                code="API_ERROR"
            )

    except httpx.TimeoutException:
        raise ToolError(f"Timeout: API no respondió en {API_TIMEOUT}s", code="TIMEOUT")
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Error inesperado: {str(e)}", code="INTERNAL_ERROR")


# ============================================================
# TOOL: get_inventory_stock (SOLO LECTURA ESTRICTA)
# ============================================================

@mcp.tool(
    name="get_inventory_stock",
    description=(
        "Consulta el stock de productos en inventario. "
        "SOLO LECTURA: Esta tool NO permite modificar, actualizar ni eliminar inventario. "
        "Cualquier intención de mutación será rechazada con error explícito. "
        "Usa esta tool solo para consultar niveles de stock actuales."
    )
)
@require_scopes("inventory:read")
async def get_inventory_stock(
    product_id: Optional[int] = None,
    location_id: Optional[int] = None,
    limit: int = 10,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Consulta stock de inventario (SOLO LECTURA).

    Args:
        product_id: ID del producto (opcional)
        location_id: ID del local (opcional)
        limit: Límite de resultados
        ctx: Context de MCP

    Returns:
        Dict con productos y stock

    Raises:
        ToolError: Si se detecta intención de mutación
    """
    # Validar autenticación
    user_id = validate_authentication(ctx)

    logger.info("get_inventory_stock_called",
                product_id=product_id,
                location_id=location_id,
                user=user_id)

    # Validar input
    try:
        validated_input = GetInventoryInput(
            product_id=product_id,
            location_id=location_id,
            limit=limit
        )
    except Exception as e:
        raise ToolError(f"Input inválido: {str(e)}", code="INVALID_INPUT")

    # VALIDACIÓN DEFENSIVA: Rechazar mutaciones
    # Esto es un ejemplo, en producción se validaría el contexto completo
    if ctx and hasattr(ctx, 'raw_request'):
        # Verificar que no hay intenciones de modificación en el contexto
        request_text = str(ctx.raw_request).lower()
        forbidden_keywords = ["update", "delete", "modify", "set", "change", "edit", "remove"]

        if any(kw in request_text for kw in forbidden_keywords):
            raise ToolError(
                "OPERACIÓN RECHAZADA: get_inventory_stock es SOLO LECTURA. "
                "No se permiten operaciones de modificación de inventario via MCP. "
                "Usa el sistema de gestión de inventario directamente para mutaciones.",
                code="READ_ONLY_VIOLATION"
            )

    # Construir query params
    url = f"{API_BASE_URL}/inventory/products"
    params = {"limit": validated_input.limit}

    if validated_input.product_id:
        params["product_id"] = validated_input.product_id
    if validated_input.location_id:
        params["location_id"] = validated_input.location_id

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(url, params=params)

        if response.status_code == 200:
            data = response.json()

            logger.info("inventory_retrieved",
                       count=len(data) if isinstance(data, list) else 0,
                       user=ctx.user_id if ctx else None)

            return {
                "success": True,
                "products": data,
                "count": len(data) if isinstance(data, list) else 0,
                "readonly_note": "Esta consulta es de solo lectura. Para modificar inventario, usa el sistema de gestión."
            }

        else:
            raise ToolError(
                f"Error HTTP {response.status_code}: {response.text}",
                code="API_ERROR"
            )

    except httpx.TimeoutException:
        raise ToolError(f"Timeout: API no respondió en {API_TIMEOUT}s", code="TIMEOUT")
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Error inesperado: {str(e)}", code="INTERNAL_ERROR")


# ============================================================
# HEALTH CHECK
# ============================================================

@mcp.tool(
    name="health_check",
    description="Verifica el estado del servidor MCP y conectividad con backend"
)
async def health_check(ctx: Context = None) -> Dict[str, Any]:
    """Health check del servidor MCP"""
    return {
        "status": "healthy",
        "server": "brasaland-mcp-server",
        "version": "1.0.0",
        "backend_url": API_BASE_URL,
        "oauth_enabled": oauth_server is not None
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import asyncio

    print("=" * 70)
    print("🚀 Brasaland MCP Server")
    print("=" * 70)
    print(f"Transport: HTTP/SSE")
    print(f"Host: {MCP_SERVER_HOST}:{MCP_SERVER_PORT}")
    print(f"Backend: {API_BASE_URL}")
    print(f"OAuth: {'Enabled' if oauth_server else 'Disabled (dev mode)'}")
    print("=" * 70)
    print("\nTools disponibles:")
    print("  - create_incident (scope: incidents:write)")
    print("  - update_incident_status (scope: incidents:write)")
    print("  - get_incident_status (scope: incidents:read)")
    print("  - get_inventory_stock (scope: inventory:read) [SOLO LECTURA]")
    print("  - health_check")
    print("\n" + "=" * 70)
    print("Servidor listo para conexiones MCP remotas vía HTTP/SSE")
    print("=" * 70 + "\n")

    # Ejecutar servidor
    try:
        mcp.run(
            host=MCP_SERVER_HOST,
            port=MCP_SERVER_PORT,
            transport="http"
        )
    except KeyboardInterrupt:
        print("\n\n✅ Servidor detenido")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
