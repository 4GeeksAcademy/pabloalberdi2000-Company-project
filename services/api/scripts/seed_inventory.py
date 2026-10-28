"""
Seed Script for Brasaland Inventory System

Pobla la base de datos de Supabase con ingredientes y órdenes de prueba.

Datos específicos del negocio (cocina a la brasa):
- Ingredientes: Carnes, vegetales, arroz, especias, bebidas
- Entradas: Llegadas de materia prima a diferentes sedes
- Salidas: Uso en cocina, merma

CRÍTICO: Stock resultante = SUM(inbound) - SUM(outbound)
"""

import sys
from pathlib import Path

# Agregar raíz de la app al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from app.database_supabase import engine, init_db
from app.models.inventory import (
    Ingredient,
    InboundOrder,
    OutboundOrder,
    MeasurementUnit,
    WarehouseLocation
)
from datetime import datetime, timedelta


def seed_ingredients(session: Session) -> dict:
    """
    Crear ingredientes de cocina a la brasa de Brasaland.

    Returns:
        dict: {sku: Ingredient} para referenciar en órdenes
    """
    ingredients_data = [
        # Carnes (producto estrella)
        {
            "name": "Carne de res (churrasco)",
            "sku": "CARNE-RES-001",
            "description": "Corte de res para churrasco a la brasa",
            "unit": MeasurementUnit.KG,
            "min_stock": 50.0,
            "reorder_point": 100.0
        },
        {
            "name": "Carne de cerdo (costillas)",
            "sku": "CARNE-CERDO-001",
            "description": "Costillas de cerdo para asar",
            "unit": MeasurementUnit.KG,
            "min_stock": 30.0,
            "reorder_point": 60.0
        },
        {
            "name": "Pollo entero",
            "sku": "POLLO-001",
            "description": "Pollo entero para asar a la brasa",
            "unit": MeasurementUnit.UNIT,
            "min_stock": 100.0,
            "reorder_point": 200.0
        },
        {
            "name": "Chorizo colombiano",
            "sku": "CHORIZO-001",
            "description": "Chorizo artesanal para parrilla",
            "unit": MeasurementUnit.KG,
            "min_stock": 20.0,
            "reorder_point": 40.0
        },

        # Acompañamientos
        {
            "name": "Arroz blanco",
            "sku": "ARROZ-BLANCO-001",
            "description": "Arroz blanco para acompañamiento",
            "unit": MeasurementUnit.KG,
            "min_stock": 100.0,
            "reorder_point": 200.0
        },
        {
            "name": "Frijoles rojos",
            "sku": "FRIJOLES-001",
            "description": "Frijoles rojos secos para bandeja paisa",
            "unit": MeasurementUnit.KG,
            "min_stock": 50.0,
            "reorder_point": 100.0
        },
        {
            "name": "Plátano macho",
            "sku": "PLATANO-001",
            "description": "Plátano macho para patacones",
            "unit": MeasurementUnit.KG,
            "min_stock": 40.0,
            "reorder_point": 80.0
        },
        {
            "name": "Papa criolla",
            "sku": "PAPA-CRIOLLA-001",
            "description": "Papa criolla para asar",
            "unit": MeasurementUnit.KG,
            "min_stock": 60.0,
            "reorder_point": 120.0
        },
        {
            "name": "Yuca",
            "sku": "YUCA-001",
            "description": "Yuca para frita o cocida",
            "unit": MeasurementUnit.KG,
            "min_stock": 50.0,
            "reorder_point": 100.0
        },

        # Vegetales frescos
        {
            "name": "Tomate",
            "sku": "TOMATE-001",
            "description": "Tomate fresco para ensaladas",
            "unit": MeasurementUnit.KG,
            "min_stock": 30.0,
            "reorder_point": 60.0
        },
        {
            "name": "Lechuga",
            "sku": "LECHUGA-001",
            "description": "Lechuga crespa para ensaladas",
            "unit": MeasurementUnit.KG,
            "min_stock": 20.0,
            "reorder_point": 40.0
        },
        {
            "name": "Cebolla blanca",
            "sku": "CEBOLLA-001",
            "description": "Cebolla blanca para guisos y ensaladas",
            "unit": MeasurementUnit.KG,
            "min_stock": 25.0,
            "reorder_point": 50.0
        },

        # Especias y condimentos
        {
            "name": "Sal marina",
            "sku": "SAL-001",
            "description": "Sal marina para sazonar carnes",
            "unit": MeasurementUnit.KG,
            "min_stock": 10.0,
            "reorder_point": 20.0
        },
        {
            "name": "Limón Tahití",
            "sku": "LIMON-001",
            "description": "Limón para jugos y aderezos",
            "unit": MeasurementUnit.KG,
            "min_stock": 15.0,
            "reorder_point": 30.0
        },
        {
            "name": "Aceite vegetal",
            "sku": "ACEITE-001",
            "description": "Aceite vegetal para cocina",
            "unit": MeasurementUnit.L,
            "min_stock": 20.0,
            "reorder_point": 40.0
        },

        # Bebidas
        {
            "name": "Agua embotellada 600ml",
            "sku": "AGUA-600ML-001",
            "description": "Agua purificada embotellada",
            "unit": MeasurementUnit.UNIT,
            "min_stock": 500.0,
            "reorder_point": 1000.0
        },
        {
            "name": "Coca-Cola 350ml",
            "sku": "COCA-COLA-001",
            "description": "Refresco de cola",
            "unit": MeasurementUnit.UNIT,
            "min_stock": 300.0,
            "reorder_point": 600.0
        },
    ]

    ingredients_dict = {}

    for data in ingredients_data:
        ingredient = Ingredient(**data)
        session.add(ingredient)
        session.flush()  # Get ID without committing
        ingredients_dict[data["sku"]] = ingredient
        print(f"  ✅ Ingrediente: {ingredient.name} (SKU: {ingredient.sku})")

    return ingredients_dict


