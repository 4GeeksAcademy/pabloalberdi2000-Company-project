"""
Schemas Pydantic para Incidencias Postventa
"""
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, List
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


# ============================================================
# PERSISTENCE SCHEMAS (Fase 4 - Incident Management)
# ============================================================

# Enums para persistencia (English naming para consistencia API)
Origin = Literal['customer', 'branch', 'internal']
Status = Literal['open', 'in_progress', 'resolved', 'discarded']

# Branch extendido con "central" para incidencias no específicas de sede
Branch = Literal[
    'medellin_centro', 'medellin_poblado', 'medellin_envigado',
    'bogota_zona_rosa', 'bogota_usaquen', 'bogota_suba',
    'cali_norte', 'cali_sur',
    'cartagena_centro', 'barranquilla_norte',
    'miami_beach', 'miami_downtown',
    'orlando_international', 'tampa_centro',
    'central'
]


class IncidentCreate(BaseModel):
    """Schema para crear nueva incidencia"""
    title: str = Field(..., min_length=1, max_length=255, description="Título descriptivo")
    description: str = Field(..., min_length=1, max_length=2000, description="Descripción detallada")
    category: Categoria = Field(..., description="Categoría de la incidencia")
    origin: Origin = Field(..., description="Origen del reporte")
    branch: Branch = Field(..., description="Sede o 'central'")

    @field_validator('title', 'description')
    @classmethod
    def validate_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Field cannot be empty or whitespace only')
        return v.strip()


class IncidentStatusUpdate(BaseModel):
    """Schema para actualizar estado de incidencia (state machine)"""
    status: Status = Field(..., description="Nuevo estado")
    satisfaction: Optional[int] = Field(None, ge=1, le=5, description="Satisfacción (1-5, opcional)")


class IncidentUpdate(BaseModel):
    """Schema para actualizar campos de incidencia (no status)"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    category: Optional[Categoria] = None
    branch: Optional[Branch] = None


class IncidentResponse(BaseModel):
    """Schema de respuesta de incidencia"""
    id: str
    title: str
    description: str
    category: Categoria
    status: Status
    origin: Origin
    branch: Branch
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601
    satisfaction: Optional[int] = None
    legacy_id: Optional[str] = None  # Del CSV histórico


class IncidentListResponse(BaseModel):
    """Respuesta paginada de listado"""
    total: int
    items: List[IncidentResponse]
    limit: int
    offset: int


class IncidentSummary(BaseModel):
    """Métricas agregadas del sistema"""
    total_incidents: int
    by_status: dict
    by_category: dict
    by_origin: dict
    by_branch: dict
    avg_satisfaction: Optional[float] = None
