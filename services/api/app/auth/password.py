"""
Password Hashing

Funciones para hashear y verificar contraseñas con bcrypt.
CRÍTICO: Nunca almacenar contraseñas en texto plano.
"""

from passlib.hash import bcrypt


def hash_password(password: str) -> str:
    """
    Hashear contraseña con bcrypt.

    Args:
        password: Contraseña en texto plano

    Returns:
        Hash de la contraseña
    """
    return bcrypt.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verificar contraseña contra hash.

    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Hash almacenado en BD

    Returns:
        True si la contraseña coincide, False si no
    """
    return bcrypt.verify(plain_password, hashed_password)
