"""
SQLite Database for Inventory System (Alternative to Supabase)

This is a local SQLite alternative when Supabase is not configured.
Used for development and testing without external dependencies.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
import os

# SQLite database for inventory
INVENTORY_DB_PATH = os.getenv("INVENTORY_DB_PATH", "./brasaland_inventory.db")
INVENTORY_DATABASE_URL = f"sqlite:///{INVENTORY_DB_PATH}"

# Create engine
inventory_engine = create_engine(
    INVENTORY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# Session maker
InventorySessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=inventory_engine
)


def get_inventory_db():
    """Dependency for inventory database sessions"""
    db = InventorySessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_inventory_db():
    """Initialize inventory tables"""
    from app.models.inventory import (
        Ingredient,
        InboundOrder,
        OutboundOrder,
        WarehouseLocation
    )

    SQLModel.metadata.create_all(inventory_engine)
    print("✅ Inventory database tables created (SQLite)")


def check_inventory_db_connection() -> bool:
    """Check if inventory database is accessible"""
    try:
        with inventory_engine.connect() as conn:
            return True
    except Exception as e:
        print(f"❌ Inventory DB connection failed: {e}")
        return False
