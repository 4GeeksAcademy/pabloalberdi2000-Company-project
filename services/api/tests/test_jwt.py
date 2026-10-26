"""
Tests for JWT Utilities (app/auth/jwt.py)

Casos críticos:
- TC-JWT-001: Crear token válido
- TC-JWT-002: Decodificar token válido
- TC-JWT-003: Token recién expirado
- TC-JWT-004: Token con firma inválida
- TC-JWT-005: Token sin claim 'sub'

Prioridad: 🔴 CRÍTICO (Cobertura objetivo: 100%)
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt

from app.auth.jwt import create_access_token, verify_token
from app.config import settings


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.critical
class TestJWTCreation:
    """Tests de creación de tokens JWT"""

    def test_create_token_with_user_id(self):
        """
        TC-JWT-001: Crear token válido con user_id

        Given: User ID válido
        When: create_access_token({"sub": user_id})
        Then:
          - Token JWT generado
          - Decodificación exitosa
          - Claim 'sub' contiene user_id
          - Claim 'exp' es tiempo futuro (24h)
        """
        user_id = "123"  # JWT spec requires sub to be string

        # Crear token
        token = create_access_token(data={"sub": user_id})

        # Verificar que es string no vacío
        assert isinstance(token, str)
        assert len(token) > 50

        # Decodificar sin validar expiración
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        # Verificar claims
        assert "sub" in payload
        assert payload["sub"] == user_id
        assert "exp" in payload

        # Verificar que expira en el futuro
        exp_timestamp = payload["exp"]
        now_timestamp = datetime.utcnow().timestamp()
        assert exp_timestamp > now_timestamp

        # Verificar que expira en ~24 horas
        time_until_expiry = exp_timestamp - now_timestamp
        expected_expiry = settings.access_token_expire_minutes * 60
        assert abs(time_until_expiry - expected_expiry) < 60  # Margen de 1 minuto

    def test_create_token_with_string_user_id(self):
        """
        TC-JWT-001b: Crear token con user_id como string

        TinyDB usa doc_id como int, pero algunos sistemas usan UUID.
        Verificar que funciona con ambos tipos.
        """
        user_id = "user-uuid-12345"

        token = create_access_token(data={"sub": user_id})
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        assert payload["sub"] == user_id

    def test_create_token_with_additional_claims(self):
        """
        TC-JWT-001c: Crear token con claims adicionales

        Verificar que se pueden agregar claims extra (role, permissions).
        """
        data = {
            "sub": "123",
            "role": "admin",
            "permissions": ["read", "write"]
        }

        token = create_access_token(data=data)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        assert payload["sub"] == 123
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.critical
class TestJWTDecoding:
    """Tests de decodificación de tokens JWT"""

    def test_decode_valid_token(self):
        """
        TC-JWT-002: Decodificar token válido

        Given: Token generado hace 1 hora
        When: verify_token(token)
        Then: Payload extraído correctamente
        """
        user_id = "456"  # JWT spec requires sub to be string
        token = create_access_token(data={"sub": user_id})

        # Decodificar con función de la app
        payload = verify_token(token)

        # Verificar payload
        assert payload is not None
        assert payload["sub"] == user_id
        assert "exp" in payload

    def test_decode_token_with_additional_claims(self):
        """
        TC-JWT-002b: Decodificar token con claims adicionales
        """
        data = {"sub": "789", "role": "user", "email": "test@example.com"}
        token = create_access_token(data=data)

        payload = verify_token(token)

        assert payload["sub"] == 789
        assert payload["role"] == "user"
        assert payload["email"] == "test@example.com"


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.critical
class TestJWTExpiration:
    """Tests de expiración de tokens"""

    def test_token_expires_after_24_hours(self):
        """
        TC-JWT-003: Token recién expirado (24h + 1s)

        Given: Token generado hace exactamente 24h 1s
        When: Decodificación
        Then: Error de expiración
        """
        # Crear token con expiración en el pasado
        user_id = "100"  # JWT spec requires sub to be string
        expire = datetime.utcnow() - timedelta(hours=24, seconds=1)
        payload = {
            "sub": user_id,
            "exp": expire
        }

        expired_token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

        # Intentar decodificar con validación de expiración
        result = verify_token(expired_token)

        # verify_token debe retornar None en token expirado
        assert result is None

    def test_token_valid_before_expiration(self):
        """
        TC-JWT-003b: Token válido antes de expirar

        Given: Token generado hace 23 horas
        When: Decodificación
        Then: Payload extraído correctamente
        """
        user_id = "200"  # JWT spec requires sub to be string
        # Crear token que expira en 1 hora
        expire = datetime.utcnow() + timedelta(hours=1)
        payload = {
            "sub": user_id,
            "exp": expire
        }

        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

        # Decodificar
        result = verify_token(token)

        assert result is not None
        assert result["sub"] == user_id

    def test_token_expires_exactly_at_24_hours(self):
        """
        TC-JWT-003c: Token en el límite exacto de 24 horas
        """
        user_id = "300"  # JWT spec requires sub to be string
        expire = datetime.utcnow() - timedelta(hours=24)
        payload = {"sub": user_id, "exp": expire}

        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
        result = verify_token(token)

        # En el límite exacto, debería fallar (exp <= now)
        assert result is None


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.critical
class TestJWTSecurity:
    """Tests de seguridad de tokens"""

    def test_token_with_invalid_signature(self):
        """
        TC-JWT-004: Token con firma inválida

        Given: Token manipulado o firmado con otra clave
        When: Decodificación
        Then: Error de validación
        """
        # Crear token con settings.secret_key diferente
        fake_token = jwt.encode(
            {"sub": "999", "exp": datetime.utcnow() + timedelta(hours=1)},
            "wrong-secret-key-12345",
            algorithm=settings.algorithm
        )

        # Intentar decodificar con settings.secret_key correcta
        result = verify_token(fake_token)

        # Debe retornar None (firma inválida)
        assert result is None

    def test_token_without_sub_claim(self):
        """
        TC-JWT-005: Token sin claim 'sub'

        Given: Token con payload vacío o sin 'sub'
        When: Decodificación
        Then: Token válido pero sin 'sub' (manejado por dependencies)
        """
        # Crear token sin 'sub'
        expire = datetime.utcnow() + timedelta(hours=1)
        payload = {"exp": expire, "role": "admin"}

        token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

        # Decodificar
        result = verify_token(token)

        # Token es válido (firma + no expirado)
        assert result is not None
        # Pero no tiene 'sub'
        assert "sub" not in result
        # dependencies.py debe rechazarlo

    def test_malformed_token_string(self):
        """
        TC-JWT-004b: Token con formato completamente inválido

        Given: String que no es JWT
        When: Decodificación
        Then: Error de validación
        """
        malformed_token = "esto-no-es-un-jwt-valido"

        result = verify_token(malformed_token)

        assert result is None

    def test_token_with_none_algorithm(self):
        """
        TC-JWT-004c: Intento de ataque con algorithm='none'

        Vulnerabilidad conocida: algunos sistemas permiten 'none' algorithm.
        Verificar que nuestra implementación lo rechaza.
        """
        # Crear token sin firma (algorithm=none)
        payload = {
            "sub": "666",
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp()
        }

        # Intentar crear token sin algoritmo
        none_token = jwt.encode(payload, "", algorithm="none")

        # Intentar decodificar (debe fallar)
        result = verify_token(none_token)

        assert result is None


@pytest.mark.unit
@pytest.mark.utils
class TestJWTEdgeCases:
    """Tests de casos límite y edge cases"""

    def test_empty_payload(self):
        """
        Edge case: Payload vacío (solo exp)
        """
        token = create_access_token(data={})
        payload = verify_token(token)

        # Token válido pero sin 'sub'
        assert payload is not None
        assert "exp" in payload
        assert "sub" not in payload

    def test_large_payload(self):
        """
        Edge case: Payload con muchos claims
        """
        data = {
            "sub": "123",
            "role": "admin",
            "permissions": ["read", "write", "delete"] * 10,
            "metadata": {"key": "value"} * 5
        }

        token = create_access_token(data=data)
        payload = verify_token(token)

        assert payload is not None
        assert payload["sub"] == 123
        assert len(payload["permissions"]) == 30

    def test_unicode_in_payload(self):
        """
        Edge case: Claims con caracteres unicode
        """
        data = {
            "sub": "123",
            "name": "José García",
            "address": "Calle 123, Medellín 🇨🇴"
        }

        token = create_access_token(data=data)
        payload = verify_token(token)

        assert payload["name"] == "José García"
        assert "🇨🇴" in payload["address"]

    def test_token_creation_is_deterministic(self):
        """
        Verify: Dos tokens creados con mismo payload son diferentes
        (incluyen timestamp de creación)
        """
        data = {"sub": "123"}

        token1 = create_access_token(data=data)
        token2 = create_access_token(data=data)

        # Deben ser diferentes (incluyen timestamp)
        assert token1 != token2

        # Pero ambos válidos
        payload1 = verify_token(token1)
        payload2 = verify_token(token2)

        assert payload1["sub"] == payload2["sub"] == 123
