"""
Inventory Router for Brasaland

Endpoints para gestión de inventario de ingredientes.

Arquitectura de Doble Base de Datos:
- TinyDB: Autenticación (get_current_user)
- Supabase: Datos de inventario

Reglas de Negocio CRÍTICAS:
1. Stock es CALCULADO: SUM(inbound) - SUM(outbound)
2. Stock NO puede ser negativo (validado antes de persistir outbound)
3. user_uuid se obtiene del token JWT (TinyDB) y se almacena como string
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, func
from typing import List, Optional
from datetime import datetime

from ..database_supabase import get_inventory_db
from ..auth.dependencies import get_current_active_user
from ..models.inventory import Ingredient, InboundOrder, OutboundOrder, WarehouseLocation
from ..schemas.inventory import (
    IngredientCreate,
    IngredientUpdate,
    IngredientResponse,
    InboundOrderCreate,
    InboundOrderResponse,
    OutboundOrderCreate,
    OutboundOrderResponse,
    OrderResponse,
    StockReport,
    StockReportItem,
)

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"]
)


# ============ HELPER FUNCTIONS ============

def calculate_stock(
    db: Session,
    ingredient_id: int,
    warehouse: Optional[WarehouseLocation] = None
) -> float:
    """
    Calcular stock actual de un ingrediente.

    Fórmula: stock = SUM(inbound.quantity) - SUM(outbound.quantity)

    Args:
        db: Sesión de base de datos
        ingredient_id: ID del ingrediente
        warehouse: Filtrar por almacén específico (opcional)

    Returns:
        float: Stock actual (puede ser 0, nunca negativo si validaciones OK)
    """
    # Sumar entradas
    inbound_query = select(func.sum(InboundOrder.quantity)).where(
        InboundOrder.ingredient_id == ingredient_id
    )
    if warehouse:
        inbound_query = inbound_query.where(InboundOrder.warehouse == warehouse)

    total_inbound = db.exec(inbound_query).first() or 0.0

    # Sumar salidas
    outbound_query = select(func.sum(OutboundOrder.quantity)).where(
        OutboundOrder.ingredient_id == ingredient_id
    )
    if warehouse:
        outbound_query = outbound_query.where(OutboundOrder.warehouse == warehouse)

    total_outbound = db.exec(outbound_query).first() or 0.0

    return total_inbound - total_outbound


def get_stock_by_warehouse(db: Session, ingredient_id: int) -> dict:
    """
    Calcular stock desglosado por almacén.

    Returns:
        dict: {warehouse_name: stock_quantity}
    """
    result = {}
    for warehouse in WarehouseLocation:
        stock = calculate_stock(db, ingredient_id, warehouse)
        if stock > 0:  # Solo incluir almacenes con stock
            result[warehouse.value] = stock
    return result


# ============ INGREDIENT ENDPOINTS ============

@router.post("/ingredients", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED)
def create_ingredient(
    *,
    db: Session = Depends(get_inventory_db),
    current_user: dict = Depends(get_current_active_user),
    ingredient_data: IngredientCreate
):
    """
    Crear un nuevo ingrediente.

    Requiere: Autenticación JWT
    Stock inicial: 0 (se incrementa con inbound orders)
    """
    # Verificar que SKU no existe
    existing = db.exec(
        select(Ingredient).where(Ingredient.sku == ingredient_data.sku)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ingredient with SKU '{ingredient_data.sku}' already exists"
        )

    # Crear ingrediente
    ingredient = Ingredient(**ingredient_data.model_dump())
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)

    # Construir response con stock calculado (0 para nuevo ingrediente)
    return IngredientResponse(
        **ingredient.model_dump(),
        current_stock=0.0,
        stock_by_warehouse={}
    )


@router.get("/ingredients", response_model=List[IngredientResponse])
def list_ingredients(
    *,
    db: Session = Depends(get_inventory_db),
    current_user: dict = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    warehouse: Optional[WarehouseLocation] = Query(None)
):
    """
    Listar ingredientes con su stock actual calculado.

    Requiere: Autenticación JWT

    Query params:
    - skip: Paginación offset
    - limit: Paginación límite
    - warehouse: Filtrar stock por almacén específico
    """
    # Obtener ingredientes
    ingredients = db.exec(
        select(Ingredient).offset(skip).limit(limit)
    ).all()

    # Construir responses con stock calculado
    result = []
    for ingredient in ingredients:
        current_stock = calculate_stock(db, ingredient.id, warehouse)
        stock_by_warehouse = get_stock_by_warehouse(db, ingredient.id) if not warehouse else None

        result.append(
            IngredientResponse(
                **ingredient.model_dump(),
                current_stock=current_stock,
                stock_by_warehouse=stock_by_warehouse
            )
        )

    return result


@router.get("/ingredients/{ingredient_id}", response_model=IngredientResponse)
def get_ingredient(
    *,
    db: Session = Depends(get_inventory_db),
    current_user: dict = Depends(get_current_active_user),
    ingredient_id: int,
    warehouse: Optional[WarehouseLocation] = Query(None)
):
    """
    Obtener ingrediente por ID con stock actual calculado.

    Requiere: Autenticación JWT
    """
    ingredient = db.get(Ingredient, ingredient_id)

    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient with ID {ingredient_id} not found"
        )

    # Calcular stock
    current_stock = calculate_stock(db, ingredient.id, warehouse)
    stock_by_warehouse = get_stock_by_warehouse(db, ingredient.id)

    return IngredientResponse(
        **ingredient.model_dump(),
        current_stock=current_stock,
        stock_by_warehouse=stock_by_warehouse
    )


@router.put("/ingredients/{ingredient_id}", response_model=IngredientResponse)
def update_ingredient(
    *,
    db: Session = Depends(get_inventory_db),
    current_user: dict = Depends(get_current_active_user),
    ingredient_id: int,
    ingredient_data: IngredientUpdate
):
    """
    Actualizar datos de un ingrediente (NO afecta stock).

    Requiere: Autenticación JWT
    IMPORTANTE: Stock NO es actualizable aquí, solo mediante orders
    """
    ingredient = db.get(Ingredient, ingredient_id)

    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient with ID {ingredient_id} not found"
        )

    # Actualizar solo campos provistos
    update_data = ingredient_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ingredient, field, value)

    ingredient.updated_at = datetime.utcnow()

    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)

    # Calcular stock
    current_stock = calculate_stock(db, ingredient.id)
    stock_by_warehouse = get_stock_by_warehouse(db, ingredient.id)

    return IngredientResponse(
        **ingredient.model_dump(),
        current_stock=current_stock,
        stock_by_warehouse=stock_by_warehouse
    )


# ============ INBOUND ORDER ENDPOINTS ============

@router.post("/orders/inbound", response_model=InboundOrderResponse, status_code=status.HTTP_201_CREATED)
def create_inbound_order(
    *,
    db: Session = Depends(get_inventory_db),
    current_user: dict = Depends(get_current_active_user),
    order_data: InboundOrderCreate
):
    """
    Registrar una entrada de stock (llegada de materia prima).

    Requiere: Autenticación JWT
    Efecto: Incrementa el stock disponible
    user_uuid: Se obtiene automáticamente del token JWT
    """
    # Verificar que ingrediente existe
    ingredient = db.get(Ingredient, order_data.ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient with ID {order_data.ingredient_id} not found"
        )

    # Obtener user_uuid del usuario autenticado (TinyDB)
    user_uuid = str(current_user.doc_id)  # doc_id de TinyDB como string

    # Crear orden de entrada
    order = InboundOrder(
        **order_data.model_dump(),
        user_uuid=user_uuid
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    # Construir response con datos del ingrediente
    return InboundOrderResponse(
        **order.model_dump(),
        ingredient_name=ingredient.name,
        ingredient_sku=ingredient.sku
    )


# ============ OUTBOUND ORDER ENDPOINTS ============

@router.post("/orders/outbound", response_model=OutboundOrderResponse, status_code=status.HTTP_201_CREATED)
def create_outbound_order(
    *,
    db: Session = Depends(get_inventory_db),
    current_user: dict = Depends(get_current_active_user),
    order_data: OutboundOrderCreate
):
    """
    Registrar una salida de stock (uso en cocina, merma, etc.).

    Requiere: Autenticación JWT
    Efecto: Decrementa el stock disponible

    ⚠️ CRÍTICO: Valida que stock no quede negativo ANTES de persistir.
    Si stock resultante < 0 → HTTP 400 (rechaza orden)
    """
    # Verificar que ingrediente existe
    ingredient = db.get(Ingredient, order_data.ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient with ID {order_data.ingredient_id} not found"
        )

    # ⚠️ VALIDACIÓN CRÍTICA: Stock no negativo
    current_stock = calculate_stock(
        db,
        order_data.ingredient_id,
        order_data.warehouse
    )

    if current_stock < order_data.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient stock for '{ingredient.name}' in {order_data.warehouse.value}. "
                f"Available: {current_stock} {ingredient.unit.value}, "
                f"Requested: {order_data.quantity} {ingredient.unit.value}"
            )
        )

    # Obtener user_uuid del usuario autenticado (TinyDB)
    user_uuid = str(current_user.doc_id)

    # Crear orden de salida
    order = OutboundOrder(
        **order_data.model_dump(),
        user_uuid=user_uuid
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    # Construir response con datos del ingrediente
    return OutboundOrderResponse(
        **order.model_dump(),
        ingredient_name=ingredient.name,
        ingredient_sku=ingredient.sku
    )


# ============ ORDERS LIST ENDPOINT ============

@router.get("/orders", response_model=List[OrderResponse])
def list_orders(
    *,
    db: Session = Depends(get_inventory_db),
    current_user: dict = Depends(get_current_active_user),
    order_type: Optional[str] = Query(None, regex="^(inbound|outbound)$"),
    ingredient_id: Optional[int] = Query(None),
    warehouse: Optional[WarehouseLocation] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Listar todas las órdenes (inbound + outbound).

    Requiere: Autenticación JWT

    Query params:
    - order_type: Filtrar por 'inbound' o 'outbound'
    - ingredient_id: Filtrar por ingrediente
    - warehouse: Filtrar por almacén
    - skip, limit: Paginación
    """
    result = []

    # Listar inbound orders si aplica
    if not order_type or order_type == "inbound":
        inbound_query = select(InboundOrder, Ingredient).join(Ingredient)

        if ingredient_id:
            inbound_query = inbound_query.where(InboundOrder.ingredient_id == ingredient_id)
        if warehouse:
            inbound_query = inbound_query.where(InboundOrder.warehouse == warehouse)

        inbound_orders = db.exec(inbound_query.offset(skip).limit(limit)).all()

        for order, ingredient in inbound_orders:
            result.append(OrderResponse(
                id=order.id,
                type="inbound",
                ingredient_id=order.ingredient_id,
                ingredient_name=ingredient.name,
                ingredient_sku=ingredient.sku,
                quantity=order.quantity,
                warehouse=order.warehouse,
                user_uuid=order.user_uuid,
                notes_or_reason=order.notes,
                created_at=order.created_at
            ))

    # Listar outbound orders si aplica
    if not order_type or order_type == "outbound":
        outbound_query = select(OutboundOrder, Ingredient).join(Ingredient)

        if ingredient_id:
            outbound_query = outbound_query.where(OutboundOrder.ingredient_id == ingredient_id)
        if warehouse:
            outbound_query = outbound_query.where(OutboundOrder.warehouse == warehouse)

        outbound_orders = db.exec(outbound_query.offset(skip).limit(limit)).all()

        for order, ingredient in outbound_orders:
            result.append(OrderResponse(
                id=order.id,
                type="outbound",
                ingredient_id=order.ingredient_id,
                ingredient_name=ingredient.name,
                ingredient_sku=ingredient.sku,
                quantity=order.quantity,
                warehouse=order.warehouse,
                user_uuid=order.user_uuid,
                notes_or_reason=order.reason,
                created_at=order.created_at
            ))

    # Ordenar por fecha (más reciente primero)
    result.sort(key=lambda x: x.created_at, reverse=True)

    return result


