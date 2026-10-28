"""
Timing Middleware

Middleware HTTP para medir y registrar la latencia de cada request.
Útil para identificar candidatos a caching basado en evidencia real.
"""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging

# Configurar logger
logger = logging.getLogger("timing")
logger.setLevel(logging.INFO)

# Handler de consola con formato estructurado
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter(
        "⏱️  [%(asctime)s] %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
)
logger.addHandler(console_handler)


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para medir tiempo de ejecución de cada request.

    Registra en consola:
    - Método HTTP
    - Path completo
    - Status code
    - Duración en ms (precisión sub-milisegundo)

    Útil para:
    1. Identificar endpoints lentos (>100-200ms)
    2. Detectar patrones de uso (frecuencia)
    3. Justificar decisiones de caching
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # Capturar tiempo de inicio (alta precisión)
        start_time = time.perf_counter()

        # Ejecutar request
        response = await call_next(request)

        # Calcular duración
        duration_s = time.perf_counter() - start_time
        duration_ms = duration_s * 1000

        # Extraer información del request
        method = request.method
        path = request.url.path
        status_code = response.status_code

        # Determinar severidad basado en latencia
        if duration_ms > 500:
            level = "WARNING"  # Endpoints muy lentos (>500ms)
        elif duration_ms > 200:
            level = "INFO"     # Endpoints moderados (200-500ms)
        else:
            level = "DEBUG"    # Endpoints rápidos (<200ms)

        # Log estructurado
        log_message = (
            f"{method:6} {path:40} "
            f"Status:{status_code:3} "
            f"Duration:{duration_ms:7.2f}ms"
        )

        # Agregar indicador visual para endpoints lentos
        if duration_ms > 200:
            log_message += " ⚠️  CANDIDATO A CACHING"

        # Registrar según severidad
        if level == "WARNING":
            logger.warning(log_message)
        elif level == "INFO":
            logger.info(log_message)
        else:
            logger.debug(log_message)

        # Agregar header de timing a la respuesta (útil para debugging frontend)
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response
