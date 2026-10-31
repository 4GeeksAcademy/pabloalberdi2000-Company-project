"""
Rate Limiting Middleware - Brasaland Digital

Protección contra abuso de API y control de costos LLM.

CRÍTICO:
- Endpoints LLM tienen límites estrictos (prevenir DoS económico)
- Basado en IP address (get_remote_address)
- Excepciones logueadas con structlog

Dependencias:
    pip install slowapi

Uso:
    from services.middleware.rate_limiter import limiter, setup_rate_limiting

    # En main.py
    setup_rate_limiting(app)

    # En routers
    @router.post("/query")
    @limiter.limit("20/minute")
    async def query_endpoint(request: Request):
        ...
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request, HTTPException
from typing import Callable
import structlog

# Logging estructurado
logger = structlog.get_logger()

# ============================================================
# CONFIGURACIÓN DE LIMITER
# ============================================================

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"],  # Límite global por defecto
    storage_uri="memory://",        # En memoria (cambiar a Redis en prod)
    strategy="fixed-window"         # Ventana fija de tiempo
)

# ============================================================
# LÍMITES POR ENDPOINT
# ============================================================

# Límites específicos por tipo de endpoint
ENDPOINT_LIMITS = {
    # Endpoints LLM (costosos)
    "knowledge_query": "20/minute",      # RAG queries
    "rfp_intake": "5/minute",            # Upload PDFs + procesamiento
    "rfp_generate": "3/minute",          # Generación iterativa
    "chat_message": "30/minute",         # Chat WebSocket

    # Endpoints MCP (tools)
    "mcp_tool_write": "10/minute",       # Tools de escritura
    "mcp_tool_read": "50/minute",        # Tools de lectura

    # Endpoints autenticación
    "auth_login": "5/hour",              # Prevenir brute force
    "auth_register": "3/hour",

    # Endpoints estándar
    "api_standard": "100/minute",
}

# ============================================================
# SETUP FUNCTION
# ============================================================

def setup_rate_limiting(app: FastAPI):
    """
    Configurar rate limiting en aplicación FastAPI.

    Args:
        app: Instancia de FastAPI

    Efectos:
        - Agrega limiter al state de la app
        - Configura exception handler para RateLimitExceeded
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    logger.info(
        "rate_limiting_configured",
        default_limit="1000/hour",
        strategy="fixed-window",
        storage="memory"
    )

# ============================================================
# EXCEPTION HANDLER
# ============================================================

async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Handler personalizado para violaciones de rate limit.

    Loguea cada violación con structlog para análisis.
    """
    client_ip = get_remote_address(request)
    endpoint = request.url.path

    # Log estructurado de violación
    logger.warning(
        "rate_limit_exceeded",
        client_ip=client_ip,
        endpoint=endpoint,
        method=request.method,
        limit=str(exc.detail),
        user_agent=request.headers.get("user-agent", "unknown")
    )

    # Respuesta al cliente
    return HTTPException(
        status_code=429,
        detail={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": "60 seconds"
        }
    ).json()

# ============================================================
# DECORADORES HELPER
# ============================================================

def limit_llm_endpoint(endpoint_type: str) -> Callable:
    """
    Decorator helper para endpoints LLM.

    Uso:
        @limit_llm_endpoint("knowledge_query")
        async def query_knowledge(request: Request):
            ...

    Args:
        endpoint_type: Tipo de endpoint (key en ENDPOINT_LIMITS)

    Returns:
        Decorator configurado con límite apropiado
    """
    limit = ENDPOINT_LIMITS.get(endpoint_type, "100/minute")

    def decorator(func: Callable) -> Callable:
        return limiter.limit(limit)(func)

    return decorator

# ============================================================
# RATE LIMIT CHECKER (para uso programático)
# ============================================================

async def check_rate_limit(
    request: Request,
    limit: str = "100/minute"
) -> bool:
    """
    Verificar rate limit programáticamente sin levantar excepción.

    Útil para lógica condicional basada en límites.

    Args:
        request: Request de FastAPI
        limit: String de límite (ej. "20/minute")

    Returns:
        True si bajo el límite, False si excedido
    """
    try:
        limiter.test(limit, get_remote_address(request))
        return True
    except RateLimitExceeded:
        return False

# ============================================================
# METRICS (para monitoreo)
# ============================================================

def get_rate_limit_stats() -> dict:
    """
    Obtener estadísticas de rate limiting.

    Returns:
        Dict con métricas de uso
    """
    # Placeholder - implementar con Redis en producción
    return {
        "storage": "memory",
        "strategy": "fixed-window",
        "active_limits": len(ENDPOINT_LIMITS)
    }
