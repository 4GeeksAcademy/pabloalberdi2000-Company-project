"""
MCP Client Adapter - Consume Tools vía Model Context Protocol

Adaptador que consume tools del servidor MCP en lugar de llamadas directas.

MIGRACIÓN:
- Antes: services/agent/graph.py → tools.py (funciones directas)
- Después: services/agent/graph.py → mcp_adapter.py → MCP Server (HTTP/SSE)

CRÍTICO:
- Usa langchain-mcp-adapters para integración con LangGraph
- Las tools MCP reemplazan las funciones directas de tools.py
- El servidor MCP maneja autenticación OAuth y audit logging
- Timeout en cliente: 10s (más generoso que tools directas: 5s)
"""

import os
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

from dotenv import load_dotenv
import structlog

# LangChain MCP Adapters
try:
    from langchain_mcp_adapters import MCPToolAdapter
except ImportError:
    print("ERROR: langchain-mcp-adapters no instalado.")
    print("Instalar con: pip install langchain-mcp-adapters")
    sys.exit(1)

load_dotenv()

# Logging estructurado
logger = structlog.get_logger()

# ============================================================
# CONFIGURACIÓN
# ============================================================

# MCP Server endpoint
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8100")

# OAuth credentials (si se requiere autenticación)
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET")
OAUTH_TOKEN_URL = os.getenv("OAUTH_TOKEN_URL")

# Timeout para cliente MCP (más generoso que tools directas)
MCP_CLIENT_TIMEOUT = int(os.getenv("MCP_CLIENT_TIMEOUT", "10"))

# ============================================================
# CLIENTE MCP
# ============================================================

