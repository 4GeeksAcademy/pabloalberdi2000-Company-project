"""
Supplier Management Router - FastAPI

API REST para gestión de proveedores de Brasaland.
Reemplaza la hoja de cálculo manual con endpoints CRUD completos.

Endpoints:
- POST /api/suppliers - Crear proveedor
- GET /api/suppliers - Listar con filtros
- GET /api/suppliers/{id} - Obtener detalle
- PUT /api/suppliers/{id} - Actualizar campos
- PATCH /api/suppliers/{id}/rate - Actualizar tarifa
- PATCH /api/suppliers/{id}/status - Actualizar estado
- DELETE /api/suppliers/{id} - Eliminar proveedor
- GET /api/suppliers/summary - Métricas agregadas
"""
from fastapi import APIRouter, Depends, Query, status
from typing import Optional

from app.schemas.supplier import (
    SupplierCreate,
    SupplierUpdate,
    SupplierRateUpdate,
    SupplierStatusUpdate,
    SupplierResponse,
    SupplierListResponse,
    SupplierSummary,
    SupplierStatus,
    SupplierCategory,
    Country
)
from app.services.supplier_service import (
    create_new_supplier,
    get_supplier_by_doc_id,
    update_supplier_rate,
    update_supplier_status,
    update_supplier_fields,
    delete_supplier_by_id,
    list_suppliers_with_filters,
    get_suppliers_summary
)
from app.auth.dependencies import get_current_active_user

router = APIRouter(prefix="/api/suppliers", tags=["Suppliers"])


@router.post(
    "",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear proveedor",
    description="Crear nuevo proveedor con validación estricta de Pydantic"
)
async def create_supplier(
    data: SupplierCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Crear nuevo proveedor.

    Validaciones automáticas (Pydantic):
    - name: requerido, no vacío
    - country: Colombia o USA
    - categories: lista no vacía de categorías válidas
    - delivery_rate_usd: mayor que 0
    - status: activo o suspendido

    Retorna 422 Unprocessable Entity si alguna validación falla.
    Retorna 409 Conflict si ya existe proveedor con ese nombre.
    """
    return create_new_supplier(data)


@router.get(
    "",
    response_model=SupplierListResponse,
    summary="Listar proveedores",
    description="Listar proveedores con filtros opcionales y paginación"
)
async def list_suppliers(
    status: Optional[SupplierStatus] = Query(None, description="Filtrar por estado"),
    country: Optional[Country] = Query(None, description="Filtrar por país"),
    category: Optional[SupplierCategory] = Query(None, description="Filtrar por categoría"),
    limit: int = Query(100, ge=1, le=500, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset de paginación"),
    current_user: dict = Depends(get_current_active_user)
):
    """
    Listar proveedores con filtros opcionales.

    Filtros disponibles:
    - status: activo | suspendido
    - country: Colombia | USA
    - category: una de las 6 categorías del BRIEFING

    Paginación:
    - limit: máximo 500 resultados por página
    - offset: desplazamiento para paginación
    """
    items, total = list_suppliers_with_filters(
        status=status,
        country=country,
        category=category,
        limit=limit,
        offset=offset
    )

    return SupplierListResponse(
        total=total,
        items=items,
        limit=limit,
        offset=offset
    )


@router.get(
    "/summary",
    response_model=SupplierSummary,
    summary="Resumen de proveedores",
    description="Métricas agregadas de proveedores"
)
async def get_summary(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Obtener métricas agregadas de proveedores.

    Retorna:
    - total_suppliers: Total de proveedores
    - by_status: Totales por estado
    - by_country: Totales por país
    - by_category: Totales por categoría
    - avg_delivery_rate_usd: Tarifa promedio
    """
    return get_suppliers_summary()


@router.get(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Obtener proveedor",
    description="Obtener detalle de proveedor por ID"
)
async def get_supplier(
    supplier_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Obtener proveedor por ID.

    Retorna 404 Not Found si no existe.
    """
    return get_supplier_by_doc_id(supplier_id)


@router.put(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Actualizar proveedor",
    description="Actualizar campos de proveedor (actualización parcial)"
)
async def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Actualizar campos de proveedor.

    Solo actualiza campos proporcionados.
    Genera nuevo updated_at automáticamente.

    Retorna 404 Not Found si no existe.
    Retorna 409 Conflict si nuevo nombre ya existe.
    """
    return update_supplier_fields(supplier_id, data)


@router.patch(
    "/{supplier_id}/rate",
    response_model=SupplierResponse,
    summary="Actualizar tarifa",
    description="Actualizar tarifa de entrega (endpoint dedicado para auditoría)"
)
async def update_rate(
    supplier_id: int,
    data: SupplierRateUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Actualizar tarifa de entrega de proveedor.

    Endpoint dedicado para cambios de tarifa.
    Registra updated_at automáticamente para auditoría.

    Validación Pydantic:
    - delivery_rate_usd debe ser > 0

    Retorna 422 si tarifa <= 0.
    Retorna 404 si proveedor no existe.
    """
    return update_supplier_rate(supplier_id, data)


@router.patch(
    "/{supplier_id}/status",
    response_model=SupplierResponse,
    summary="Actualizar estado",
    description="Actualizar estado de proveedor (activo/suspendido)"
)
async def update_status(
    supplier_id: int,
    data: SupplierStatusUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Actualizar estado de proveedor.

    Estados válidos:
    - activo: Proveedor operativo
    - suspendido: Proveedor temporalmente inactivo

    Retorna 422 si estado inválido.
    Retorna 404 si proveedor no existe.
    """
    return update_supplier_status(supplier_id, data)


@router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar proveedor",
    description="Eliminar proveedor por ID"
)
async def delete_supplier(
    supplier_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Eliminar proveedor por ID.

    Retorna 204 No Content si se eliminó exitosamente.
    Retorna 404 Not Found si no existe.
    """
    delete_supplier_by_id(supplier_id)
