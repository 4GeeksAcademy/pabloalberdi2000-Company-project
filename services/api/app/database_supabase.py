"""
Supabase Database Configuration for Inventory System

Arquitectura de doble base de datos:
1. TinyDB (tinydb_database.py): Usuarios y autenticación
2. Supabase/PostgreSQL (este archivo): Datos de negocio (inventario)

Reglas de Negocio Críticas:
- Stock NUNCA es editable directamente, siempre es calculado
- Fórmula: stock = SUM(inbound.quantity) - SUM(outbound.quantity)
- No se replica users en Supabase, solo se referencia user_uuid como string
"""

from sqlmodel import SQLModel, create_engine, Session, text
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

# ============ SUPABASE / POSTGRESQL CONNECTION ============

DATABASE_URL = os.getenv("SUPABASE_DATABASE_URL", "")

# Engine para Supabase/PostgreSQL (datos de negocio)
# Solo se crea si la URL está configurada
engine = None
if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Set True para debug SQL queries
        pool_pre_ping=True,  # Verificar conexión antes de usar
    )


def init_db() -> None:
    """
    Inicializar tablas de inventario en Supabase.
    Llamar al arrancar la aplicación en main.py.

    IMPORTANTE: No toca TinyDB (users, auth).
    """
    if engine is None:
        print("⚠️  Supabase not configured, skipping inventory DB init")
        return
    SQLModel.metadata.create_all(engine)


def get_inventory_db() -> Generator[Session, None, None]:
    """
    Dependency para inyectar sesión de Supabase en routers de inventario.

    Uso en router:
        def endpoint(db: Session = Depends(get_inventory_db)):
            ...

    Gestiona automáticamente:
    - Apertura de sesión por request
    - Commit en caso de éxito
    - Rollback en caso de excepción
    - Cierre de sesión al finalizar
    """
    if engine is None:
        raise RuntimeError("Supabase DB not configured. Set SUPABASE_DATABASE_URL env var.")

    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ============ HEALTH CHECK ============

def check_db_connection() -> bool:
    """
    Verificar conectividad con Supabase.

    Returns:
        bool: True si conexión exitosa, False si falla
    """
    if engine is None:
        print("⚠️  Supabase not configured")
        return False

    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {str(e)}")
        return False
