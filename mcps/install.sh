#!/bin/bash
# Script de instalación de dependencias MCP Server

set -e

echo "========================================================================"
echo "🔧 Instalador de Dependencias MCP Server - Brasaland"
echo "========================================================================"
echo ""

# Detectar gestor de paquetes Python
if command -v uv &> /dev/null; then
    echo "✓ uv detectado"
    MANAGER="uv"
elif command -v pip3 &> /dev/null; then
    echo "✓ pip3 detectado"
    MANAGER="pip3"
else
    echo "❌ ERROR: No se encontró ni uv ni pip3"
    exit 1
fi

# Crear entorno virtual si no existe
if [ ! -d "venv-mcp" ]; then
    echo ""
    echo "📦 Creando entorno virtual venv-mcp..."
    python3 -m venv venv-mcp
    echo "✓ Entorno virtual creado"
fi

# Activar entorno virtual
echo ""
echo "🔌 Activando entorno virtual..."
source venv-mcp/bin/activate

# Instalar dependencias
echo ""
echo "📥 Instalando dependencias desde mcps/requirements.txt..."
pip install -r mcps/requirements.txt

echo ""
echo "========================================================================"
echo "✅ Instalación completada"
echo "========================================================================"
echo ""
echo "Para activar el entorno virtual en futuras sesiones:"
echo "  source venv-mcp/bin/activate"
echo ""
echo "Para iniciar el servidor MCP:"
echo "  python3 mcps/server.py"
echo ""
echo "========================================================================"