def seed_inbound_orders(session: Session, ingredients: dict) -> None:
    """
    Crear órdenes de entrada de stock (llegadas de materia prima).

    Simula 3 días de llegadas en diferentes sedes.
    """
    # user_uuid de ejemplo (doc_id del admin de TinyDB = 1)
    admin_uuid = "1"

    orders_data = [
        # Día 1 - Llegada grande a almacén central
        {
            "ingredient_sku": "CARNE-RES-001",
            "quantity": 200.0,
            "warehouse": WarehouseLocation.CENTRAL_WAREHOUSE,
            "user_uuid": admin_uuid,
            "notes": "Proveedor principal - Carne Argentina Premium",
            "created_at": datetime.utcnow() - timedelta(days=3)
        },
        {
            "ingredient_sku": "CARNE-CERDO-001",
            "quantity": 150.0,
            "warehouse": WarehouseLocation.CENTRAL_WAREHOUSE,
            "user_uuid": admin_uuid,
            "notes": "Proveedor local - Cerdo fresco",
            "created_at": datetime.utcnow() - timedelta(days=3)
        },
        {
            "ingredient_sku": "POLLO-001",
            "quantity": 300.0,
            "warehouse": WarehouseLocation.CENTRAL_WAREHOUSE,
            "user_uuid": admin_uuid,
            "notes": "Pollos de granja orgánica",
            "created_at": datetime.utcnow() - timedelta(days=3)
        },
        {
            "ingredient_sku": "ARROZ-BLANCO-001",
            "quantity": 500.0,
            "warehouse": WarehouseLocation.CENTRAL_WAREHOUSE,
            "user_uuid": admin_uuid,
            "notes": "Arroz Diana - 10 bultos de 50kg",
            "created_at": datetime.utcnow() - timedelta(days=3)
        },

        # Día 2 - Distribución a sedes Colombia
        {
            "ingredient_sku": "CARNE-RES-001",
            "quantity": 50.0,
            "warehouse": WarehouseLocation.MEDELLIN_POBLADO,
            "user_uuid": admin_uuid,
            "notes": "Redistribución desde almacén central",
            "created_at": datetime.utcnow() - timedelta(days=2)
        },
        {
            "ingredient_sku": "POLLO-001",
            "quantity": 80.0,
            "warehouse": WarehouseLocation.MEDELLIN_POBLADO,
            "user_uuid": admin_uuid,
            "notes": "Redistribución desde almacén central",
            "created_at": datetime.utcnow() - timedelta(days=2)
        },
        {
            "ingredient_sku": "CARNE-RES-001",
            "quantity": 40.0,
            "warehouse": WarehouseLocation.BOGOTA_ZONA_ROSA,
            "user_uuid": admin_uuid,
            "notes": "Redistribución desde almacén central",
            "created_at": datetime.utcnow() - timedelta(days=2)
        },

        # Día 3 - Distribución a sedes Florida
        {
            "ingredient_sku": "CARNE-RES-001",
            "quantity": 60.0,
            "warehouse": WarehouseLocation.MIAMI_BEACH,
            "user_uuid": admin_uuid,
            "notes": "Importación desde almacén central",
            "created_at": datetime.utcnow() - timedelta(days=1)
        },
        {
            "ingredient_sku": "POLLO-001",
            "quantity": 100.0,
            "warehouse": WarehouseLocation.MIAMI_BEACH,
            "user_uuid": admin_uuid,
            "notes": "Proveedor local Florida - US Foods",
            "created_at": datetime.utcnow() - timedelta(days=1)
        },

        # Ingredientes adicionales
        {
            "ingredient_sku": "AGUA-600ML-001",
            "quantity": 2000.0,
            "warehouse": WarehouseLocation.CENTRAL_WAREHOUSE,
            "user_uuid": admin_uuid,
            "notes": "Pedido mensual - Agua Cristal",
            "created_at": datetime.utcnow() - timedelta(days=3)
        },
        {
            "ingredient_sku": "COCA-COLA-001",
            "quantity": 1500.0,
            "warehouse": WarehouseLocation.CENTRAL_WAREHOUSE,
            "user_uuid": admin_uuid,
            "notes": "Pedido mensual - Coca-Cola",
            "created_at": datetime.utcnow() - timedelta(days=3)
        },
    ]

    for data in orders_data:
        ingredient = ingredients[data.pop("ingredient_sku")]
        order = InboundOrder(
            ingredient_id=ingredient.id,
            **data
        )
        session.add(order)
        print(f"  ✅ Entrada: {order.quantity} {ingredient.unit.value} de {ingredient.name} en {order.warehouse.value}")


