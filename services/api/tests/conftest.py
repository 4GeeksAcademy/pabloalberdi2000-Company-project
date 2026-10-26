"""
Pytest Configuration and Shared Fixtures

Fixtures disponibles:
- test_db: Base de datos temporal para pruebas
- test_client: Cliente HTTP de FastAPI
- test_user: Usuario de prueba con credenciales conocidas
- auth_token: Token JWT válido
- auth_headers: Headers con Authorization Bearer
- expired_token: Token JWT expirado para tests
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from jose import jwt
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.tinydb_database import db, users_table, profiles_table, reset_tokens_table
from app.auth.password import hash_password
from app.auth.jwt import create_access_token, verify_token
from app.config import settings


@pytest.fixture(scope="function")
def test_client():
    """
    Cliente HTTP de prueba para FastAPI.
    Cada test obtiene su propia instancia.
    """
    client = TestClient(app)
    return client


@pytest.fixture(scope="function")
def test_db():
    """
    Base de datos temporal para pruebas.
    Limpia todas las tablas antes de cada test.
    """
    # Limpiar todas las tablas antes del test
    users_table.truncate()
    profiles_table.truncate()
    reset_tokens_table.truncate()

    yield db

    # Limpiar después del test
    users_table.truncate()
    profiles_table.truncate()
    reset_tokens_table.truncate()


@pytest.fixture
def test_user(test_db):
    """
    Usuario de prueba con credenciales conocidas.

    Returns:
        dict: Usuario insertado en DB con:
            - email: "test@brasaland.com"
            - password (plaintext): "testpass123"
            - hashed_password: bcrypt hash
            - role: "user"
            - is_active: True
    """
    user_data = {
        "email": "test@brasaland.com",
        "hashed_password": hash_password("testpass123"),
        "role": "user",
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }

    doc_id = users_table.insert(user_data)
    user = users_table.get(doc_id=doc_id)

    # Agregar plaintext password para tests
    user["_test_password"] = "testpass123"

    return user


@pytest.fixture
def inactive_user(test_db):
    """
    Usuario desactivado para tests de autorización.
    """
    user_data = {
        "email": "inactive@brasaland.com",
        "hashed_password": hash_password("testpass123"),
        "role": "user",
        "is_active": False,
        "created_at": datetime.utcnow().isoformat()
    }

    doc_id = users_table.insert(user_data)
    user = users_table.get(doc_id=doc_id)
    user["_test_password"] = "testpass123"

    return user


@pytest.fixture
def test_user_with_profile(test_db):
    """
    Usuario con perfil completo vinculado.
    """
    # Crear usuario
    user_data = {
        "email": "withprofile@brasaland.com",
        "hashed_password": hash_password("testpass123"),
        "role": "user",
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }
    user_id = users_table.insert(user_data)
    user = users_table.get(doc_id=user_id)

    # Crear perfil vinculado
    profile_data = {
        "user_id": user_id,
        "name": "Test User",
        "phone": "+573001234567",
        "address": "Calle Test 123, Medellín"
    }
    profile_id = profiles_table.insert(profile_data)
    profile = profiles_table.get(doc_id=profile_id)

    user["_test_password"] = "testpass123"
    user["profile"] = profile

    return user


@pytest.fixture
def auth_token(test_user):
    """
    Token JWT válido para el test_user.
    Expira en 24 horas (configuración por defecto).

    Returns:
        str: Token JWT firmado
    """
    return create_access_token(data={"sub": test_user.doc_id})


@pytest.fixture
def auth_headers(auth_token):
    """
    Headers HTTP con Authorization Bearer.

    Returns:
        dict: {"Authorization": "Bearer <token>"}
    """
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def expired_token(test_user):
    """
    Token JWT expirado (hace 25 horas).

    Útil para tests de:
    - TC-ME-004: Token expirado en /auth/me
    - Validación de expiración en dependencies

    Returns:
        str: Token JWT expirado
    """
    # Crear payload con expiración en el pasado
    expire = datetime.utcnow() - timedelta(hours=25)
    payload = {
        "sub": test_user.doc_id,
        "exp": expire
    }

    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token


@pytest.fixture
def malformed_token():
    """
    Token JWT con firma inválida.

    Útil para tests de:
    - TC-ME-005: Token malformado
    - Validación de firma en jwt.py

    Returns:
        str: Token con firma incorrecta
    """
    # Token válido pero firmado con clave diferente
    fake_token = jwt.encode(
        {"sub": 999, "exp": datetime.utcnow() + timedelta(hours=1)},
        "fake-secret-key",
        algorithm=settings.algorithm
    )
    return fake_token


@pytest.fixture
def admin_user(test_db):
    """
    Usuario con rol admin para tests de permisos.
    """
    user_data = {
        "email": "admin@brasaland.com",
        "hashed_password": hash_password("admin123"),
        "role": "admin",
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }

    doc_id = users_table.insert(user_data)
    user = users_table.get(doc_id=doc_id)
    user["_test_password"] = "admin123"

    return user


@pytest.fixture
def multiple_users(test_db):
    """
    Batch de múltiples usuarios para tests de listado.

    Returns:
        list[dict]: Lista de 5 usuarios con diferentes roles
    """
    users = []

    for i in range(5):
        user_data = {
            "email": f"user{i}@brasaland.com",
            "hashed_password": hash_password(f"pass{i}123"),
            "role": "admin" if i == 0 else "user",
            "is_active": i != 4,  # user4 desactivado
            "created_at": datetime.utcnow().isoformat()
        }
        doc_id = users_table.insert(user_data)
        user = users_table.get(doc_id=doc_id)
        user["_test_password"] = f"pass{i}123"
        users.append(user)

    return users


# ============ Markers personalizados ============

def pytest_configure(config):
    """
    Registrar markers custom para pytest.
    """
    config.addinivalue_line(
        "markers", "auth: mark test as authentication test"
    )
    config.addinivalue_line(
        "markers", "users: mark test as user management test"
    )
    config.addinivalue_line(
        "markers", "utils: mark test as utility function test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "critical: mark test as critical business logic test"
    )
