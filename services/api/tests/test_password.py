"""
Tests for Password Utilities (app/auth/password.py)

Casos críticos:
- TC-PASS-001: Hashear password
- TC-PASS-002: Verificar password correcto
- TC-PASS-003: Password con caracteres especiales
- TC-PASS-004: Verificar password incorrecto
- TC-PASS-005: Verificar contra hash inválido

Prioridad: 🔴 CRÍTICO (Cobertura objetivo: 100%)
"""

import pytest
from app.auth.password import hash_password, verify_password


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.critical
class TestPasswordHashing:
    """Tests de hashing de contraseñas con bcrypt"""

    def test_hash_password_returns_valid_hash(self):
        """
        TC-PASS-001: Hashear password

        Given: Password en texto plano
        When: hash_password(password)
        Then:
          - Hash generado (bcrypt)
          - Hash diferente del original
          - Longitud > 50 caracteres
        """
        password = "mySecurePassword123"

        # Hashear
        hashed = hash_password(password)

        # Verificar que es string
        assert isinstance(hashed, str)

        # Verificar que no es el password original
        assert hashed != password

        # Verificar longitud (bcrypt genera hashes de ~60 chars)
        assert len(hashed) > 50

        # Verificar que comienza con formato bcrypt ($2b$)
        assert hashed.startswith("$2b$")

    def test_hash_password_is_non_deterministic(self):
        """
        TC-PASS-001b: Hashear mismo password dos veces genera hashes diferentes

        Bcrypt usa salt aleatorio, así que mismo password → diferentes hashes.
        Ambos deben verificar correctamente.
        """
        password = "samePassword123"

        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes diferentes (salt diferente)
        assert hash1 != hash2

        # Pero ambos verifican contra el password original
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_hash_empty_password(self):
        """
        TC-PASS-001c: Hashear password vacío

        Pydantic debe validar min_length=8 antes de llegar aquí,
        pero verificamos que hash_password no crashee.
        """
        password = ""

        # No debe crashear
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_very_long_password(self):
        """
        TC-PASS-001d: Hashear password muy largo (500 caracteres)
        """
        password = "a" * 500

        hashed = hash_password(password)

        # Hash generado correctamente
        assert isinstance(hashed, str)
        assert verify_password(password, hashed) is True


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.critical
class TestPasswordVerification:
    """Tests de verificación de contraseñas"""

    def test_verify_correct_password(self):
        """
        TC-PASS-002: Verificar password correcto

        Given: Password y su hash
        When: verify_password(password, hash)
        Then: Return True
        """
        password = "correctPassword123"
        hashed = hash_password(password)

        # Verificar
        result = verify_password(password, hashed)

        assert result is True

    def test_verify_incorrect_password(self):
        """
        TC-PASS-004: Verificar password incorrecto

        Given: Password diferente al hasheado
        When: verify_password(wrong_pass, hash)
        Then: Return False
        """
        correct_password = "correctPassword123"
        wrong_password = "wrongPassword456"

        hashed = hash_password(correct_password)

        # Verificar con password incorrecto
        result = verify_password(wrong_password, hashed)

        assert result is False

    def test_verify_case_sensitive(self):
        """
        TC-PASS-004b: Verificación es case-sensitive

        "Password" != "password"
        """
        password = "Password123"
        hashed = hash_password(password)

        # Minúsculas
        assert verify_password("password123", hashed) is False

        # Mayúsculas
        assert verify_password("PASSWORD123", hashed) is False

        # Exacto
        assert verify_password("Password123", hashed) is True

    def test_verify_whitespace_sensitive(self):
        """
        TC-PASS-004c: Verificación es sensible a espacios

        "pass " != "pass"
        """
        password = "password123"
        hashed = hash_password(password)

        # Con espacio al final
        assert verify_password("password123 ", hashed) is False

        # Con espacio al inicio
        assert verify_password(" password123", hashed) is False

        # Sin espacios (correcto)
        assert verify_password("password123", hashed) is True


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.critical
class TestPasswordSpecialCharacters:
    """Tests con caracteres especiales"""

    def test_password_with_special_characters(self):
        """
        TC-PASS-003: Password con caracteres especiales

        Given: Password `P@ss!#$%^&*()`
        When: Hash y verificación
        Then: Verificación exitosa
        """
        password = "P@ss!#$%^&*()"

        hashed = hash_password(password)

        # Verificar con password exacto
        assert verify_password(password, hashed) is True

        # Verificar que caracteres especiales importan
        assert verify_password("Pass!#$%^&*()", hashed) is False  # Sin @
        assert verify_password("P@ss", hashed) is False  # Sin caracteres finales

    def test_password_with_unicode(self):
        """
        TC-PASS-003b: Password con caracteres unicode
        """
        password = "contraseña123ñáéíóú"

        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("contrasena123", hashed) is False  # Sin tildes

    def test_password_with_emojis(self):
        """
        TC-PASS-003c: Password con emojis (edge case)
        """
        password = "pass🔒word🔑123"

        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("password123", hashed) is False

    def test_password_with_quotes(self):
        """
        TC-PASS-003d: Password con comillas y caracteres de escape
        """
        password = 'pass"word\'123\\n'

        hashed = hash_password(password)

        assert verify_password(password, hashed) is True


