"""
TinyDB Database Configuration for User Authentication

Este módulo configura TinyDB exclusivamente para User y Profile.
Candidate y Note siguen usando SQLAlchemy.
"""

from tinydb import TinyDB, Query
from typing import Optional, List
import os

# Archivo de BD en la raíz del proyecto API
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "users_db.json")

# Instancia global de TinyDB
db = TinyDB(DB_PATH)

# Tablas
users_table = db.table('users')
profiles_table = db.table('profiles')
reset_tokens_table = db.table('reset_tokens')  # Hito 6 - AUTH-03
incidents_table = db.table('incidents')  # Fase 4 - Incident Management

# Query helpers
User = Query()
Profile = Query()
ResetToken = Query()  # Hito 6 - AUTH-03
Incident = Query()  # Fase 4 - Incident Management


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


# ============ INCIDENTS HELPERS (Fase 4 - Incident Management) ============

def get_incident_by_id(incident_id: str) -> Optional[dict]:
    """
    Buscar incidencia por UUID.

    Args:
        incident_id: UUID de la incidencia

    Returns:
        Documento de incidencia o None si no existe
    """
    result = incidents_table.search(Incident.id == incident_id)
    return result[0] if result else None


def get_incident_by_legacy_id(legacy_id: str) -> Optional[dict]:
    """
    Buscar incidencia por ID del CSV histórico (idempotencia en seeding).

    Args:
        legacy_id: ID original del CSV (e.g. "INC001")

    Returns:
        Documento de incidencia o None si no existe
    """
    result = incidents_table.search(Incident.legacy_id == legacy_id)
    return result[0] if result else None


def create_incident(incident_data: dict) -> dict:
    """
    Insertar nueva incidencia.

    Args:
        incident_data: Diccionario con datos de la incidencia

    Returns:
        Documento insertado con TinyDB doc_id
    """
    doc_id = incidents_table.insert(incident_data)
    return incidents_table.get(doc_id=doc_id)


def update_incident(incident_id: str, update_data: dict) -> Optional[dict]:
    """
    Actualizar incidencia por UUID.

    Args:
        incident_id: UUID de la incidencia
        update_data: Campos a actualizar

    Returns:
        Documento actualizado o None si no existe
    """
    incidents_table.update(update_data, Incident.id == incident_id)
    return get_incident_by_id(incident_id)


def list_incidents(filters: dict = None, limit: int = 100, offset: int = 0) -> List[dict]:
    """
    Listar incidencias con filtros opcionales y paginación.

    Args:
        filters: Diccionario con filtros (status, origin, branch, category)
        limit: Máximo de resultados (default 100)
        offset: Offset para paginación (default 0)

    Returns:
        Lista de documentos de incidencias
    """
    if filters:
        # Construir query compuesta con AND lógico
        query = None
        for key, value in filters.items():
            condition = getattr(Incident, key) == value
            query = condition if query is None else query & condition
        results = incidents_table.search(query)
    else:
        results = incidents_table.all()

    # Aplicar paginación
    return results[offset:offset + limit]


def count_incidents(filters: dict = None) -> int:
    """
    Contar incidencias con filtros opcionales.

    Args:
        filters: Diccionario con filtros (status, origin, branch, category)

    Returns:
        Número total de incidencias que cumplen los filtros
    """
    if filters:
        query = None
        for key, value in filters.items():
            condition = getattr(Incident, key) == value
            query = condition if query is None else query & condition
        return len(incidents_table.search(query))
    return len(incidents_table.all())
