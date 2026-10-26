"""
Brasaland Shared - Paquete transversal para validaciones y lógica compartida

Este paquete contiene código reutilizable por múltiples servicios del monorepo:
- scripts/ (CLI tools)
- services/api/ (FastAPI backend)
- Futuros servicios

Estructura:
- validators.py: Validaciones de incidencias según BRIEFING.md
- constants.py: Constantes del dominio (categorías, estados, locales)
"""

__version__ = "1.0.0"

from .validators import (
    validar_registro,
    validar_fecha,
    validar_satisfaccion,
    calcular_satisfaccion_promedio,
    obtener_evaluacion_satisfaccion
)

from .constants import (
    CATEGORIAS_PERMITIDAS,
    ESTADOS_PERMITIDOS,
    PAISES_PERMITIDOS,
    LOCALES_PERMITIDOS,
    CAMPOS_OBLIGATORIOS
)

__all__ = [
    # Validators
    "validar_registro",
    "validar_fecha",
    "validar_satisfaccion",
    "calcular_satisfaccion_promedio",
    "obtener_evaluacion_satisfaccion",
    # Constants
    "CATEGORIAS_PERMITIDAS",
    "ESTADOS_PERMITIDOS",
    "PAISES_PERMITIDOS",
    "LOCALES_PERMITIDOS",
    "CAMPOS_OBLIGATORIOS",
]
