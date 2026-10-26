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
reset_tokens_table = db.table('reset_tokens')  # Hito 6 - AUTH-03

# Query helpers
User = Query()
Profile = Query()
ResetToken = Query()  # Hito 6 - AUTH-03


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


# ============ RESET TOKENS HELPERS (Hito 6 - AUTH-03) ============

def is_reset_token_used(jti: str) -> bool:
    """
    Verifica si un reset token ya fue usado.

    Args:
        jti: ID único del token (JWT ID)

    Returns:
        True si el token ya fue usado, False en caso contrario
    """
    result = reset_tokens_table.search(ResetToken.jti == jti)
    return len(result) > 0


def mark_reset_token_as_used(jti: str, user_id: int):
    """
    Marca un reset token como usado (invalidado).

    Args:
        jti: ID único del token
        user_id: ID del usuario que usó el token
    """
    from datetime import datetime

    reset_tokens_table.insert({
        "jti": jti,
        "user_id": user_id,
        "used_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat()
    })