def seed_outbound_orders(session: Session, ingredients: dict) -> None:
    """
    Crear órdenes de salida de stock (uso en cocina).

    Simula consumo diario en diferentes sedes.
    """
    admin_uuid = "1"

    orders_data = [
        # Consumo en Medellín Poblado
        {
            "ingredient_sku": "CARNE-RES-001",
            "quantity": 25.0,
            "warehouse": WarehouseLocation.MEDELLIN_POBLADO,
            "user_uuid": admin_uuid,
            "reason": "Uso en cocina - Servicio del día",
            "created_at": datetime.utcnow() - timedelta(hours=12)
        },
        {
            "ingredient_sku": "POLLO-001",
            "quantity": 40.0,
            "warehouse": WarehouseLocation.MEDELLIN_POBLADO,
            "user_uuid": admin_uuid,
            "reason": "Uso en cocina - Servicio del día",
            "created_at": datetime.utcnow() - timedelta(hours=12)
        },

        # Consumo en Bogotá Zona Rosa
        {
            "ingredient_sku": "CARNE-RES-001",
            "quantity": 20.0,
            "warehouse": WarehouseLocation.BOGOTA_ZONA_ROSA,
            "user_uuid": admin_uuid,
            "reason": "Uso en cocina - Servicio del día",
            "created_at": datetime.utcnow() - timedelta(hours=10)
        },

        # Consumo en Miami Beach
        {
            "ingredient_sku": "CARNE-RES-001",
            "quantity": 30.0,
            "warehouse": WarehouseLocation.MIAMI_BEACH,
            "user_uuid": admin_uuid,
            "reason": "Uso en cocina - Servicio del día",
            "created_at": datetime.utcnow() - timedelta(hours=8)
        },
        {
            "ingredient_sku": "POLLO-001",
            "quantity": 50.0,
            "warehouse": WarehouseLocation.MIAMI_BEACH,
            "user_uuid": admin_uuid,
            "reason": "Uso en cocina - Servicio del día",
            "created_at": datetime.utcnow() - timedelta(hours=8)
        },

        # Merma
        {
            "ingredient_sku": "CARNE-RES-001",
            "quantity": 2.0,
            "warehouse": WarehouseLocation.CENTRAL_WAREHOUSE,
            "user_uuid": admin_uuid,
            "reason": "Merma por calidad - Lote con defecto",
            "created_at": datetime.utcnow() - timedelta(days=1)
        },
    ]

    for data in orders_data:
        ingredient = ingredients[data.pop("ingredient_sku")]
        order = OutboundOrder(
            ingredient_id=ingredient.id,
            **data
        )
        session.add(order)
        print(f"  ✅ Salida: {order.quantity} {ingredient.unit.value} de {ingredient.name} en {order.warehouse.value}")


