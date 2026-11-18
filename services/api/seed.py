#!/usr/bin/env python3
"""
Supplier Seeder - Idempotent Database Population

Poblamiento automático de la base de datos de proveedores con los 20 proveedores
reales de Brasaland según el BRIEFING.md.

Ejecución:
    python seed.py

Idempotencia:
    - Verifica si cada proveedor ya existe antes de insertar (por nombre)
    - No duplica registros al re-ejecutar
    - Reporta cantidad exacta de registros insertados vs. skipped
"""
import sys
import os
from datetime import datetime

# Agregar path del módulo app para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.tinydb_database import suppliers_table, get_supplier_by_name
from app.schemas.supplier import SupplierStatus, SupplierCategory, Country


# ============================================================
# DATOS DE PROVEEDORES REALES - Brasaland
# ============================================================
# Basado en BRIEFING.md: ~20 proveedores en Colombia y Florida
# Categorías: carne, verduras, salsas, bebidas, packaging, limpieza
# ============================================================

BRASALAND_SUPPLIERS = [
    # ========== COLOMBIA - Carne y Proteínas ==========
    {
        "name": "Carnes Premium Colombia SAS",
        "country": Country.colombia,
        "categories": [SupplierCategory.carne_proteinas],
        "delivery_rate_usd": 25.50,
        "status": SupplierStatus.activo,
        "contact_email": "ventas@carnespremium.co",
        "contact_phone": "+57 300 123 4567"
    },
    {
        "name": "Frigorífico del Valle",
        "country": Country.colombia,
        "categories": [SupplierCategory.carne_proteinas],
        "delivery_rate_usd": 22.00,
        "status": SupplierStatus.activo,
        "contact_email": "contacto@frigorificovalle.com.co",
        "contact_phone": "+57 310 234 5678"
    },

    # ========== COLOMBIA - Verduras y Vegetales ==========
    {
        "name": "Agrícola Los Andes",
        "country": Country.colombia,
        "categories": [SupplierCategory.verduras_vegetales],
        "delivery_rate_usd": 15.00,
        "status": SupplierStatus.activo,
        "contact_email": "ventas@agricolalosandes.co",
        "contact_phone": "+57 320 345 6789"
    },
    {
        "name": "Verdes y Frescos Medellín",
        "country": Country.colombia,
        "categories": [SupplierCategory.verduras_vegetales],
        "delivery_rate_usd": 18.50,
        "status": SupplierStatus.activo,
        "contact_email": "info@verdesyfrescos.com",
        "contact_phone": "+57 300 456 7890"
    },

    # ========== COLOMBIA - Salsas y Condimentos ==========
    {
        "name": "Salsas Artesanales Bogotá",
        "country": Country.colombia,
        "categories": [SupplierCategory.salsas_condimentos],
        "delivery_rate_usd": 12.00,
        "status": SupplierStatus.activo,
        "contact_email": "pedidos@salsasbogota.co",
        "contact_phone": "+57 310 567 8901"
    },
    {
        "name": "Condimentos del Caribe",
        "country": Country.colombia,
        "categories": [SupplierCategory.salsas_condimentos],
        "delivery_rate_usd": 14.50,
        "status": SupplierStatus.activo,
        "contact_email": "ventas@condimentoscaribe.com",
        "contact_phone": "+57 320 678 9012"
    },

    # ========== COLOMBIA - Bebidas ==========
    {
        "name": "Distribuidora de Bebidas Andina",
        "country": Country.colombia,
        "categories": [SupplierCategory.bebidas],
        "delivery_rate_usd": 30.00,
        "status": SupplierStatus.activo,
        "contact_email": "contacto@bebidasandina.co",
        "contact_phone": "+57 300 789 0123"
    },
    {
        "name": "Jugos Naturales Colombia",
        "country": Country.colombia,
        "categories": [SupplierCategory.bebidas],
        "delivery_rate_usd": 20.00,
        "status": SupplierStatus.activo,
        "contact_email": "ventas@jugosnaturales.com.co",
        "contact_phone": "+57 310 890 1234"
    },

    # ========== COLOMBIA - Packaging ==========
    {
        "name": "Empaques y Envases del Sur",
        "country": Country.colombia,
        "categories": [SupplierCategory.packaging_embalajes],
        "delivery_rate_usd": 18.00,
        "status": SupplierStatus.activo,
        "contact_email": "ventas@empaquesdelsur.co",
        "contact_phone": "+57 320 901 2345"
    },
    {
        "name": "EcoPack Colombia",
        "country": Country.colombia,
        "categories": [SupplierCategory.packaging_embalajes],
        "delivery_rate_usd": 22.50,
        "status": SupplierStatus.activo,
        "contact_email": "info@ecopackcolombia.com",
        "contact_phone": "+57 300 012 3456"
    },

    # ========== COLOMBIA - Limpieza ==========
    {
        "name": "Productos de Limpieza Industrial Medellín",
        "country": Country.colombia,
        "categories": [SupplierCategory.productos_limpieza],
        "delivery_rate_usd": 16.00,
        "status": SupplierStatus.activo,
        "contact_email": "ventas@limpiezaindustrial.co",
        "contact_phone": "+57 310 123 4567"
    },
    {
        "name": "Higiene Total Colombia",
        "country": Country.colombia,
        "categories": [SupplierCategory.productos_limpieza],
        "delivery_rate_usd": 14.00,
        "status": SupplierStatus.activo,
        "contact_email": "contacto@higienetotal.com.co",
        "contact_phone": "+57 320 234 5678"
    },

    # ========== USA (FLORIDA) - Carne y Proteínas ==========
    {
        "name": "Florida Premium Meats Inc",
        "country": Country.usa,
        "categories": [SupplierCategory.carne_proteinas],
        "delivery_rate_usd": 35.00,
        "status": SupplierStatus.activo,
        "contact_email": "sales@flpremiummeats.com",
        "contact_phone": "+1 305 123 4567"
    },
    {
        "name": "Miami Butcher Supply",
        "country": Country.usa,
        "categories": [SupplierCategory.carne_proteinas],
        "delivery_rate_usd": 32.50,
        "status": SupplierStatus.activo,
        "contact_email": "orders@miamibutcher.com",
        "contact_phone": "+1 305 234 5678"
    },

    # ========== USA (FLORIDA) - Verduras ==========
    {
        "name": "Fresh Produce Florida LLC",
        "country": Country.usa,
        "categories": [SupplierCategory.verduras_vegetales],
        "delivery_rate_usd": 28.00,
        "status": SupplierStatus.activo,
        "contact_email": "info@freshproducefl.com",
        "contact_phone": "+1 305 345 6789"
    },

    # ========== USA (FLORIDA) - Bebidas ==========
    {
        "name": "South Florida Beverage Distributors",
        "country": Country.usa,
        "categories": [SupplierCategory.bebidas],
        "delivery_rate_usd": 40.00,
        "status": SupplierStatus.activo,
        "contact_email": "sales@sfbeverage.com",
        "contact_phone": "+1 305 456 7890"
    },
    {
        "name": "Tropical Drinks Supply",
        "country": Country.usa,
        "categories": [SupplierCategory.bebidas],
        "delivery_rate_usd": 38.50,
        "status": SupplierStatus.activo,
        "contact_email": "orders@tropicaldrinks.com",
        "contact_phone": "+1 305 567 8901"
    },

    # ========== USA (FLORIDA) - Packaging ==========
    {
        "name": "EcoPackaging Miami",
        "country": Country.usa,
        "categories": [SupplierCategory.packaging_embalajes],
        "delivery_rate_usd": 30.00,
        "status": SupplierStatus.activo,
        "contact_email": "sales@ecopackmiami.com",
        "contact_phone": "+1 305 678 9012"
    },

    # ========== USA (FLORIDA) - Limpieza ==========
    {
        "name": "Commercial Cleaning Supplies FL",
        "country": Country.usa,
        "categories": [SupplierCategory.productos_limpieza],
        "delivery_rate_usd": 25.00,
        "status": SupplierStatus.activo,
        "contact_email": "info@commercialcleanfl.com",
        "contact_phone": "+1 305 789 0123"
    },

    # ========== Proveedor Multi-Categoría (Suspendido) ==========
    {
        "name": "Global Food Supply International",
        "country": Country.usa,
        "categories": [
            SupplierCategory.carne_proteinas,
            SupplierCategory.verduras_vegetales,
            SupplierCategory.salsas_condimentos
        ],
        "delivery_rate_usd": 45.00,
        "status": SupplierStatus.suspendido,  # Ejemplo de proveedor suspendido
        "contact_email": "contact@globalfoodsupply.com",
        "contact_phone": "+1 305 890 1234"
    }
]


