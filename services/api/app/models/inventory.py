"""
Inventory ORM Models for Brasaland

Modelos para gestión de inventario de ingredientes (materia prima).

Arquitectura:
- Ingredient: Producto/ingrediente (ej. "Carne de res", "Arroz blanco")
- InboundOrder: Orden de entrada de stock (registra llegada de materia prima)
- OutboundOrder: Orden de salida de stock (registra uso en cocina)

Reglas de Negocio CRÍTICAS:
1. Stock es CALCULADO, nunca almacenado directamente
2. Fórmula: stock = SUM(inbound) - SUM(outbound)
3. user_uuid es string (referencia a TinyDB users, sin FK relacional)
4. Stock no puede ser negativo (validado en router)
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============ ENUMS ============

class MeasurementUnit(str, Enum):
    """Unidades de medida para ingredientes"""
    KG = "kg"           # Kilogramo
    G = "g"             # Gramo
    L = "l"             # Litro
    ML = "ml"           # Mililitro
    UNIT = "unit"       # Unidad (ej. huevos, limones)
    PACKAGE = "package" # Paquete


class WarehouseLocation(str, Enum):
    """Almacenes/sedes donde se gestiona inventario"""
    # Colombia
    MEDELLIN_CENTRO = "medellin_centro"
    MEDELLIN_POBLADO = "medellin_poblado"
    MEDELLIN_ENVIGADO = "medellin_envigado"
    BOGOTA_ZONA_ROSA = "bogota_zona_rosa"
    BOGOTA_USAQUEN = "bogota_usaquen"
    BOGOTA_SUBA = "bogota_suba"
    CALI_NORTE = "cali_norte"
    CALI_SUR = "cali_sur"
    CARTAGENA_CENTRO = "cartagena_centro"
    BARRANQUILLA_NORTE = "barranquilla_norte"
    # Florida
    MIAMI_BEACH = "miami_beach"
    MIAMI_DOWNTOWN = "miami_downtown"
    ORLANDO_INTERNATIONAL = "orlando_international"
    TAMPA_CENTRO = "tampa_centro"
    # Almacén central
    CENTRAL_WAREHOUSE = "central_warehouse"


# ============ MODELS ============

class Ingredient(SQLModel, table=True):
    """
    Ingrediente / Materia Prima

    Representa un ingrediente usado en cocina de Brasaland.
    El stock NO se almacena aquí, se calcula dinámicamente.
    """
    __tablename__ = "ingredients"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, nullable=False, index=True)
    sku: str = Field(max_length=100, nullable=False, unique=True, index=True)
    description: Optional[str] = Field(default=None, max_length=500)
    unit: MeasurementUnit = Field(nullable=False)

    # Niveles de alerta
    min_stock: float = Field(default=0.0, ge=0.0)  # Alerta cuando stock < min_stock
    reorder_point: Optional[float] = Field(default=None, ge=0.0)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships (SQLModel genera las FKs automáticamente)
    inbound_orders: List["InboundOrder"] = Relationship(back_populates="ingredient")
    outbound_orders: List["OutboundOrder"] = Relationship(back_populates="ingredient")


class InboundOrder(SQLModel, table=True):
    """
    Orden de Entrada de Stock

    Registra la llegada de materia prima al almacén.
    Incrementa el stock disponible.

    CRÍTICO: user_uuid es string (referencia lógica a TinyDB, sin FK)
    """
    __tablename__ = "inbound_orders"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Relación con Ingredient (FK relacional)
    ingredient_id: int = Field(foreign_key="ingredients.id", nullable=False, index=True)
    ingredient: Optional[Ingredient] = Relationship(back_populates="inbound_orders")

    # Cantidad de entrada
    quantity: float = Field(gt=0.0, nullable=False)  # Debe ser positiva

    # Ubicación (almacén/sede)
    warehouse: WarehouseLocation = Field(nullable=False, index=True)

    # Usuario que registró la entrada (referencia string a TinyDB users)
    # NO es FK relacional porque users está en TinyDB, no en Supabase
    user_uuid: str = Field(max_length=255, nullable=False, index=True)

    # Metadata
    notes: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)


class OutboundOrder(SQLModel, table=True):
    """
    Orden de Salida de Stock

    Registra el uso/consumo de materia prima (cocina, merma, etc.).
    Decrementa el stock disponible.

    CRÍTICO:
    - user_uuid es string (referencia lógica a TinyDB, sin FK)
    - Validación de stock no negativo se hace en router ANTES de persistir
    """
    __tablename__ = "outbound_orders"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Relación con Ingredient (FK relacional)
    ingredient_id: int = Field(foreign_key="ingredients.id", nullable=False, index=True)
    ingredient: Optional[Ingredient] = Relationship(back_populates="outbound_orders")

    # Cantidad de salida
    quantity: float = Field(gt=0.0, nullable=False)  # Debe ser positiva

    # Ubicación (almacén/sede)
    warehouse: WarehouseLocation = Field(nullable=False, index=True)

    # Usuario que registró la salida (referencia string a TinyDB users)
    user_uuid: str = Field(max_length=255, nullable=False, index=True)

    # Metadata
    reason: Optional[str] = Field(default=None, max_length=500)  # Motivo: cocina, merma, etc.
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)
