"""
Reset Token Management for Password Recovery (Hito 6 - AUTH-03)

Tokens de reset son JWT con:
- Secret key DIFERENTE al de access tokens (reset_token_secret_key)
- Expiración corta (30 min por defecto)
- JTI único para invalidación (prevenir reuso)
"""

from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import uuid
from ..config import settings
from ..tinydb_database import is_reset_token_used, mark_reset_token_as_used


def create_reset_token(user_id: int) -> str:
    """
    Crear token de reset de contraseña.

    Args:
        user_id: ID de TinyDB del usuario

    Returns:
        Token JWT firmado con secret diferente al de access tokens
    """
    jti = str(uuid.uuid4())  # ID único para este token

    to_encode = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=settings.reset_token_expire_minutes),
        "type": "password_reset",
        "jti": jti
    }

    token = jwt.encode(
        to_encode,
        settings.reset_token_secret_key,  # ⚠️ SECRET DIFERENTE
        algorithm=settings.algorithm
    )
    return token


def verify_reset_token(token: str) -> Optional[dict]:
    """
    Verificar y decodificar reset token.

    Valida:
    - Firma válida con reset_token_secret_key
    - Token no expirado
    - Tipo correcto (password_reset)
    - Token no usado previamente (check en TinyDB)

    Args:
        token: Token JWT a verificar

    Returns:
        Payload del token si válido y no usado
        None si inválido, expirado, tipo incorrecto o ya usado
    """
    try:
        payload = jwt.decode(
            token,
            settings.reset_token_secret_key,  # ⚠️ SECRET DIFERENTE
            algorithms=[settings.algorithm]
        )

        # Verificar tipo
        if payload.get("type") != "password_reset":
            return None

        # Verificar si ya fue usado (blacklist en TinyDB)
        jti = payload.get("jti")
        if not jti or is_reset_token_used(jti):
            return None

        return payload

    except JWTError:
        return None


def invalidate_reset_token(jti: str, user_id: int):
    """
    Invalidar token después de uso exitoso.

    Agrega el JTI a la blacklist en TinyDB para prevenir reuso.

    Args:
        jti: ID único del token
        user_id: ID del usuario
    """
    mark_reset_token_as_used(jti, user_id)
