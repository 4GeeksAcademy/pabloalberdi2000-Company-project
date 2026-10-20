"""
TinyDB Database Configuration for User Authentication

Este módulo configura TinyDB exclusivamente para User y Profile.
Candidate y Note siguen usando SQLAlchemy.
"""

from tinydb import TinyDB, Query
from typing import Optional
import os

# Archivo de BD en la raíz del proyecto API
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "users_db.json")

# Instancia global de TinyDB
db = TinyDB(DB_PATH)

# Tablas
users_table = db.table('users')
profiles_table = db.table('profiles')

# Query helpers
User = Query()
Profile = Query()


def get_tinydb():
    """
    Dependency para inyectar TinyDB en routers.
    Similar a get_db() pero para TinyDB.
    """
    return db


def get_user_by_email(email: str) -> Optional[dict]:
    """Helper: Buscar usuario por email"""
    result = users_table.search(User.email == email)
    return result[0] if result else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Helper: Buscar usuario por ID de TinyDB"""
    result = users_table.get(doc_id=user_id)
    return result


def get_profile_by_user_id(user_id: int) -> Optional[dict]:
    """Helper: Buscar perfil por user_id"""
    result = profiles_table.search(Profile.user_id == user_id)
    return result[0] if result else None
