"""
Schemas Pydantic para Incidencias Postventa
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date


# Tipos literales según BRIEFING
Categoria = Literal[
    'calidad_comida',
    'servicio_cliente',
    'operaciones',
    'infraestructura',
    'pedidos_online',
    'facturacion'
]

Estado = Literal['abierto', 'en_proceso', 'cerrado', 'descartado']

Pais = Literal['CO', 'US']

Local = Literal[
    # Colombia
    'medellin_centro', 'medellin_poblado', 'medellin_envigado',
    'bogota_zona_rosa', 'bogota_usaquen', 'bogota_suba',
    'cali_norte', 'cali_sur',
    'cartagena_centro', 'barranquilla_norte',
    # Florida
    'miami_beach', 'miami_downtown',
    'orlando_international', 'tampa_centro'
]


class IncidentCSVRow(BaseModel):
    """Representa una fila del CSV de incidencias"""
    id_incidencia: str
    fecha: date
    categoria: Categoria
    descripcion: str
    estado: Estado
    local: Local
    pais: Pais
    satisfaccion: Optional[int] = Field(None, ge=1, le=5)
    email_cliente: Optional[str] = None
    telefono: Optional[str] = None


class IncidentInvalido(BaseModel):
    """Registro inválido con razón"""
    linea: int
    id_incidencia: str
    razon: str


class MetricasPorCategoria(BaseModel):
    """Métricas agrupadas por categoría"""
    categoria: str
    cantidad: int
    porcentaje: float


class MetricasPorEstado(BaseModel):
    """Métricas agrupadas por estado"""
    estado: str
    cantidad: int
    porcentaje: float


class MetricasPorPais(BaseModel):
    """Métricas agrupadas por país"""
    pais: str
    pais_nombre: str
    cantidad: int
    porcentaje: float


class AnalysisResponse(BaseModel):
    """Respuesta del análisis de incidencias"""
    total_procesados: int
    total_validos: int
    total_invalidos: int
    registros_invalidos: list[IncidentInvalido]
    por_categoria: list[MetricasPorCategoria]
    por_estado: list[MetricasPorEstado]
    por_pais: list[MetricasPorPais]
    satisfaccion_promedio: float
    satisfaccion_evaluacion: str  # EXCELENTE, BUENO, REQUIERE ATENCIÓN
