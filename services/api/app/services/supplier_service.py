"""
Supplier Service - Business logic layer

Gestión de lógica de negocio para proveedores de Brasaland.
Reutiliza el patrón establecido en incident_service.py.
"""
from typing import Optional, List, Tuple
from datetime import datetime
from fastapi import HTTPException

from ..schemas.supplier import (
    SupplierCreate,
    SupplierUpdate,
    SupplierRateUpdate,
    SupplierStatusUpdate,
    SupplierResponse,
    SupplierSummary,
    SupplierStatus,
    SupplierCategory,
    Country
)
from ..tinydb_database import (
    get_supplier_by_id,
    get_supplier_by_name,
    create_supplier,
    update_supplier,
    delete_supplier,
    list_suppliers,
    count_suppliers,
    suppliers_table
)


def create_new_supplier(data: SupplierCreate) -> SupplierResponse:
    """
    Crear nuevo proveedor.

    Validaciones:
    - Nombre único (no permitir duplicados)
    - Timestamps automáticos (created_at, updated_at)

    Args:
        data: Datos del proveedor

    Returns:
        Proveedor creado con ID asignado

    Raises:
        HTTPException 409: Si ya existe proveedor con ese nombre
    """
    # Verificar que no exista proveedor con ese nombre
    existing = get_supplier_by_name(data.name)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Supplier with name '{data.name}' already exists"
        )

    # Crear documento con timestamps
    now = datetime.utcnow().isoformat()
    doc = {
        "name": data.name,
        "country": data.country.value,
        "categories": [cat.value for cat in data.categories],
        "delivery_rate_usd": data.delivery_rate_usd,
        "status": data.status.value,
        "contact_email": data.contact_email,
        "contact_phone": data.contact_phone,
        "created_at": now,
        "updated_at": now
    }

    # Insertar y retornar con ID
    created = create_supplier(doc)
    return _doc_to_response(created)


def get_supplier_by_doc_id(supplier_id: int) -> SupplierResponse:
    """
    Obtener proveedor por ID.

    Args:
        supplier_id: ID del documento en TinyDB

    Returns:
        Proveedor encontrado

    Raises:
        HTTPException 404: Si no existe
    """
    supplier = get_supplier_by_id(supplier_id)
    if not supplier:
        raise HTTPException(
            status_code=404,
            detail=f"Supplier with ID {supplier_id} not found"
        )
    return _doc_to_response(supplier)


def update_supplier_rate(supplier_id: int, data: SupplierRateUpdate) -> SupplierResponse:
    """
    Actualizar tarifa de entrega de proveedor.

    Genera nuevo updated_at para auditoría de cambios de precios.

    Args:
        supplier_id: ID del proveedor
        data: Nueva tarifa

    Returns:
        Proveedor actualizado

    Raises:
        HTTPException 404: Si no existe
    """
    supplier = get_supplier_by_id(supplier_id)
    if not supplier:
        raise HTTPException(
            status_code=404,
            detail=f"Supplier with ID {supplier_id} not found"
        )

    # Actualizar solo tarifa y timestamp
    update_data = {
        "delivery_rate_usd": data.delivery_rate_usd,
        "updated_at": datetime.utcnow().isoformat()
    }

    updated = update_supplier(supplier_id, update_data)
    return _doc_to_response(updated)


def update_supplier_status(supplier_id: int, data: SupplierStatusUpdate) -> SupplierResponse:
    """
    Actualizar estado de proveedor.

    Args:
        supplier_id: ID del proveedor
        data: Nuevo estado

    Returns:
        Proveedor actualizado

    Raises:
        HTTPException 404: Si no existe
    """
    supplier = get_supplier_by_id(supplier_id)
    if not supplier:
        raise HTTPException(
            status_code=404,
            detail=f"Supplier with ID {supplier_id} not found"
        )

    # Actualizar solo estado y timestamp
    update_data = {
        "status": data.status.value,
        "updated_at": datetime.utcnow().isoformat()
    }

    updated = update_supplier(supplier_id, update_data)
    return _doc_to_response(updated)