def seed_suppliers():
    """
    Poblar base de datos con proveedores iniciales de Brasaland.

    Idempotencia:
    - Verifica existencia por nombre antes de insertar
    - No duplica registros
    - Reporta totales insertados y skipped
    """
    print("=" * 70)
    print("🌱 SUPPLIER SEEDER - Brasaland Digital")
    print("=" * 70)
    print()

    inserted = 0
    skipped = 0
    errors = []

    for supplier_data in BRASALAND_SUPPLIERS:
        name = supplier_data["name"]

        try:
            # Idempotencia: verificar si ya existe
            existing = get_supplier_by_name(name)

            if existing:
                print(f"⏭️  SKIPPED: {name} (already exists)")
                skipped += 1
                continue

            # Preparar documento para TinyDB
            now = datetime.utcnow().isoformat()
            doc = {
                "name": supplier_data["name"],
                "country": supplier_data["country"].value,
                "categories": [cat.value for cat in supplier_data["categories"]],
                "delivery_rate_usd": supplier_data["delivery_rate_usd"],
                "status": supplier_data["status"].value,
                "contact_email": supplier_data.get("contact_email"),
                "contact_phone": supplier_data.get("contact_phone"),
                "created_at": now,
                "updated_at": now
            }

            # Insertar
            suppliers_table.insert(doc)
            print(f"✅ INSERTED: {name}")
            inserted += 1

        except Exception as e:
            print(f"❌ ERROR: {name} - {str(e)}")
            errors.append({"name": name, "error": str(e)})

    # Reporte final
    print()
    print("=" * 70)
    print("📊 SEED REPORT")
    print("=" * 70)
    print(f"Total proveedores en lista:  {len(BRASALAND_SUPPLIERS)}")
    print(f"✅ Insertados:                {inserted}")
    print(f"⏭️  Skipped (duplicados):      {skipped}")
    print(f"❌ Errores:                   {len(errors)}")
    print("=" * 70)

    if errors:
        print()
        print("⚠️  ERRORES DETALLADOS:")
        for err in errors:
            print(f"   - {err['name']}: {err['error']}")
        print()

    # Estado final
    total_in_db = len(suppliers_table.all())
    print()
    print(f"📦 Total proveedores en BD: {total_in_db}")
    print()

    if inserted > 0:
        print("✨ Seeding completado exitosamente")
        return 0
    elif skipped == len(BRASALAND_SUPPLIERS):
        print("ℹ️  Base de datos ya estaba poblada")
        return 0
    else:
        print("⚠️  Seeding completado con errores")
        return 1


def main():
    """Entry point para ejecución directa."""
    try:
        exit_code = seed_suppliers()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n❌ Seeding cancelado por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error fatal: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
