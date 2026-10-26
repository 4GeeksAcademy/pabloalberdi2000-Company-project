"""
Constantes del dominio Brasaland

Valores permitidos según BRIEFING_INCIDENCIAS.md
"""

# Valores permitidos según BRIEFING
CATEGORIAS_PERMITIDAS = {
    'calidad_comida',
    'servicio_cliente',
    'operaciones',
    'infraestructura',
    'pedidos_online',
    'facturacion'
}

ESTADOS_PERMITIDOS = {
    'abierto',
    'en_proceso',
    'cerrado',
    'descartado'
}

PAISES_PERMITIDOS = {'CO', 'US'}

LOCALES_PERMITIDOS = {
    # Colombia (10 locales)
    'medellin_centro', 'medellin_poblado', 'medellin_envigado',
    'bogota_zona_rosa', 'bogota_usaquen', 'bogota_suba',
    'cali_norte', 'cali_sur',
    'cartagena_centro', 'barranquilla_norte',
    # Florida (4 locales)
    'miami_beach', 'miami_downtown',
    'orlando_international', 'tampa_centro'
}

CAMPOS_OBLIGATORIOS = [
    'id_incidencia',
    'fecha',
    'categoria',
    'descripcion',
    'estado',
    'local',
    'pais'
]
