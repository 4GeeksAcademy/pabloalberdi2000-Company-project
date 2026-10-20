"""
JWT Token Management

Funciones para crear y verificar tokens JWT.
"""

from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from ..config import settings


def create_access_token(data: dict) -> str:
    """
    Crear JWT con expiración configurada.

    Args:
        data: Dict con datos a codificar en el token (debe incluir 'sub' con user_id)

    Returns:
        Token JWT firmado
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    Decodificar y validar JWT.

    Args:
        token: Token JWT a verificar

    Returns:
        Payload del token si es válido, None si es inválido o expiró
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None
