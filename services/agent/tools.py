"""
Agent Tools - Herramientas Vivas para Consulta de Servicios

Tools de solo lectura (GET) que consultan servicios reales del monorepo:
- Incidentes (GET /api/incidents, GET /api/incidents/{id})
- Inventario (GET /inventory/products) [opcional]

CRÍTICO:
- NO mocking en código productivo (solo servicios reales)
- Solo lectura (GET), nunca CREATE/UPDATE/DELETE
- Timeouts estrictos (3-5s)
- Fallback honesto sin alucinación
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum

import httpx
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ============================================================
# CONFIGURACIÓN
# ============================================================

# Base URL del backend (desde env o default localhost)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "5"))  # 5 segundos default

# Autenticación (si se requiere JWT)
API_KEY = os.getenv("API_KEY", None)

# ============================================================
# SCHEMAS TIPADOS (Contratos de Tools)
# ============================================================

class IncidentStatus(str, Enum):
    """Estados posibles de un incidente"""
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

class IncidentOrigin(str, Enum):
    """Origen del incidente"""
    CUSTOMER = "cliente"
    INTERNAL = "interno"
    SYSTEM = "sistema"

class IncidentResponse(BaseModel):
    """Contrato tipado para respuesta de consulta de incidente"""
    id: int = Field(..., description="ID único del incidente")
    status: str = Field(..., description="Estado actual")
    category: str = Field(..., description="Categoría del incidente")
    origin: str = Field(..., description="Origen del incidente")
    description: str = Field(..., description="Descripción del incidente")
    created_at: str = Field(..., description="Fecha de creación")
    updated_at: Optional[str] = Field(None, description="Última actualización")
    resolved_at: Optional[str] = Field(None, description="Fecha de resolución")

class IncidentListResponse(BaseModel):
    """Respuesta para listado de incidentes"""
    incidents: List[IncidentResponse]
    total: int
    page: int
    page_size: int

class ProductResponse(BaseModel):
    """Contrato tipado para respuesta de consulta de inventario"""
    id: int
    name: str
    sku: str
    stock: int
    price: float
    location_id: int

# ============================================================
# TOOL: Consulta de Incidente por ID
# ============================================================

def get_incident_by_id(ticket_id: int | str) -> Dict[str, Any]:
    """
    Tool: Consulta estado de un incidente específico por ID.

    Conecta con: GET /api/incidents/{id}

    Args:
        ticket_id: ID del ticket/incidente

    Returns:
        Dict con información del incidente o error

    Ejemplo de retorno exitoso:
        {
            "success": True,
            "data": {
                "id": 482,
                "status": "in_progress",
                "category": "técnico",
                "origin": "cliente",
                "description": "Error en sistema de pedidos",
                "created_at": "2024-10-25T10:30:00",
                "updated_at": "2024-10-26T15:45:00"
            }
        }

    Ejemplo de error:
        {
            "success": False,
            "error": "Timeout: El servicio de incidentes no respondió en 5s",
            "ticket_id": 482
        }
    """
    try:
        # Normalizar ticket_id a int
        ticket_id_int = int(ticket_id)
    except ValueError:
        return {
            "success": False,
            "error": f"ID de ticket inválido: '{ticket_id}' no es un número",
            "ticket_id": ticket_id
        }

    # URL del endpoint
    url = f"{API_BASE_URL}/incidents/{ticket_id_int}"

    # Headers (autenticación si se requiere)
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    try:
        # Llamada HTTP con timeout estricto
        with httpx.Client(timeout=API_TIMEOUT) as client:
            response = client.get(url, headers=headers)

        # Verificar status code
        if response.status_code == 404:
            return {
                "success": False,
                "error": f"Ticket {ticket_id_int} no encontrado en el sistema",
                "ticket_id": ticket_id_int
            }

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Error HTTP {response.status_code}: {response.text}",
                "ticket_id": ticket_id_int
            }

        # Parsear respuesta
        data = response.json()

        # Validar con schema (opcional, para garantizar contrato)
        try:
            incident = IncidentResponse(**data)
            return {
                "success": True,
                "data": incident.model_dump()
            }
        except Exception as e:
            # Si no cumple schema, devolver raw
            return {
                "success": True,
                "data": data,
                "warning": f"Respuesta no cumple schema esperado: {e}"
            }

    except httpx.TimeoutException:
        return {
            "success": False,
            "error": f"Timeout: El servicio de incidentes no respondió en {API_TIMEOUT}s",
            "ticket_id": ticket_id_int
        }

    except httpx.ConnectError:
        return {
            "success": False,
            "error": f"Error de conexión: No se pudo conectar a {API_BASE_URL}",
            "ticket_id": ticket_id_int
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error inesperado: {str(e)}",
            "ticket_id": ticket_id_int
        }


# ============================================================
# TOOL: Listado de Incidentes con Filtros
# ============================================================

def list_incidents(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Tool: Lista incidentes con filtros opcionales.

    Conecta con: GET /api/incidents?status=...&category=...

    Args:
        status: Filtrar por estado (open, in_progress, resolved, closed)
        category: Filtrar por categoría
        limit: Máximo de incidentes a devolver

    Returns:
        Dict con lista de incidentes o error
    """
    url = f"{API_BASE_URL}/incidents"

    # Construir query params
    params = {"limit": limit}
    if status:
        params["status"] = status
    if category:
        params["category"] = category

    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    try:
        with httpx.Client(timeout=API_TIMEOUT) as client:
            response = client.get(url, params=params, headers=headers)

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Error HTTP {response.status_code}: {response.text}"
            }

        data = response.json()

        return {
            "success": True,
            "data": data,
            "count": len(data) if isinstance(data, list) else data.get("total", 0)
        }

    except httpx.TimeoutException:
        return {
            "success": False,
            "error": f"Timeout: El servicio de incidentes no respondió en {API_TIMEOUT}s"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error inesperado: {str(e)}"
        }


