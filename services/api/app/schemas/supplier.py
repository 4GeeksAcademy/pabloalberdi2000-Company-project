"""
Supplier Management Schemas - Pydantic v2

Modelos de validación para gestión de proveedores de Brasaland.
Alineado con BRIEFING.md: ~20 proveedores de carne, verduras, salsas, bebidas, packaging y limpieza.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from enum import Enum


# ============ Enums ============

class SupplierStatus(str, Enum):
    """
    Estados de proveedor según BRIEFING.md
    """
    activo = "activo"
    suspendido = "suspendido"


class SupplierCategory(str, Enum):
    """
    Categorías de productos según BRIEFING.md - Compras y Proveedores
    """
    carne_proteinas = "carne_proteinas"
    verduras_vegetales = "verduras_vegetales"
    salsas_condimentos = "salsas_condimentos"
    bebidas = "bebidas"
    packaging_embalajes = "packaging_embalajes"
    productos_limpieza = "productos_limpieza"


class Country(str, Enum):
    """
    Países de operación de Brasaland
    """
    colombia = "Colombia"
    usa = "USA"


# ============ Input Schemas ============

class SupplierCreate(BaseModel):
    """
    Schema para crear proveedor (entrada - sin updated_at)

    Validaciones:
    - name: requerido, no vacío
    - country: Colombia o USA
    - categories: lista no vacía de categorías válidas
    - delivery_rate_usd: mayor que 0
    - status: activo o suspendido
    """
    name: str = Field(..., min_length=1, max_length=255, description="Nombre del proveedor")
    country: Country = Field(..., description="País de operación")
    categories: List[SupplierCategory] = Field(..., min_items=1, description="Categorías de productos")
    delivery_rate_usd: float = Field(..., gt=0, description="Tarifa de entrega en USD (debe ser > 0)")
    status: SupplierStatus = Field(default=SupplierStatus.activo, description="Estado del proveedor")
    contact_email: Optional[str] = Field(None, max_length=255, description="Email de contacto")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Teléfono de contacto")

    @field_validator('name')
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        """Validar que el nombre no sea solo espacios en blanco"""
        if not v.strip():
            raise ValueError('Supplier name cannot be empty or only whitespace')
        return v.strip()

    @field_validator('categories')
    @classmethod
    def validate_categories_unique(cls, v: List[SupplierCategory]) -> List[SupplierCategory]:
        """Validar que no haya categorías duplicadas"""
        if len(v) != len(set(v)):
            raise ValueError('Supplier categories must be unique')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "name": "Carnes Premium Colombia SAS",
                "country": "Colombia",
                "categories": ["carne_proteinas"],
                "delivery_rate_usd": 25.50,
                "status": "activo",
                "contact_email": "ventas@carnespremium.co",
                "contact_phone": "+57 300 123 4567"
            }]
        }
    }


class SupplierRateUpdate(BaseModel):
    """
    Schema para actualizar tarifa de entrega (PATCH específico)

    Registra updated_at automáticamente para auditoría de cambios de precios.
    """
    delivery_rate_usd: float = Field(..., gt=0, description="Nueva tarifa en USD (debe ser > 0)")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "delivery_rate_usd": 30.00
            }]
        }
    }


class SupplierStatusUpdate(BaseModel):
    """
    Schema para actualizar estado (PATCH específico)
    """
    status: SupplierStatus = Field(..., description="Nuevo estado del proveedor")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "status": "suspendido"
            }]
        }
    }


class SupplierUpdate(BaseModel):
    """
    Schema para actualización parcial de proveedor (PUT)

    Todos los campos opcionales. Solo actualiza campos enviados.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    country: Optional[Country] = None
    categories: Optional[List[SupplierCategory]] = Field(None, min_items=1)
    delivery_rate_usd: Optional[float] = Field(None, gt=0)
    status: Optional[SupplierStatus] = None
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)

    @field_validator('name')
    @classmethod
    def validate_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Validar que el nombre no sea solo espacios en blanco si se proporciona"""
        if v is not None and not v.strip():
            raise ValueError('Supplier name cannot be empty or only whitespace')
        return v.strip() if v else None

    @field_validator('categories')
    @classmethod
    def validate_categories_unique(cls, v: Optional[List[SupplierCategory]]) -> Optional[List[SupplierCategory]]:
        """Validar que no haya categorías duplicadas si se proporcionan"""
        if v is not None and len(v) != len(set(v)):
            raise ValueError('Supplier categories must be unique')
        return v


# ============ Output Schema ============

class SupplierResponse(BaseModel):
    """
    Schema de respuesta con id y updated_at generados por el sistema
    """
    id: int = Field(..., description="ID asignado por TinyDB")
    name: str
    country: Country
    categories: List[SupplierCategory]
    delivery_rate_usd: float
    status: SupplierStatus
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    created_at: str = Field(..., description="Timestamp de creación (ISO 8601)")
    updated_at: str = Field(..., description="Timestamp de última actualización (ISO 8601)")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": 1,
                "name": "Carnes Premium Colombia SAS",
                "country": "Colombia",
                "categories": ["carne_proteinas"],
                "delivery_rate_usd": 25.50,
                "status": "activo",
                "contact_email": "ventas@carnespremium.co",
                "contact_phone": "+57 300 123 4567",
                "created_at": "2026-11-18T10:30:00Z",
                "updated_at": "2026-11-18T10:30:00Z"
            }]
        }
    }


# ============ List Response ============

class SupplierListResponse(BaseModel):
    """
    Respuesta paginada de proveedores
    """
    total: int = Field(..., description="Total de proveedores que coinciden con filtros")
    items: List[SupplierResponse] = Field(..., description="Proveedores en esta página")
    limit: int = Field(..., description="Límite de resultados por página")
    offset: int = Field(..., description="Offset de paginación")


# ============ Summary/Stats Response ============

class SupplierSummary(BaseModel):
    """
    Resumen agregado de proveedores
    """
    total_suppliers: int = Field(..., description="Total de proveedores")
    by_status: dict = Field(..., description="Totales por estado")
    by_country: dict = Field(..., description="Totales por país")
    by_category: dict = Field(..., description="Totales por categoría")
    avg_delivery_rate_usd: float = Field(..., description="Tarifa promedio de entrega")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "total_suppliers": 20,
                "by_status": {
                    "activo": 18,
                    "suspendido": 2
                },
                "by_country": {
                    "Colombia": 12,
                    "USA": 8
                },
                "by_category": {
                    "carne_proteinas": 5,
                    "verduras_vegetales": 4,
                    "bebidas": 3
                },
                "avg_delivery_rate_usd": 28.75
            }]
        }
    }
