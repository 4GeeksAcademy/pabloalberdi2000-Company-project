"""
Seed Script for Brasaland Inventory System (SQLite version)

Pobla la base de datos local de SQLite con ingredientes y órdenes de prueba.

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
from app.database_inventory_sqlite import inventory_engine, init_inventory_db
from app.models.inventory import (
    Ingredient,
    InboundOrder,
    OutboundOrder,
    MeasurementUnit,
    WarehouseLocation
)
from datetime import datetime, timedelta
import random

# Initialize database
init_inventory_db()


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
            "unit": "kg",
            "min_stock": 50.0,
            "reorder_point": 100.0
        },
        {
            "name": "Carne de cerdo (costillas)",
            "sku": "CARNE-CERDO-001",
            "description": "Costillas de cerdo para asar",
            "unit": "kg",
            "min_stock": 30.0,
            "reorder_point": 60.0
        },
        {
            "name": "Pollo entero",
            "sku": "POLLO-001",
            "description": "Pollo entero para asar a la brasa",
            "unit": "unit",
            "min_stock": 100.0,
            "reorder_point": 200.0
        },
        {
            "name": "Chorizo colombiano",
            "sku": "CHORIZO-001",
            "description": "Chorizo artesanal para parrilla",
            "unit": "kg",
            "min_stock": 20.0,
            "reorder_point": 40.0
        },

        # Acompañamientos
        {
            "name": "Arroz blanco",
            "sku": "ARROZ-BLANCO-001",
            "description": "Arroz blanco para acompañamiento",
            "unit": "kg",
            "min_stock": 100.0,
            "reorder_point": 200.0
        },
        {
            "name": "Papas criollas",
            "sku": "PAPA-CRIOLLA-001",
            "description": "Papas criollas colombianas",
            "unit": "kg",
            "min_stock": 50.0,
            "reorder_point": 100.0
        },
        {
            "name": "Plátano maduro",
            "sku": "PLATANO-MADURO-001",
            "description": "Plátano para asar",
            "unit": "unit",
            "min_stock": 200.0,
            "reorder_point": 400.0
        },

        # Salsas y condimentos
        {
            "name": "Chimichurri argentino",
            "sku": "CHIMICHURRI-001",
            "description": "Salsa chimichurri para carnes",
            "unit": "l",
            "min_stock": 10.0,
            "reorder_point": 20.0
        },
        {
            "name": "Ají picante",
            "sku": "AJI-PICANTE-001",
            "description": "Ají picante colombiano",
            "unit": "l",
            "min_stock": 5.0,
            "reorder_point": 10.0
        },

        # Bebidas
        {
            "name": "Cerveza nacional",
            "sku": "CERVEZA-NACIONAL-001",
            "description": "Cerveza colombiana (botella 330ml)",
            "unit": "unit",
            "min_stock": 500.0,
            "reorder_point": 1000.0
        },
        {
            "name": "Gaseosa Colombiana",
            "sku": "GASEOSA-001",
            "description": "Gaseosa colombiana (botella 400ml)",
            "unit": "unit",
            "min_stock": 300.0,
            "reorder_point": 600.0
        },
    ]

    print(f"\n📦 Creating {len(ingredients_data)} ingredients...")
    ingredients_map = {}

    for data in ingredients_data:
        existing = session.exec(
            select(Ingredient).where(Ingredient.sku == data["sku"])
        ).first()

        if existing:
            print(f"   ⏭️  Skipped: {data['sku']} (already exists)")
            ingredients_map[data["sku"]] = existing
            continue

        ingredient = Ingredient(**data)
        session.add(ingredient)
        ingredients_map[data["sku"]] = ingredient
        print(f"   ✅ Created: {data['sku']}")

    session.commit()
    return ingredients_map


def seed_inbound_orders(session: Session, ingredients: dict, count: int = 20):
    """
    Crear órdenes de entrada (llegada de materia prima).

    Args:
        session: SQLModel session
        ingredients: Mapa de SKU -> Ingredient
        count: Número de órdenes de entrada a crear
    """
    warehouses = list(WarehouseLocation)
    print(f"\n📥 Creating {count} inbound orders...")

    created = 0
    for i in range(count):
        # Fecha aleatoria en los últimos 60 días
        days_ago = random.randint(1, 60)
        received_date = datetime.utcnow() - timedelta(days=days_ago)

        # Seleccionar ingrediente aleatorio
        sku = random.choice(list(ingredients.keys()))
        ingredient = ingredients[sku]

        # Cantidad basada en reorder_point
        if ingredient.unit == "kg":
            quantity = round(random.uniform(50, 200), 2)
            unit_price = round(random.uniform(10, 50), 2)
        elif ingredient.unit == "l":
            quantity = round(random.uniform(10, 50), 2)
            unit_price = round(random.uniform(5, 20), 2)
        else:  # unit
            quantity = random.randint(100, 500)
            unit_price = round(random.uniform(1, 10), 2)

        order = InboundOrder(
            ingredient_id=ingredient.id,
            quantity=quantity,
            warehouse=random.choice(warehouses),
            user_uuid="admin-user-001"  # Admin user that created the order
        )

        session.add(order)
        created += 1

    session.commit()
    print(f"   ✅ Created: {created} inbound orders")


def seed_outbound_orders(session: Session, ingredients: dict, count: int = 30):
    """
    Crear órdenes de salida (uso en cocina, merma).

    Args:
        session: SQLModel session
        ingredients: Mapa de SKU -> Ingredient
        count: Número de órdenes de salida a crear
    """
    warehouses = list(WarehouseLocation)
    reasons = [
        "Consumo en cocina - servicio normal",
        "Preparación de platos del día",
        "Merma por vencimiento",
        "Rotura de envase",
        "Uso en evento especial"
    ]

    print(f"\n📤 Creating {count} outbound orders...")

    created = 0
    for i in range(count):
        # Fecha aleatoria en los últimos 45 días
        days_ago = random.randint(1, 45)
        used_date = datetime.utcnow() - timedelta(days=days_ago)

        # Seleccionar ingrediente aleatorio
        sku = random.choice(list(ingredients.keys()))
        ingredient = ingredients[sku]

        # Cantidad menor que inbound (consumo diario)
        if ingredient.unit == "kg":
            quantity = round(random.uniform(10, 80), 2)
        elif ingredient.unit == "l":
            quantity = round(random.uniform(2, 20), 2)
        else:  # unit
            quantity = random.randint(20, 150)

        order = OutboundOrder(
            ingredient_id=ingredient.id,
            quantity=quantity,
            warehouse=random.choice(warehouses),
            user_uuid="admin-user-001",
            reason=random.choice(reasons)
        )

        session.add(order)
        created += 1

    session.commit()
    print(f"   ✅ Created: {created} outbound orders")


def print_inventory_summary(session: Session):
    """Imprimir resumen del inventario"""
    ingredients = session.exec(select(Ingredient)).all()
    total_inbound = session.exec(select(InboundOrder)).all()
    total_outbound = session.exec(select(OutboundOrder)).all()

    print("\n" + "="*70)
    print("📊 INVENTORY SUMMARY")
    print("="*70)
    print(f"🥩 Ingredients:     {len(ingredients)}")
    print(f"📥 Inbound Orders:  {len(total_inbound)}")
    print(f"📤 Outbound Orders: {len(total_outbound)}")
    print("\n🔢 Stock Calculation (first 5 ingredients):")
    print("-" * 70)

    for ing in ingredients[:5]:
        inbound_qty = sum(
            o.quantity for o in session.exec(
                select(InboundOrder).where(InboundOrder.ingredient_id == ing.id)
            ).all()
        )
        outbound_qty = sum(
            o.quantity for o in session.exec(
                select(OutboundOrder).where(OutboundOrder.ingredient_id == ing.id)
            ).all()
        )
        stock = inbound_qty - outbound_qty

        status = "✅" if stock >= ing.min_stock else "⚠️ LOW"
        print(f"   {ing.sku:20} | Stock: {stock:8.2f} {ing.unit.value:6} | {status}")

    print("="*70)


def main():
    """Seed completo del inventario"""
    print("\n🌱 Seeding Brasaland Inventory (SQLite)...\n")

    with Session(inventory_engine) as session:
        # 1. Crear ingredientes
        ingredients = seed_ingredients(session)

        # 2. Crear órdenes de entrada
        seed_inbound_orders(session, ingredients, count=25)

        # 3. Crear órdenes de salida
        seed_outbound_orders(session, ingredients, count=40)

        # 4. Resumen
        print_inventory_summary(session)

    print("\n✅ Inventory seed completed!")


if __name__ == "__main__":
    main()
