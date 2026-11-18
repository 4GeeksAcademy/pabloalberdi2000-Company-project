#!/usr/bin/env python3
"""
Script Helper - Generación de Secretos Seguros

PROPÓSITO: Generar secretos criptográficamente seguros para JWT y tokens

EJECUCIÓN:
    python scripts/generate_secrets.py

OUTPUT:
    - Imprime secretos generados en formato .env
    - Copia al portapapeles (opcional)
"""

import secrets
import sys


def generate_secret(length: int = 32) -> str:
    """
    Genera un secreto criptográficamente seguro.

    Args:
        length: Longitud del secreto en bytes (default: 32)

    Returns:
        String URL-safe base64 encoded
    """
    return secrets.token_urlsafe(length)


def main():
    print("=" * 70)
    print("🔐 Generador de Secretos Seguros - Brasaland Digital")
    print("=" * 70)
    print()

    # Generar secretos
    secret_key = generate_secret(32)
    reset_token_secret = generate_secret(32)

    # Imprimir en formato .env
    print("# Copiar estas líneas a tu archivo .env:")
    print()
    print(f"SECRET_KEY={secret_key}")
    print(f"RESET_TOKEN_SECRET_KEY={reset_token_secret}")
    print()

    # Validaciones de seguridad
    print("=" * 70)
    print("✅ VALIDACIONES DE SEGURIDAD")
    print("=" * 70)
    print(f"✓ SECRET_KEY longitud: {len(secret_key)} caracteres (mínimo 32)")
    print(f"✓ RESET_TOKEN_SECRET_KEY longitud: {len(reset_token_secret)} caracteres (mínimo 32)")
    print(f"✓ Secretos diferentes: {secret_key != reset_token_secret}")
    print(f"✓ Entropía: 256 bits")
    print()

    # Advertencias
    print("=" * 70)
    print("⚠️  ADVERTENCIAS DE SEGURIDAD")
    print("=" * 70)
    print("1. NUNCA commitear estos secretos al repositorio Git")
    print("2. NUNCA compartir secretos por email/Slack/chat inseguro")
    print("3. NUNCA reutilizar secretos entre entornos (dev/staging/prod)")
    print("4. Rotar secretos cada 90 días en producción")
    print("5. Almacenar secretos en un gestor de secretos (AWS Secrets Manager, Vault, etc.)")
    print()

    # Instrucciones de uso
    print("=" * 70)
    print("📋 INSTRUCCIONES DE USO")
    print("=" * 70)
    print("1. Copiar las líneas generadas arriba")
    print("2. Pegar en tu archivo services/api/.env")
    print("3. Verificar que el servidor inicia correctamente")
    print("4. Eliminar el historial de tu terminal después")
    print()

    # Intentar copiar al portapapeles (opcional)
    try:
        import pyperclip
        env_content = f"SECRET_KEY={secret_key}\nRESET_TOKEN_SECRET_KEY={reset_token_secret}"
        pyperclip.copy(env_content)
        print("✅ Secretos copiados al portapapeles")
        print()
    except ImportError:
        print("💡 Tip: Instalar pyperclip para copiar automáticamente al portapapeles")
        print("   pip install pyperclip")
        print()

    print("=" * 70)
    print("✨ Generación completada exitosamente")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
