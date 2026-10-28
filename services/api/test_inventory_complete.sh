#!/bin/bash
# Test completo del sistema de inventario

set -e

API_URL="http://localhost:8000"

echo "🔐 1. Login para obtener JWT..."
TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@brasaland.com", "password": "admin123"}')

TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
  echo "❌ Error: No se pudo obtener el token"
  exit 1
fi

echo "✅ Token obtenido"
echo ""

echo "📦 2. Listar ingredientes..."
curl -s "$API_URL/inventory/ingredients?limit=3" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -30
echo ""

echo "🥩 3. Obtener detalle de ingrediente #1 (Carne de res)..."
curl -s "$API_URL/inventory/ingredients/1" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "📊 4. Reporte de stock general..."
curl -s "$API_URL/inventory/stock-report?low_stock_only=false" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -40
echo ""

echo "📋 5. Listar órdenes (primeras 5)..."
curl -s "$API_URL/inventory/orders?limit=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -40
echo ""

echo "➕ 6. Crear nueva entrada de stock..."
curl -s -X POST "$API_URL/inventory/orders/inbound" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": 1,
    "quantity": 50.0,
    "warehouse": "bogota_suba",
    "notes": "Pedido de prueba - test automatizado"
  }' | python3 -m json.tool
echo ""

echo "✅ ¡Test completado exitosamente!"
