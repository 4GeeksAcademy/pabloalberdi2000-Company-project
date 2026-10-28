"""
Inventory Pydantic Schemas for Brasaland

Schemas desacoplados de los modelos ORM para validación y serialización.

Arquitectura:
- Schemas de entrada (Create): Datos para crear registros
- Schemas de salida (Response): Datos para respuestas HTTP
- Schemas computados: Incluyen campos calculados (ej. current_stock)

CRÍTICO:
- IngredientResponse DEBE incluir current_stock calculado
- NUNCA retornar objetos ORM directamente en responses
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict
from datetime import datetime
from ..models.inventory import MeasurementUnit, WarehouseLocation


# ============ INGREDIENT SCHEMAS ============

class IngredientCreate(BaseModel):
    """Schema para crear un nuevo ingrediente"""
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    unit: MeasurementUnit
    min_stock: float = Field(default=0.0, ge=0.0)
    reorder_point: Optional[float] = Field(None, ge=0.0)

    @validator('name', 'sku')
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty or whitespace')
        return v.strip()


class IngredientUpdate(BaseModel):
    """Schema para actualizar un ingrediente (sin cambiar stock)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    unit: Optional[MeasurementUnit] = None
    min_stock: Optional[float] = Field(None, ge=0.0)
    reorder_point: Optional[float] = Field(None, ge=0.0)


class IngredientResponse(BaseModel):
    """
    Schema de respuesta para ingrediente.

    CRÍTICO: Incluye current_stock calculado dinámicamente.
    El stock NO viene del modelo ORM, se calcula en el router.
    """
    id: int
    name: str
    sku: str
    description: Optional[str]
    unit: MeasurementUnit
    min_stock: float
    reorder_point: Optional[float]
    created_at: datetime
    updated_at: datetime

    # ⚠️ CAMPO CALCULADO - No existe en la tabla
    current_stock: float = Field(
        ...,
        description="Stock actual calculado: SUM(inbound) - SUM(outbound)"
    )

    # Stock por almacén (opcional, para vista detallada)
    stock_by_warehouse: Optional[Dict[str, float]] = Field(
        None,
        description="Stock desglosado por almacén/sede"
    )

    class Config:
        from_attributes = True  # Permite construir desde objetos ORM


# ============ INBOUND ORDER SCHEMAS ============

class InboundOrderCreate(BaseModel):
    """Schema para registrar una entrada de stock"""
    ingredient_id: int = Field(..., gt=0)
    quantity: float = Field(..., gt=0.0)
    warehouse: WarehouseLocation
    notes: Optional[str] = Field(None, max_length=500)

    # user_uuid se obtiene automáticamente de get_current_user, no se envía en body


class InboundOrderResponse(BaseModel):
    """Schema de respuesta para orden de entrada"""
    id: int
    ingredient_id: int
    quantity: float
    warehouse: WarehouseLocation
    user_uuid: str
    notes: Optional[str]
    created_at: datetime

    # Datos del ingrediente asociado (para evitar N+1 queries)
    ingredient_name: Optional[str] = None
    ingredient_sku: Optional[str] = None

    class Config:
        from_attributes = True


# ============ OUTBOUND ORDER SCHEMAS ============

class OutboundOrderCreate(BaseModel):
    """
    Schema para registrar una salida de stock.

    CRÍTICO: Validación de stock no negativo se hace en router,
    NO en el schema (requiere consulta a DB).
    """
    ingredient_id: int = Field(..., gt=0)
    quantity: float = Field(..., gt=0.0)
    warehouse: WarehouseLocation
    reason: Optional[str] = Field(None, max_length=500)

    # user_uuid se obtiene automáticamente de get_current_user


class OutboundOrderResponse(BaseModel):
    """Schema de respuesta para orden de salida"""
    id: int
    ingredient_id: int
    quantity: float
    warehouse: WarehouseLocation
    user_uuid: str
    reason: Optional[str]
    created_at: datetime

    # Datos del ingrediente asociado
    ingredient_name: Optional[str] = None
    ingredient_sku: Optional[str] = None

    class Config:
        from_attributes = True


# ============ COMBINED ORDER RESPONSE ============

class OrderResponse(BaseModel):
    """Schema unificado para listar órdenes (inbound + outbound)"""
    id: int
    type: str = Field(..., description="'inbound' o 'outbound'")
    ingredient_id: int
    ingredient_name: str
    ingredient_sku: str
    quantity: float
    warehouse: WarehouseLocation
    user_uuid: str
    notes_or_reason: Optional[str] = Field(None, description="notes (inbound) o reason (outbound)")
    created_at: datetime


# ============ STOCK REPORT SCHEMA ============

class StockReportItem(BaseModel):
    """Item de reporte de stock por ingrediente"""
    ingredient_id: int
    ingredient_name: str
    ingredient_sku: str
    unit: MeasurementUnit
    current_stock: float
    min_stock: float
    reorder_point: Optional[float]
    needs_reorder: bool = Field(..., description="True si stock < reorder_point")
    stock_by_warehouse: Dict[str, float]


class StockReport(BaseModel):
    """Reporte completo de stock"""
    total_ingredients: int
    low_stock_count: int = Field(..., description="Ingredientes bajo mínimo")
    items: list[StockReportItem]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
