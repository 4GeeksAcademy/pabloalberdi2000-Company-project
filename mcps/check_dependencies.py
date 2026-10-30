#!/usr/bin/env python3
"""
Verificador de Dependencias MCP Server

Verifica que todas las dependencias necesarias estén instaladas.
"""

import sys
from typing import List, Tuple

# Lista de dependencias requeridas
REQUIRED_PACKAGES = [
    ("fastmcp", "FastMCP"),
    ("mcpauth", "mcpauth (OAuth middleware)"),
    ("httpx", "httpx (HTTP client)"),
    ("pydantic", "Pydantic"),
    ("structlog", "structlog"),
    ("dotenv", "python-dotenv"),
]

OPTIONAL_PACKAGES = [
    ("langchain_mcp_adapters", "langchain-mcp-adapters (para cliente)"),
]


def check_package(package_name: str, display_name: str) -> Tuple[bool, str]:
    """
    Verifica si un paquete está instalado.

    Returns:
        (instalado, versión o error)
    """
    try:
        module = __import__(package_name)
        version = getattr(module, "__version__", "unknown")
        return True, version
    except ImportError as e:
        return False, str(e)


def main():
    print("=" * 70)
    print("🔍 Verificador de Dependencias MCP Server - Brasaland")
    print("=" * 70)
    print()

    # Verificar dependencias requeridas
    print("📦 Dependencias Requeridas:")
    print("-" * 70)

    all_required_ok = True
    for package, display_name in REQUIRED_PACKAGES:
        installed, version = check_package(package, display_name)

        if installed:
            print(f"  ✅ {display_name:<40} v{version}")
        else:
            print(f"  ❌ {display_name:<40} NO INSTALADO")
            all_required_ok = False

    print()

    # Verificar dependencias opcionales
    print("📦 Dependencias Opcionales:")
    print("-" * 70)

    for package, display_name in OPTIONAL_PACKAGES:
        installed, version = check_package(package, display_name)

        if installed:
            print(f"  ✅ {display_name:<40} v{version}")
        else:
            print(f"  ⚠️  {display_name:<40} no instalado (opcional)")

    print()
    print("=" * 70)

    if all_required_ok:
        print("✅ Todas las dependencias requeridas están instaladas")
        print("=" * 70)
        print()
        print("Próximos pasos:")
        print("  1. Configurar mcps/.env (copiar de .env.example)")
        print("  2. Iniciar servidor: python3 mcps/server.py")
        print()
        return 0
    else:
        print("❌ FALTAN DEPENDENCIAS REQUERIDAS")
        print("=" * 70)
        print()
        print("Para instalar:")
        print("  pip install -r mcps/requirements.txt")
        print()
        print("O usar el script de instalación:")
        print("  bash mcps/install.sh")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