class BrasalandMCPClient:
    """
    Cliente MCP que expone tools del servidor como funciones.

    Adaptado para uso en LangGraph Agent.
    """

    def __init__(self, server_url: str = MCP_SERVER_URL):
        """
        Inicializa cliente MCP.

        Args:
            server_url: URL del servidor MCP (HTTP/SSE)
        """
        self.server_url = server_url
        self.adapter = None
        self._connect()

    def _connect(self):
        """Conecta al servidor MCP y carga tools disponibles"""
        try:
            logger.info("mcp_connecting", url=self.server_url)

            # Configurar adaptador MCP
            # El adaptador maneja la conexión SSE/HTTP y descubrimiento de tools
            self.adapter = MCPToolAdapter(
                server_url=self.server_url,
                timeout=MCP_CLIENT_TIMEOUT,
                # OAuth (si está configurado)
                auth={
                    "client_id": OAUTH_CLIENT_ID,
                    "client_secret": OAUTH_CLIENT_SECRET,
                    "token_url": OAUTH_TOKEN_URL
                } if OAUTH_CLIENT_ID else None
            )

            # Verificar conexión con health check
            health = self.adapter.call_tool("health_check")

            logger.info("mcp_connected",
                       server=health.get("server"),
                       version=health.get("version"),
                       oauth_enabled=health.get("oauth_enabled"))

        except Exception as e:
            logger.error("mcp_connection_failed", error=str(e))
            raise ConnectionError(f"No se pudo conectar al servidor MCP: {e}")

    def get_incident_by_id(self, ticket_id: int | str) -> Dict[str, Any]:
        """
        Consulta estado de un incidente específico por ID (vía MCP).

        Args:
            ticket_id: ID del ticket/incidente

        Returns:
            Dict con información del incidente o error
        """
        logger.info("mcp_tool_call", tool="get_incident_status", ticket_id=ticket_id)

        try:
            result = self.adapter.call_tool(
                tool_name="get_incident_status",
                arguments={"ticket_id": int(ticket_id)}
            )

            return result

        except Exception as e:
            logger.error("mcp_tool_error", tool="get_incident_status", error=str(e))
            return {
                "success": False,
                "error": f"Error llamando a MCP tool: {str(e)}",
                "ticket_id": ticket_id
            }

    def list_incidents(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Lista incidentes (NO IMPLEMENTADO en MCP Server v1.0).

        Fallback: Retorna mensaje informativo.

        TODO: Implementar tool list_incidents en MCP Server.
        """
        logger.warning("mcp_tool_not_implemented", tool="list_incidents")

        return {
            "success": False,
            "error": "list_incidents no está disponible en MCP Server v1.0",
            "fallback": "Usa get_incident_status para consultas individuales"
        }

    def get_inventory_products(
        self,
        product_id: Optional[int] = None,
        location_id: Optional[int] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Consulta productos de inventario (vía MCP - SOLO LECTURA).

        Args:
            product_id: ID del producto (opcional)
            location_id: Filtrar por local
            limit: Máximo de productos

        Returns:
            Dict con productos o error
        """
        logger.info("mcp_tool_call",
                   tool="get_inventory_stock",
                   location_id=location_id,
                   limit=limit)

        try:
            arguments = {"limit": limit}

            if product_id:
                arguments["product_id"] = product_id
            if location_id:
                arguments["location_id"] = location_id

            result = self.adapter.call_tool(
                tool_name="get_inventory_stock",
                arguments=arguments
            )

            return result

        except Exception as e:
            logger.error("mcp_tool_error", tool="get_inventory_stock", error=str(e))
            return {
                "success": False,
                "error": f"Error llamando a MCP tool: {str(e)}"
            }

    def create_incident(
        self,
        description: str,
        category: str,
        origin: str = "interno",
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crea un nuevo incidente (vía MCP).

        NOTA: Esta es una operación de escritura (incidents:write scope).

        Args:
            description: Descripción del incidente
            category: Categoría (técnico, servicio, logística, RRHH)
            origin: Origen (cliente, interno, sistema)
            priority: Prioridad opcional (low, medium, high)

        Returns:
            Dict con ID del incidente creado
        """
        logger.info("mcp_tool_call",
                   tool="create_incident",
                   category=category)

        try:
            arguments = {
                "description": description,
                "category": category,
                "origin": origin
            }

            if priority:
                arguments["priority"] = priority

            result = self.adapter.call_tool(
                tool_name="create_incident",
                arguments=arguments
            )

            return result

        except Exception as e:
            logger.error("mcp_tool_error", tool="create_incident", error=str(e))
            return {
                "success": False,
                "error": f"Error llamando a MCP tool: {str(e)}"
            }

    def update_incident_status(
        self,
        ticket_id: int,
        new_status: str,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Actualiza el estado de un incidente (vía MCP).

        NOTA: Esta es una operación de escritura (incidents:write scope).

        Args:
            ticket_id: ID del ticket
            new_status: Nuevo estado (open, in_progress, resolved, closed)
            comment: Comentario opcional

        Returns:
            Dict con confirmación del cambio
        """
        logger.info("mcp_tool_call",
                   tool="update_incident_status",
                   ticket_id=ticket_id,
                   new_status=new_status)

        try:
            arguments = {
                "ticket_id": ticket_id,
                "new_status": new_status
            }

            if comment:
                arguments["comment"] = comment

            result = self.adapter.call_tool(
                tool_name="update_incident_status",
                arguments=arguments
            )

            return result

        except Exception as e:
            logger.error("mcp_tool_error", tool="update_incident_status", error=str(e))
            return {
                "success": False,
                "error": f"Error llamando a MCP tool: {str(e)}"
            }

    def get_available_tools(self) -> List[str]:
        """
        Lista tools disponibles en el servidor MCP.

        Returns:
            Lista de nombres de tools
        """
        try:
            return self.adapter.list_tools()
        except Exception as e:
            logger.error("mcp_list_tools_error", error=str(e))
            return []


# ============================================================
# INSTANCIA GLOBAL (Singleton)
# ============================================================

# Cliente MCP global para reutilizar conexión
_mcp_client = None

def get_mcp_client() -> BrasalandMCPClient:
    """
    Obtiene instancia singleton del cliente MCP.

    Returns:
        Cliente MCP conectado
    """
    global _mcp_client

    if _mcp_client is None:
        _mcp_client = BrasalandMCPClient()

    return _mcp_client


# ============================================================
# FUNCIONES DE COMPATIBILITY (Interfaz idéntica a tools.py)
# ============================================================

def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    Ejecuta una tool vía MCP (drop-in replacement para tools.py).

    Args:
        tool_name: Nombre de la tool
        **kwargs: Argumentos para la tool

    Returns:
        Resultado de la tool
    """
    client = get_mcp_client()

    # Mapeo de nombres (tools.py → MCP Server)
    tool_mapping = {
        "get_incident_by_id": "get_incident_by_id",
        "list_incidents": "list_incidents",
        "get_inventory_products": "get_inventory_products",
        # Tools de escritura (nuevas en MCP)
        "create_incident": "create_incident",
        "update_incident_status": "update_incident_status"
    }

    if tool_name not in tool_mapping:
        return {
            "success": False,
            "error": f"Tool '{tool_name}' no encontrada en MCP. Tools disponibles: {list(tool_mapping.keys())}"
        }

    # Llamar método correspondiente del cliente
    method_name = tool_mapping[tool_name]
    method = getattr(client, method_name)

    try:
        return method(**kwargs)
    except Exception as e:
        return {
            "success": False,
            "error": f"Error ejecutando MCP tool '{tool_name}': {str(e)}"
        }


# ============================================================
# REGISTRY PARA LANGGRAPH (Compatible con tools.py)
# ============================================================

AVAILABLE_TOOLS = {
    "get_incident_by_id": {
        "function": lambda **kwargs: execute_tool("get_incident_by_id", **kwargs),
        "description": "Consulta el estado actual de un ticket/incidente específico por su ID (vía MCP). Usa esta tool cuando el usuario pregunte sobre el estado, progreso o detalles de un ticket en particular.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "ID del ticket/incidente a consultar (ej: '482', '123')"
                }
            },
            "required": ["ticket_id"]
        }
    },
    "list_incidents": {
        "function": lambda **kwargs: execute_tool("list_incidents", **kwargs),
        "description": "Lista incidentes con filtros opcionales (NO DISPONIBLE en MCP v1.0 - Fallback).",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["open", "in_progress", "resolved", "closed"],
                    "description": "Filtrar por estado (opcional)"
                },
                "category": {
                    "type": "string",
                    "description": "Filtrar por categoría (opcional)"
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Máximo de incidentes a devolver"
                }
            }
        }
    },
    "get_inventory_products": {
        "function": lambda **kwargs: execute_tool("get_inventory_products", **kwargs),
        "description": "Consulta productos del inventario (vía MCP - SOLO LECTURA). Usa esta tool cuando el usuario pregunte sobre stock, productos disponibles o inventario de locales.",
        "parameters": {
            "type": "object",
            "properties": {
                "location_id": {
                    "type": "integer",
                    "description": "Filtrar por local específico (opcional)"
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Máximo de productos a devolver"
                }
            }
        }
    },
    "create_incident": {
        "function": lambda **kwargs: execute_tool("create_incident", **kwargs),
        "description": "Crea un nuevo incidente en el sistema (vía MCP - REQUIERE incidents:write). Usa cuando el usuario solicite crear un ticket.",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Descripción del incidente"
                },
                "category": {
                    "type": "string",
                    "enum": ["técnico", "servicio", "logística", "RRHH"],
                    "description": "Categoría del incidente"
                },
                "origin": {
                    "type": "string",
                    "default": "interno",
                    "description": "Origen (cliente, interno, sistema)"
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Prioridad (opcional)"
                }
            },
            "required": ["description", "category"]
        }
    },
    "update_incident_status": {
        "function": lambda **kwargs: execute_tool("update_incident_status", **kwargs),
        "description": "Actualiza el estado de un incidente (vía MCP - REQUIERE incidents:write). Usa cuando el usuario solicite cambiar el estado de un ticket.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "ID del ticket"
                },
                "new_status": {
                    "type": "string",
                    "enum": ["open", "in_progress", "resolved", "closed"],
                    "description": "Nuevo estado"
                },
                "comment": {
                    "type": "string",
                    "description": "Comentario opcional sobre el cambio"
                }
            },
            "required": ["ticket_id", "new_status"]
        }
    }
}


# ============================================================
# MAIN (Testing)
# ============================================================

if __name__ == "__main__":
    import json

    print("=" * 70)
    print("🧪 Testing MCP Client Adapter")
    print("=" * 70)

    # Test 1: Conectar y health check
    print("\n1️⃣  Conectando a servidor MCP...")
    try:
        client = get_mcp_client()
        print("✅ Conectado exitosamente")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        sys.exit(1)

    # Test 2: Listar tools disponibles
    print("\n2️⃣  Listando tools disponibles...")
    tools = client.get_available_tools()
    print(f"Tools: {tools}")

    # Test 3: Consultar incidente (requiere backend mock o real)
    print("\n3️⃣  Consultando ticket 482...")
    result = client.get_incident_by_id(ticket_id=482)
    print(f"Resultado:\n{json.dumps(result, indent=2, ensure_ascii=False)}")

    # Test 4: Consultar inventario
    print("\n4️⃣  Consultando inventario...")
    result = client.get_inventory_products(limit=5)
    print(f"Resultado:\n{json.dumps(result, indent=2, ensure_ascii=False)}")

    print("\n" + "=" * 70)
    print("✅ Tests completados")
    print("=" * 70)
