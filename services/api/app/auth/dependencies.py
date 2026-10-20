"""
Authentication Dependencies

Dependencies de FastAPI para proteger endpoints.
Uso: agregar como parámetro en funciones de router con Depends()
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Dict
from ..tinydb_database import get_user_by_id
from .jwt import verify_token

# OAuth2 scheme - tokenUrl es el endpoint de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    """
    Dependency: Extraer y validar token JWT, retornar usuario actual.

    Lanza HTTPException 401 si:
    - Token inválido o malformado
    - Token expirado
    - Usuario no existe en BD

    Returns:
        Dict con datos del usuario (incluye doc_id de TinyDB)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verificar token
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    # Extraer user_id del payload
    user_id: int = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Buscar usuario en TinyDB
    user = get_user_by_id(user_id)
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    Dependency: Usuario activo (is_active=True).

    Lanza HTTPException 400 si usuario está desactivado.

    Returns:
        Dict con datos del usuario activo
    """
    if not current_user.get("is_active", False):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_admin(current_user: Dict = Depends(get_current_active_user)) -> Dict:
    """
    Dependency: Solo usuarios con role='admin'.

    Lanza HTTPException 403 si usuario no es admin.
    Usar para endpoints que solo admins pueden acceder.

    Returns:
        Dict con datos del usuario admin
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
    return current_user


def require_manager_or_admin(current_user: Dict = Depends(get_current_active_user)) -> Dict:
    """
    Dependency: Usuarios con role='manager' o 'admin'.

    Lanza HTTPException 403 si usuario no tiene permisos suficientes.
    Usar para endpoints que requieren permisos elevados pero no necesariamente admin.

    Returns:
        Dict con datos del usuario manager/admin
    """
    role = current_user.get("role")
    if role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Manager or Admin role required."
        )
    return current_user