# ============================================================
# TOOL: Consulta de Inventario (Opcional)
# ============================================================

def get_inventory_products(
    location_id: Optional[int] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Tool: Consulta productos de inventario.

    Conecta con: GET /inventory/products?location_id=...

    Args:
        location_id: Filtrar por local
        limit: Máximo de productos

    Returns:
        Dict con productos o error
    """
    url = f"{API_BASE_URL}/inventory/products"

    params = {"limit": limit}
    if location_id:
        params["location_id"] = location_id

    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    try:
        with httpx.Client(timeout=API_TIMEOUT) as client:
            response = client.get(url, params=params, headers=headers)

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Error HTTP {response.status_code}"
            }

        data = response.json()

        return {
            "success": True,
            "data": data,
            "count": len(data) if isinstance(data, list) else 0
        }

    except httpx.TimeoutException:
        return {
            "success": False,
            "error": f"Timeout: El servicio de inventario no respondió en {API_TIMEOUT}s"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error inesperado: {str(e)}"
        }


# ============================================================
# REGISTRY DE TOOLS (para LangGraph)
# ============================================================

AVAILABLE_TOOLS = {
    "get_incident_by_id": {
        "function": get_incident_by_id,
        "description": "Consulta el estado actual de un ticket/incidente específico por su ID. Usa esta tool cuando el usuario pregunte sobre el estado, progreso o detalles de un ticket en particular.",
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
        "function": list_incidents,
        "description": "Lista incidentes con filtros opcionales (status, category). Usa esta tool cuando el usuario pregunte sobre múltiples incidentes, estadísticas o listados generales.",
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
        "function": get_inventory_products,
        "description": "Consulta productos del inventario. Usa esta tool cuando el usuario pregunte sobre stock, productos disponibles o inventario de locales.",
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
    }
}


def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    Ejecuta una tool por nombre con argumentos.

    Args:
        tool_name: Nombre de la tool registrada
        **kwargs: Argumentos para la tool

    Returns:
        Resultado de la tool
    """
    if tool_name not in AVAILABLE_TOOLS:
        return {
            "success": False,
            "error": f"Tool '{tool_name}' no encontrada. Tools disponibles: {list(AVAILABLE_TOOLS.keys())}"
        }

    tool_func = AVAILABLE_TOOLS[tool_name]["function"]

    try:
        return tool_func(**kwargs)
    except Exception as e:
        return {
            "success": False,
            "error": f"Error ejecutando tool '{tool_name}': {str(e)}"
        }