def main():
    """
    Script principal de seeding.

    Orden:
    1. Inicializar tablas
    2. Crear ingredientes
    3. Crear órdenes de entrada
    4. Crear órdenes de salida

    Stock final = SUM(inbound) - SUM(outbound)
    """
    print("\n" + "="*60)
    print("🌱 SEEDING BRASALAND INVENTORY DATABASE")
    print("="*60 + "\n")

    # Inicializar tablas
    print("📋 Creando tablas en Supabase...")
    init_db()
    print("  ✅ Tablas creadas\n")

    # Crear sesión
    session = Session(engine)

    try:
        # Verificar si ya hay datos
        existing = session.exec(select(Ingredient)).first()
        if existing:
            print("⚠️  La base de datos ya contiene datos.")
            response = input("¿Desea limpiar y re-seed? (yes/no): ")
            if response.lower() != "yes":
                print("❌ Seed cancelado")
                return

            # Limpiar tablas
            print("\n🧹 Limpiando tablas existentes...")
            session.exec("DELETE FROM outbound_orders")
            session.exec("DELETE FROM inbound_orders")
            session.exec("DELETE FROM ingredients")
            session.commit()
            print("  ✅ Tablas limpiadas\n")

        # Seed ingredientes
        print("🥩 Creando ingredientes...")
        ingredients = seed_ingredients(session)
        session.commit()
        print(f"\n  ✅ {len(ingredients)} ingredientes creados\n")

        # Seed órdenes de entrada
        print("📦 Creando órdenes de entrada (inbound)...")
        seed_inbound_orders(session, ingredients)
        session.commit()
        print("\n  ✅ Órdenes de entrada creadas\n")

        # Seed órdenes de salida
        print("🍽️  Creando órdenes de salida (outbound)...")
        seed_outbound_orders(session, ingredients)
        session.commit()
        print("\n  ✅ Órdenes de salida creadas\n")

        print("="*60)
        print("✅ SEED COMPLETADO EXITOSAMENTE")
        print("="*60)
        print("\n📊 Resumen:")
        print(f"  • Ingredientes: {len(ingredients)}")
        print(f"  • Órdenes de entrada: {session.exec(select(InboundOrder)).all().__len__()}")
        print(f"  • Órdenes de salida: {session.exec(select(OutboundOrder)).all().__len__()}")
        print("\n💡 Stock actual = SUM(inbound) - SUM(outbound)")
        print("\n🚀 Accede a la API en: http://localhost:8000/inventory/ingredients")
        print("📖 Documentación: http://localhost:8000/docs\n")

    except Exception as e:
        session.rollback()
        print(f"\n❌ ERROR durante seed: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
