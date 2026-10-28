#!/bin/sh
# ============================================
# Start Script para Frontend Next.js
# Brasaland Digital Platform
# ============================================

set -e

echo "🚀 Starting Brasaland Frontend Services..."
echo ""

# Función para manejar señales de terminación
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}

trap cleanup SIGTERM SIGINT

# Iniciar Backoffice en puerto 3001
echo "📱 Starting Backoffice on port 3001..."
cd /app/backoffice
PORT=3001 npm run dev &
BACKOFFICE_PID=$!

echo ""
echo "✅ Services started:"
echo "   📱 Backoffice: http://localhost:3001"
echo ""
echo "💡 Logs will appear below. Press Ctrl+C to stop all services."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Esperar a que los procesos terminen
wait $BACKOFFICE_PID