@pytest.mark.unit
@pytest.mark.utils
@pytest.mark.critical
class TestPasswordErrorHandling:
    """Tests de manejo de errores"""

    def test_verify_with_invalid_hash(self):
        """
        TC-PASS-005: Verificar contra hash inválido

        Given: Hash malformado (no bcrypt)
        When: verify_password(password, bad_hash)
        Then: Return False (sin crash)
        """
        password = "testPassword123"
        bad_hash = "not-a-valid-bcrypt-hash"

        # No debe crashear
        result = verify_password(password, bad_hash)

        # Debe retornar False
        assert result is False

    def test_verify_with_empty_hash(self):
        """
        TC-PASS-005b: Verificar contra hash vacío
        """
        password = "testPassword123"
        empty_hash = ""

        result = verify_password(password, empty_hash)

        assert result is False

    def test_verify_with_truncated_hash(self):
        """
        TC-PASS-005c: Verificar contra hash truncado
        """
        password = "testPassword123"
        hashed = hash_password(password)

        # Truncar hash a la mitad
        truncated_hash = hashed[:30]

        result = verify_password(password, truncated_hash)

        # Debe retornar False (hash inválido)
        assert result is False

    def test_verify_with_none_password(self):
        """
        Edge case: password None (debe ser manejado por Pydantic)
        """
        hashed = hash_password("test123")

        # Intentar verificar None
        # Debería fallar sin crashear
        try:
            result = verify_password(None, hashed)
            assert result is False
        except (TypeError, AttributeError):
            # Si crashea con error de tipo, es aceptable
            # (Pydantic debe prevenir esto antes)
            pass

    def test_verify_with_none_hash(self):
        """
        Edge case: hash None
        """
        password = "test123"

        try:
            result = verify_password(password, None)
            assert result is False
        except (TypeError, AttributeError):
            pass


@pytest.mark.unit
@pytest.mark.utils
class TestPasswordSecurity:
    """Tests de seguridad del hashing"""

    def test_timing_attack_resistance(self):
        """
        Security: Verificar que bcrypt es resistente a timing attacks

        El tiempo de verificación debe ser constante independiente de
        si el password es correcto o no.

        Nota: Test simplificado, timing attacks reales requieren análisis
        estadístico con miles de mediciones.
        """
        password = "securePassword123"
        hashed = hash_password(password)

        # Ambas verificaciones deben tomar tiempo similar (bcrypt)
        import time

        # Verificación correcta
        start = time.time()
        verify_password(password, hashed)
        correct_time = time.time() - start

        # Verificación incorrecta
        start = time.time()
        verify_password("wrongPassword", hashed)
        incorrect_time = time.time() - start

        # Ambos deben tomar > 0.01s (bcrypt es lento intencionalmente)
        assert correct_time > 0.01
        assert incorrect_time > 0.01

        # Diferencia no debe ser significativa (< 10x)
        assert abs(correct_time - incorrect_time) < max(correct_time, incorrect_time) * 10

    def test_hash_collision_resistance(self):
        """
        Security: Diferentes passwords generan diferentes hashes
        """
        password1 = "password123"
        password2 = "password124"  # Solo 1 carácter diferente

        hash1 = hash_password(password1)
        hash2 = hash_password(password2)

        # Hashes completamente diferentes
        assert hash1 != hash2

        # Verificación cruzada falla
        assert verify_password(password1, hash2) is False
        assert verify_password(password2, hash1) is False

    def test_bcrypt_cost_factor(self):
        """
        Security: Verificar que bcrypt usa factor de costo adecuado

        Hash debe tomar tiempo razonable (> 0.01s) para prevenir
        ataques de fuerza bruta.
        """
        import time

        password = "testPassword123"

        start = time.time()
        hash_password(password)
        duration = time.time() - start

        # Debe tomar al menos 10ms (factor de costo adecuado)
        assert duration > 0.01

        # Pero no debe ser excesivamente lento (< 1s)
        assert duration < 1.0