def update_supplier_fields(supplier_id: int, data: SupplierUpdate) -> SupplierResponse:
    """
    Actualizar campos de proveedor (PUT parcial).

    Solo actualiza campos proporcionados.

    Args:
        supplier_id: ID del proveedor
        data: Campos a actualizar

    Returns:
        Proveedor actualizado

    Raises:
        HTTPException 404: Si no existe
        HTTPException 409: Si nuevo nombre ya existe
    """
    supplier = get_supplier_by_id(supplier_id)
    if not supplier:
        raise HTTPException(
            status_code=404,
            detail=f"Supplier with ID {supplier_id} not found"
        )

    # Verificar nombre único si se está actualizando
    if data.name and data.name != supplier["name"]:
        existing = get_supplier_by_name(data.name)
        if existing and existing.doc_id != supplier_id:
            raise HTTPException(
                status_code=409,
                detail=f"Supplier with name '{data.name}' already exists"
            )

    # Construir update_data solo con campos proporcionados
    update_data = {"updated_at": datetime.utcnow().isoformat()}

    if data.name is not None:
        update_data["name"] = data.name
    if data.country is not None:
        update_data["country"] = data.country.value
    if data.categories is not None:
        update_data["categories"] = [cat.value for cat in data.categories]
    if data.delivery_rate_usd is not None:
        update_data["delivery_rate_usd"] = data.delivery_rate_usd
    if data.status is not None:
        update_data["status"] = data.status.value
    if data.contact_email is not None:
        update_data["contact_email"] = data.contact_email
    if data.contact_phone is not None:
        update_data["contact_phone"] = data.contact_phone

    updated = update_supplier(supplier_id, update_data)
    return _doc_to_response(updated)


def delete_supplier_by_id(supplier_id: int) -> None:
    """
    Eliminar proveedor por ID.

    Args:
        supplier_id: ID del proveedor

    Raises:
        HTTPException 404: Si no existe
    """
    supplier = get_supplier_by_id(supplier_id)
    if not supplier:
        raise HTTPException(
            status_code=404,
            detail=f"Supplier with ID {supplier_id} not found"
        )

    delete_supplier(supplier_id)


def list_suppliers_with_filters(
    status: Optional[SupplierStatus] = None,
    country: Optional[Country] = None,
    category: Optional[SupplierCategory] = None,
    limit: int = 100,
    offset: int = 0
) -> Tuple[List[SupplierResponse], int]:
    """
    Listar proveedores con filtros y paginación.

    Args:
        status: Filtrar por estado
        country: Filtrar por país
        category: Filtrar por categoría
        limit: Límite de resultados
        offset: Offset de paginación

    Returns:
        Tupla (lista de proveedores, total)
    """
    filters = {}

    if status is not None:
        filters["status"] = status.value
    if country is not None:
        filters["country"] = country.value

    # Categoría requiere búsqueda especial (array contains)
    if category is not None:
        # Para simplificar, buscar todos y filtrar en Python
        # TinyDB no soporta búsqueda nativa de "contains" en arrays
        all_suppliers = list_suppliers(filters, limit=1000, offset=0)
        filtered = [
            s for s in all_suppliers
            if category.value in s.get("categories", [])
        ]
        total = len(filtered)
        items = filtered[offset:offset + limit]
    else:
        items = list_suppliers(filters, limit, offset)
        total = count_suppliers(filters)

    return [_doc_to_response(s) for s in items], total


def get_suppliers_summary() -> SupplierSummary:
    """
    Calcular métricas agregadas de proveedores.

    Returns:
        Resumen con totales y promedios
    """
    all_suppliers = suppliers_table.all()

    by_status = {}
    by_country = {}
    by_category = {}
    total_rate = 0.0

    for supplier in all_suppliers:
        # Totales por estado
        status = supplier.get("status", "activo")
        by_status[status] = by_status.get(status, 0) + 1

        # Totales por país
        country = supplier.get("country", "Unknown")
        by_country[country] = by_country.get(country, 0) + 1

        # Totales por categoría
        for cat in supplier.get("categories", []):
            by_category[cat] = by_category.get(cat, 0) + 1

        # Suma de tarifas para promedio
        total_rate += supplier.get("delivery_rate_usd", 0.0)

    avg_rate = total_rate / len(all_suppliers) if all_suppliers else 0.0

    return SupplierSummary(
        total_suppliers=len(all_suppliers),
        by_status=by_status,
        by_country=by_country,
        by_category=by_category,
        avg_delivery_rate_usd=round(avg_rate, 2)
    )


# ============================================================
# HELPERS
# ============================================================

def _doc_to_response(doc: dict) -> SupplierResponse:
    """
    Convertir documento de TinyDB a SupplierResponse.

    TinyDB almacena el doc_id en un campo especial, lo exponemos como 'id'.

    Args:
        doc: Documento de TinyDB

    Returns:
        SupplierResponse con ID
    """
    return SupplierResponse(
        id=doc.doc_id,
        name=doc["name"],
        country=Country(doc["country"]),
        categories=[SupplierCategory(cat) for cat in doc["categories"]],
        delivery_rate_usd=doc["delivery_rate_usd"],
        status=SupplierStatus(doc["status"]),
        contact_email=doc.get("contact_email"),
        contact_phone=doc.get("contact_phone"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"]
    )