# ============ STOCK REPORT ENDPOINT ============

@router.get("/stock-report", response_model=StockReport)
def get_stock_report(
    *,
    db: Session = Depends(get_inventory_db),
    current_user: dict = Depends(get_current_active_user),
    low_stock_only: bool = Query(False)
):
    """
    Generar reporte completo de stock.

    Requiere: Autenticación JWT

    Query params:
    - low_stock_only: Solo mostrar ingredientes con stock < reorder_point
    """
    ingredients = db.exec(select(Ingredient)).all()

    items = []
    low_stock_count = 0

    for ingredient in ingredients:
        current_stock = calculate_stock(db, ingredient.id)
        stock_by_warehouse = get_stock_by_warehouse(db, ingredient.id)

        needs_reorder = False
        if ingredient.reorder_point and current_stock < ingredient.reorder_point:
            needs_reorder = True
            low_stock_count += 1

        # Filtrar si solo se quieren items con stock bajo
        if low_stock_only and not needs_reorder:
            continue

        items.append(StockReportItem(
            ingredient_id=ingredient.id,
            ingredient_name=ingredient.name,
            ingredient_sku=ingredient.sku,
            unit=ingredient.unit,
            current_stock=current_stock,
            min_stock=ingredient.min_stock,
            reorder_point=ingredient.reorder_point,
            needs_reorder=needs_reorder,
            stock_by_warehouse=stock_by_warehouse
        ))

    return StockReport(
        total_ingredients=len(ingredients),
        low_stock_count=low_stock_count,
        items=items
    )
