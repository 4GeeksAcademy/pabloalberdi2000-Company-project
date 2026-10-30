#!/bin/bash

# ============================================================
# Test de Telemetría: Endpoint de Reporte Analítico
# ============================================================
# Objetivo: Verificar que el endpoint GET /telemetry/report funcione correctamente
# con ventana móvil por defecto (últimos 7 días) y con parámetros personalizados
# ============================================================

echo "🧪 Test de Telemetría: Endpoint de Reporte Analítico"
echo "======================================================"
echo ""

BASE_URL="http://localhost:8000"

# ============================================================
# Test 1: Health Check del Servicio de Reportes
# ============================================================

echo "📋 Test 1: Health Check del Servicio de Reportes"
echo "--------------------------------------------------"
curl -s "$BASE_URL/telemetry/report/health" | python3 -m json.tool
echo ""
echo ""

# ============================================================
# Test 2: Reporte con Ventana Móvil por Defecto (últimos 7 días)
# ============================================================

echo "📋 Test 2: Reporte con Ventana Móvil por Defecto (últimos 7 días)"
echo "-------------------------------------------------------------------"
echo "📊 GET /telemetry/report"
echo ""

curl -s "$BASE_URL/telemetry/report" | python3 -m json.tool
echo ""
echo ""

# ============================================================
# Test 3: Reporte con Periodo Específico (octubre 2026)
# ============================================================

echo "📋 Test 3: Reporte con Periodo Específico (octubre 2026)"
echo "----------------------------------------------------------"
echo "📊 GET /telemetry/report?start_date=2026-10-01T00:00:00Z&end_date=2026-10-31T00:00:00Z"
echo ""

curl -s "$BASE_URL/telemetry/report?start_date=2026-10-01T00:00:00Z&end_date=2026-10-31T00:00:00Z" \
  | python3 -m json.tool
echo ""
echo ""

# ============================================================
# Test 4: Reporte desde Fecha Específica hasta Ahora
# ============================================================

echo "📋 Test 4: Reporte desde Fecha Específica hasta Ahora"
echo "-------------------------------------------------------"
echo "📊 GET /telemetry/report?start_date=2026-10-25T00:00:00Z"
echo ""

curl -s "$BASE_URL/telemetry/report?start_date=2026-10-25T00:00:00Z" \
  | python3 -m json.tool
echo ""
echo ""

# ============================================================
# Test 5: Cache HIT (segunda request idéntica en <60 segundos)
# ============================================================

echo "📋 Test 5: Cache HIT (segunda request idéntica)"
echo "------------------------------------------------"
echo "📊 Primera request (Cache MISS esperado):"
time curl -s "$BASE_URL/telemetry/report?start_date=2026-10-20T00:00:00Z&end_date=2026-10-27T00:00:00Z" \
  > /dev/null
echo ""

echo "📊 Segunda request (Cache HIT esperado - debe ser mucho más rápida):"
time curl -s "$BASE_URL/telemetry/report?start_date=2026-10-20T00:00:00Z&end_date=2026-10-27T00:00:00Z" \
  > /dev/null
echo ""
echo ""

# ============================================================
# Test 6: Error Handling - Formato de Fecha Inválido
# ============================================================

echo "📋 Test 6: Error Handling - Formato de Fecha Inválido"
echo "-------------------------------------------------------"
echo "📊 GET /telemetry/report?start_date=invalid-date"
echo ""

curl -s "$BASE_URL/telemetry/report?start_date=invalid-date" \
  | python3 -m json.tool
echo ""
echo ""

# ============================================================
# Test 7: Error Handling - start_date >= end_date
# ============================================================

echo "📋 Test 7: Error Handling - start_date >= end_date"
echo "----------------------------------------------------"
echo "📊 GET /telemetry/report?start_date=2026-10-30T00:00:00Z&end_date=2026-10-20T00:00:00Z"
echo ""

curl -s "$BASE_URL/telemetry/report?start_date=2026-10-30T00:00:00Z&end_date=2026-10-20T00:00:00Z" \
  | python3 -m json.tool
echo ""
echo ""

# ============================================================
# Test 8: Limpieza Manual del Caché
# ============================================================

echo "📋 Test 8: Limpieza Manual del Caché"
echo "-------------------------------------"
echo "📊 DELETE /telemetry/report/cache"
echo ""

curl -s -X DELETE "$BASE_URL/telemetry/report/cache" \
  | python3 -m json.tool
echo ""
echo ""

# ============================================================
# Test 9: Verificar Caché Limpiado (Health Check post-limpieza)
# ============================================================

echo "📋 Test 9: Verificar Caché Limpiado (cache_entries = 0)"
echo "---------------------------------------------------------"
curl -s "$BASE_URL/telemetry/report/health" | python3 -m json.tool
echo ""
echo ""

# ============================================================
# Resumen
# ============================================================

echo "✅ Tests completados"
echo ""
echo "🔍 Verificar logs del backend:"
echo "   - Cache MISS → '❌ Cache MISS: Generando reporte...'"
echo "   - Cache HIT  → '✅ Cache HIT: Reporte servido desde caché (age: X.Xs)'"
echo ""
echo "📊 Verificar métricas en Supabase:"
echo "   SELECT COUNT(*) FROM telemetry_events WHERE timestamp > NOW() - INTERVAL '7 days';"
echo ""
