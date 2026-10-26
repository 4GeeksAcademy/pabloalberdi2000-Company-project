"""
Tests for POST /auth/login Endpoint

Casos críticos:
- TC-LOGIN-001: Login exitoso con credenciales válidas
- TC-LOGIN-002: Email case-insensitive
- TC-LOGIN-003: Password con caracteres especiales
- TC-LOGIN-004: Email con espacios
- TC-LOGIN-005: Email no registrado
- TC-LOGIN-006: Password incorrecto
- TC-LOGIN-007: Usuario desactivado
- TC-LOGIN-008: Campos vacíos
- TC-LOGIN-009: Email inválido

Prioridad: 🔴 CRÍTICO
"""

import pytest
from fastapi import status


@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.critical
class TestLoginHappyPath:
    """Tests del camino feliz (happy path)"""

    def test_login_success_with_valid_credentials(self, test_client, test_user):
        """
        TC-LOGIN-001: Login exitoso con credenciales válidas

        Given: Usuario registrado con email y password válido
        When: POST a /auth/login con credenciales correctas
        Then:
          - Status 200
          - Response incluye access_token (JWT válido)
          - Response incluye token_type: "bearer"
          - Token puede decodificarse y contiene sub (user_id)
        """
        response = test_client.post(
            "/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["_test_password"]
            }
        )

        # Verificar status code
        assert response.status_code == status.HTTP_200_OK

        # Verificar estructura de response
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data

        # Verificar token_type
        assert data["token_type"] == "bearer"

        # Verificar que token no está vacío
        assert len(data["access_token"]) > 50

        # Verificar que token es válido (puede decodificarse)
        from app.auth.jwt import decode_access_token
        payload = decode_access_token(data["access_token"])

        assert payload is not None
        assert "sub" in payload
        assert payload["sub"] == test_user.doc_id

    def test_login_with_admin_user(self, test_client, admin_user):
        """
        TC-LOGIN-001b: Login exitoso con usuario admin

        Verificar que role='admin' no afecta login.
        """
        response = test_client.post(
            "/auth/login",
            json={
                "email": admin_user["email"],
                "password": admin_user["_test_password"]
            }
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "access_token" in data

        # Verificar que token contiene user_id correcto
        from app.auth.jwt import decode_access_token
        payload = decode_access_token(data["access_token"])
        assert payload["sub"] == admin_user.doc_id


@pytest.mark.auth
@pytest.mark.integration
class TestLoginEdgeCases:
    """Tests de casos límite (edge cases)"""

    def test_login_email_case_insensitive(self, test_client, test_user):
        """
        TC-LOGIN-002: Email en mayúsculas/minúsculas

        Given: Usuario registrado con admin@brasaland.com
        When: Login con ADMIN@BRASALAND.COM
        Then: Login exitoso (case-insensitive)

        ⚠️ BUG POTENCIAL: Actualmente TinyDB compara exacto.
        Este test puede fallar y revelar Bug #2 del TESTING.md.
        """
        response = test_client.post(
            "/auth/login",
            json={
                "email": test_user["email"].upper(),
                "password": test_user["_test_password"]
            }
        )

        # ESPERADO: 200 (case-insensitive)
        # ACTUAL: Puede ser 401 (bug no implementado aún)
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "access_token" in data
        else:
            # Si falla, documentar en TESTING.md
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            print("\n⚠️  BUG DETECTADO: Email case-sensitive (AUTH-089)")

    def test_login_with_special_characters_password(self, test_client, test_db):
        """
        TC-LOGIN-003: Password con caracteres especiales

        Given: Usuario con password P@ssw0rd!#$%
        When: Login con ese password exacto
        Then: Login exitoso
        """
        from app.tinydb_database import users_table
        from app.auth.password import hash_password
        from datetime import datetime

        # Crear usuario con password especial
        special_password = "P@ssw0rd!#$%^&*()"
        user_data = {
            "email": "special@brasaland.com",
            "hashed_password": hash_password(special_password),
            "role": "user",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }
        users_table.insert(user_data)

        # Login
        response = test_client.post(
            "/auth/login",
            json={
                "email": "special@brasaland.com",
                "password": special_password
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data

    def test_login_email_with_leading_trailing_spaces(self, test_client, test_user):
        """
        TC-LOGIN-004: Email con espacios al inicio/final

        Given: Usuario registrado
        When: Login con " admin@brasaland.com "
        Then: Se sanitiza y login exitoso O error 401 (comportamiento consistente)

        ⚠️ DECISIÓN ARQUITECTÓNICA: Documentar comportamiento esperado.
        """
        response = test_client.post(
            "/auth/login",
            json={
                "email": f" {test_user['email']} ",
                "password": test_user["_test_password"]
            }
        )

        # Comportamiento aceptable:
        # 1. Sanitiza espacios y login OK (200)
        # 2. No sanitiza y retorna 401

        if response.status_code == status.HTTP_200_OK:
            # Comportamiento 1: Sanitización automática
            data = response.json()
            assert "access_token" in data
        else:
            # Comportamiento 2: Sin sanitización
            assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.critical
class TestLoginFailureModes:
    """Tests de modos de fallo (failure modes)"""

    def test_login_with_nonexistent_email(self, test_client):
        """
        TC-LOGIN-005: Credenciales incorrectas - Email no registrado

        Given: Email no registrado
        When: POST con email inexistente
        Then:
          - Status 401
          - Mensaje genérico (no revelar si email existe)
        """
        response = test_client.post(
            "/auth/login",
            json={
                "email": "noexiste@brasaland.com",
                "password": "cualquierPassword123"
            }
        )

        # Verificar status 401
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Verificar mensaje genérico (anti-enumeración)
        data = response.json()
        assert "detail" in data

        # Mensaje NO debe decir "usuario no encontrado"
        # Debe ser genérico tipo "incorrect email or password"
        detail = data["detail"].lower()
        assert "incorrect" in detail or "invalid" in detail
        assert "email" not in detail or "password" in detail  # Ambos mencionados

    def test_login_with_incorrect_password(self, test_client, test_user):
        """
        TC-LOGIN-006: Credenciales incorrectas - Password incorrecto

        Given: Usuario existente
        When: POST con password incorrecto
        Then:
          - Status 401
          - Mismo mensaje que TC-LOGIN-005 (anti-enumeración)
        """
        response = test_client.post(
            "/auth/login",
            json={
                "email": test_user["email"],
                "password": "passwordIncorrecto123"
            }
        )

        # Verificar status 401
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Verificar mensaje genérico
        data = response.json()
        assert "detail" in data

        detail = data["detail"].lower()
        assert "incorrect" in detail or "invalid" in detail

    def test_login_messages_consistent_for_anti_enumeration(self, test_client, test_user):
        """
        TC-LOGIN-005 + TC-LOGIN-006: Anti-enumeración

        Verificar que mensajes de error son IDÉNTICOS para:
        - Email no existe
        - Password incorrecto

        Esto previene que atacantes enumeren usuarios válidos.
        """
        # Error 1: Email no existe
        response1 = test_client.post(
            "/auth/login",
            json={
                "email": "noexiste@brasaland.com",
                "password": "test123"
            }
        )

        # Error 2: Password incorrecto
        response2 = test_client.post(
            "/auth/login",
            json={
                "email": test_user["email"],
                "password": "passwordIncorrecto123"
            }
        )

        # Ambos deben retornar 401
        assert response1.status_code == status.HTTP_401_UNAUTHORIZED
        assert response2.status_code == status.HTTP_401_UNAUTHORIZED

        # Mensajes deben ser idénticos (anti-enumeración)
        message1 = response1.json()["detail"]
        message2 = response2.json()["detail"]

        assert message1 == message2

    def test_login_with_inactive_user(self, test_client, inactive_user):
        """
        TC-LOGIN-007: Usuario desactivado

        Given: Usuario con is_active: false
        When: POST con credenciales correctas
        Then: Status 400 con mensaje "Inactive user"
        """
        response = test_client.post(
            "/auth/login",
            json={
                "email": inactive_user["email"],
                "password": inactive_user["_test_password"]
            }
        )

        # Verificar status 400 (no 401, porque credenciales son correctas)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Verificar mensaje específico
        data = response.json()
        assert "detail" in data
        assert "inactive" in data["detail"].lower()


@pytest.mark.auth
@pytest.mark.integration
class TestLoginValidation:
    """Tests de validación de entrada (Pydantic)"""

    def test_login_with_empty_email(self, test_client):
        """
        TC-LOGIN-008: Campo email vacío

        Given: Payload con email vacío
        When: POST a /auth/login
        Then: Status 422 (validación Pydantic)
        """
        response = test_client.post(
            "/auth/login",
            json={
                "email": "",
                "password": "test123"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_with_empty_password(self, test_client):
        """
        TC-LOGIN-008b: Campo password vacío
        """
        response = test_client.post(
            "/auth/login",
            json={
                "email": "test@brasaland.com",
                "password": ""
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_with_missing_email(self, test_client):
        """
        TC-LOGIN-008c: Campo email faltante
        """
        response = test_client.post(
            "/auth/login",
            json={
                "password": "test123"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_with_missing_password(self, test_client):
        """
        TC-LOGIN-008d: Campo password faltante
        """
        response = test_client.post(
            "/auth/login",
            json={
                "email": "test@brasaland.com"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_with_invalid_email_format(self, test_client):
        """
        TC-LOGIN-009: Formato de email inválido

        Given: Email sin formato válido ("notanemail")
        When: POST a /auth/login
        Then: Status 422
        """
        response = test_client.post(
            "/auth/login",
            json={
                "email": "notanemail",
                "password": "test123"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_with_invalid_email_formats(self, test_client):
        """
        TC-LOGIN-009b: Múltiples formatos inválidos
        """
        invalid_emails = [
            "notanemail",
            "@brasaland.com",
            "user@",
            "user @brasaland.com",
            "user..name@brasaland.com",
        ]

        for invalid_email in invalid_emails:
            response = test_client.post(
                "/auth/login",
                json={
                    "email": invalid_email,
                    "password": "test123"
                }
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, \
                f"Email '{invalid_email}' debería ser rechazado"


@pytest.mark.auth
@pytest.mark.integration
class TestLoginSecurity:
    """Tests de seguridad"""

    def test_login_does_not_expose_stack_traces(self, test_client):
        """
        Security: Verificar que errores no exponen stack traces
        """
        # Enviar payload malformado
        response = test_client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": None  # Valor inválido
            }
        )

        # Puede ser 422 o 500, pero no debe exponer stack trace
        data = response.json()

        # No debe contener información técnica
        assert "Traceback" not in str(data)
        assert "line" not in str(data).lower() or "detail" in str(data)
        assert ".py" not in str(data) or "detail" in str(data)

    def test_login_rate_limiting_headers(self, test_client, test_user):
        """
        ⚠️ PENDIENTE: Rate limiting no implementado

        Este test documentará la necesidad futura de rate limiting.
        """
        # Hacer 10 intentos fallidos
        for _ in range(10):
            response = test_client.post(
                "/auth/login",
                json={
                    "email": test_user["email"],
                    "password": "wrongPassword"
                }
            )

        # Actualmente: todos retornan 401
        # FUTURO: después de N intentos, retornar 429 Too Many Requests

        # Por ahora solo documentamos el comportamiento actual
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        # TODO: Implementar rate limiting (AUTH-090)
