#!/bin/bash

# ============================================================
# Test de Telemetría: Lote Mixto (Válidos + Inválidos)
# ============================================================
# Objetivo: Verificar arquitectura resiliente del endpoint
# Resultado esperado: HTTP 200 con {"received": 5, "stored": 2, "rejected": 3}
# ============================================================

echo "🧪 Test de Telemetría: Lote Mixto"
echo "=================================="
echo ""
echo "📦 Enviando lote de 5 eventos (2 válidos + 3 inválidos)..."
echo ""

curl -X POST "http://localhost:8000/telemetry/events" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "eventId": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
        "timestamp": "2026-10-30T15:00:00.000Z",
        "sessionId": "sess_test_mixed",
        "userId": null,
        "event_type": "frontend_error_uncaught",
        "schemaVersion": "1.0.0",
        "requestId": "req_test_001",
        "properties": {
          "error_message": "Test error from mixed batch",
          "error_name": "TestError",
          "page_url": "http://localhost:3000/test"
        }
      },
      {
        "eventId": "INVALID_UUID_NOT_V4",
        "timestamp": "2026-10-30T15:01:00.000Z",
        "event_type": "invalid_event_bad_uuid",
        "schemaVersion": "1.0.0",
        "requestId": "req_test_002",
        "properties": {}
      },
      {
        "timestamp": "2026-10-30T15:02:00.000Z",
        "event_type": "missing_event_id_field",
        "schemaVersion": "1.0.0",
        "properties": {}
      },
      {
        "eventId": "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
        "timestamp": "NOT_A_VALID_ISO_8601_TIMESTAMP",
        "event_type": "page_view",
        "schemaVersion": "1.0.0",
        "requestId": "req_test_003",
        "properties": {
          "page_name": "test_page"
        }
      },
      {
        "eventId": "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
        "timestamp": "2026-10-30T15:03:00.000Z",
        "sessionId": "sess_test_mixed",
        "userId": null,
        "event_type": "stock_threshold_triggered",
        "schemaVersion": "1.0.0",
        "requestId": "req_test_004",
        "properties": {
          "ingredient_id": 999,
          "ingredient_name": "Test Ingredient",
          "warehouse": "medellin_centro",
          "current_stock": 3.5,
          "min_stock": 10.0,
          "reorder_point": 15.0,
          "threshold_severity": "critical"
        }
      }
    ]
  }' | python3 -m json.tool

echo ""
echo ""
echo "✅ Resultado esperado:"
echo "   received: 5"
echo "   stored: 2"
echo "   rejected: 3"
echo ""
echo "📊 Verificar en Supabase:"
echo "   SELECT * FROM telemetry_events"
echo "   WHERE batch_id = (SELECT batch_id FROM telemetry_events ORDER BY ingested_at DESC LIMIT 1);"
echo ""
echo "🔍 Verificar en logs del backend:"
echo "   📊 Telemetry batch: 5 received | 2 valid | 3 rejected"
echo ""
