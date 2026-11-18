# 🛒 API de Gestión de Proveedores - Brasaland Digital

**Versión**: 1.0.0  
**Stack**: FastAPI + Pydantic v2 + TinyDB  
**Fecha**: 2026-11-18

---

## 📋 Descripción

API REST completa para gestión de proveedores de Brasaland, reemplazando la hoja de cálculo manual con un sistema centralizado, validado y persistente.

**Características**:
- ✅ 20 proveedores pre-cargados (12 Colombia + 8 USA)
- ✅ Validación estricta con Pydantic v2 (HTTP 422)
- ✅ Seeder idempotente (re-ejecutable sin duplicados)
- ✅ 7 endpoints REST con filtros
- ✅ Autenticación JWT requerida
- ✅ Timestamps automáticos (created_at, updated_at)
- ✅ Persistencia TinyDB (JSON)

---

## 🚀 Setup e Instalación

### 1. Activar entorno virtual

```bash
cd services/api
source venv/bin/activate
```

### 2. Instalar dependencias (si es necesario)

```bash
pip install -r requirements.txt
```

### 3. Ejecutar seeder (primera vez)

```bash
python seed.py
```

**Output esperado**:
```
======================================================================
🌱 SUPPLIER SEEDER - Brasaland Digital
======================================================================

✅ INSERTED: Carnes Premium Colombia SAS
✅ INSERTED: Frigorífico del Valle
# ... 18 más ...

📊 SEED REPORT
======================================================================
Total proveedores en lista:  20
✅ Insertados:                20
⏭️  Skipped (duplicados):      0
❌ Errores:                   0
======================================================================

📦 Total proveedores en BD: 20

✨ Seeding completado exitosamente
```

### 4. Iniciar servidor

```bash
uvicorn app.main:app --reload --port 8000
```

**Verificar servidor activo**:
```bash
curl http://localhost:8000/health
# Respuesta: {"status": "healthy"}
```

---

## 🔐 Autenticación

Todos los endpoints requieren JWT token en header `Authorization`.

### Obtener token

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@brasaland.com&password=admin123"
```

**Respuesta**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Usar token en requests

```bash
export TOKEN="<access_token>"

curl "http://localhost:8000/api/suppliers" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📡 Endpoints API

### Base URL

```
http://localhost:8000/api/suppliers
```

### Autenticación requerida

Todos los endpoints requieren header:
```
Authorization: Bearer <access_token>
```

---

### 1. POST /suppliers

**Crear proveedor**

**Request**:
```bash
curl -X POST "http://localhost:8000/api/suppliers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nuevo Proveedor Test",
    "country": "Colombia",
    "categories": ["carne_proteinas"],
    "delivery_rate_usd": 30.00,
    "status": "activo",
    "contact_email": "test@example.com",
    "contact_phone": "+57 300 123 4567"
  }'
```

**Response** (HTTP 201 Created):
```json
{
  "id": 21,
  "name": "Nuevo Proveedor Test",
  "country": "Colombia",
  "categories": ["carne_proteinas"],
  "delivery_rate_usd": 30.00,
  "status": "activo",
  "contact_email": "test@example.com",
  "contact_phone": "+57 300 123 4567",
  "created_at": "2026-11-18T15:30:00.123456Z",
  "updated_at": "2026-11-18T15:30:00.123456Z"
}
```

**Validaciones**:
- ❌ `delivery_rate_usd <= 0` → HTTP 422
- ❌ `status` ∉ {activo, suspendido} → HTTP 422
- ❌ `country` ∉ {Colombia, USA} → HTTP 422
- ❌ `categories` vacía → HTTP 422
- ❌ `name` duplicado → HTTP 409 Conflict

---

### 2. GET /suppliers

**Listar proveedores con filtros opcionales**

#### Sin filtros (todos)

```bash
curl "http://localhost:8000/api/suppliers" \
  -H "Authorization: Bearer $TOKEN"
```

**Response** (HTTP 200):
```json
{
  "total": 20,
  "items": [
    {
      "id": 1,
      "name": "Carnes Premium Colombia SAS",
      "country": "Colombia",
      "categories": ["carne_proteinas"],
      "delivery_rate_usd": 25.50,
      "status": "activo",
      ...
    },
    // ... 19 proveedores más
  ],
  "limit": 100,
  "offset": 0
}
```

#### Filtrar por país

```bash
curl "http://localhost:8000/api/suppliers?country=Colombia" \
  -H "Authorization: Bearer $TOKEN"

# Respuesta: total=12 (solo proveedores de Colombia)
```

#### Filtrar por categoría

```bash
curl "http://localhost:8000/api/suppliers?category=carne_proteinas" \
  -H "Authorization: Bearer $TOKEN"

# Respuesta: total=5 (proveedores de carne)
```

#### Filtrar por estado

```bash
curl "http://localhost:8000/api/suppliers?status=activo" \
  -H "Authorization: Bearer $TOKEN"

# Respuesta: total=19 (1 suspendido)
```

#### Paginación

```bash
curl "http://localhost:8000/api/suppliers?limit=5&offset=0" \
  -H "Authorization: Bearer $TOKEN"

# Respuesta: primeros 5 proveedores
```

#### Filtros combinados

```bash
curl "http://localhost:8000/api/suppliers?country=USA&category=bebidas&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Respuesta: proveedores de bebidas en USA
```

**Parámetros query**:
- `status`: activo | suspendido
- `country`: Colombia | USA
- `category`: carne_proteinas | verduras_vegetales | salsas_condimentos | bebidas | packaging_embalajes | productos_limpieza
- `limit`: 1-500 (default: 100)
- `offset`: ≥ 0 (default: 0)

---

### 3. GET /suppliers/summary

**Obtener métricas agregadas**

```bash
curl "http://localhost:8000/api/suppliers/summary" \
  -H "Authorization: Bearer $TOKEN"
```

**Response** (HTTP 200):
```json
{
  "total_suppliers": 20,
  "by_status": {
    "activo": 19,
    "suspendido": 1
  },
  "by_country": {
    "Colombia": 12,
    "USA": 8
  },
  "by_category": {
    "carne_proteinas": 5,
    "verduras_vegetales": 3,
    "salsas_condimentos": 2,
    "bebidas": 4,
    "packaging_embalajes": 3,
    "productos_limpieza": 4
  },
  "avg_delivery_rate_usd": 24.85
}
```

---

### 4. GET /suppliers/{id}

**Obtener detalle de proveedor**

```bash
curl "http://localhost:8000/api/suppliers/1" \
  -H "Authorization: Bearer $TOKEN"
```

**Response** (HTTP 200):
```json
{
  "id": 1,
  "name": "Carnes Premium Colombia SAS",
  "country": "Colombia",
  "categories": ["carne_proteinas"],
  "delivery_rate_usd": 25.50,
  "status": "activo",
  "contact_email": "ventas@carnespremium.co",
  "contact_phone": "+57 300 123 4567",
  "created_at": "2026-11-18T10:00:00Z",
  "updated_at": "2026-11-18T10:00:00Z"
}
```

**Errores**:
- ❌ ID inexistente → HTTP 404 Not Found

---

### 5. PUT /suppliers/{id}

**Actualizar campos de proveedor**

```bash
curl -X PUT "http://localhost:8000/api/suppliers/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Carnes Premium Colombia SAS (Actualizado)",
    "delivery_rate_usd": 27.00,
    "contact_email": "nuevo@carnespremium.co"
  }'
```

**Response** (HTTP 200):
```json
{
  "id": 1,
  "name": "Carnes Premium Colombia SAS (Actualizado)",
  "delivery_rate_usd": 27.00,
  "contact_email": "nuevo@carnespremium.co",
  "updated_at": "2026-11-18T16:00:00Z",  // ✅ Actualizado automáticamente
  ...
}
```

**Notas**:
- Actualización parcial: solo actualiza campos enviados
- `updated_at` se genera automáticamente
- Validaciones Pydantic aplican

**Errores**:
- ❌ ID inexistente → HTTP 404
- ❌ Nombre duplicado → HTTP 409 Conflict
- ❌ Tarifa <= 0 → HTTP 422

---

### 6. PATCH /suppliers/{id}/rate

**Actualizar tarifa de entrega (endpoint dedicado)**

```bash
curl -X PATCH "http://localhost:8000/api/suppliers/1/rate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"delivery_rate_usd": 30.00}'
```

**Response** (HTTP 200):
```json
{
  "id": 1,
  "name": "Carnes Premium Colombia SAS",
  "delivery_rate_usd": 30.00,  // ✅ Tarifa actualizada
  "updated_at": "2026-11-18T16:15:00Z",  // ✅ Timestamp registrado para auditoría
  ...
}
```

**Propósito**: Endpoint dedicado para cambios de tarifa con auditoría de `updated_at`.

**Validaciones**:
- ❌ `delivery_rate_usd <= 0` → HTTP 422

---

### 7. PATCH /suppliers/{id}/status

**Actualizar estado del proveedor**

```bash
curl -X PATCH "http://localhost:8000/api/suppliers/1/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "suspendido"}'
```

**Response** (HTTP 200):
```json
{
  "id": 1,
  "name": "Carnes Premium Colombia SAS",
  "status": "suspendido",  // ✅ Estado actualizado
  "updated_at": "2026-11-18T16:20:00Z",
  ...
}
```

**Validaciones**:
- ❌ `status` ∉ {activo, suspendido} → HTTP 422

---

### 8. DELETE /suppliers/{id}

**Eliminar proveedor**

```bash
curl -X DELETE "http://localhost:8000/api/suppliers/1" \
  -H "Authorization: Bearer $TOKEN"
```

**Response**: HTTP 204 No Content (sin body)

**Errores**:
- ❌ ID inexistente → HTTP 404 Not Found

---

## 🧪 Testing Manual Completo

### Script de testing

```bash
#!/bin/bash

# Variables
export API_URL="http://localhost:8000"
export TOKEN=""  # Obtener de login

# 1. Autenticación
echo "1. Autenticando..."
export TOKEN=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@brasaland.com&password=admin123" | jq -r '.access_token')

# 2. Listar todos
echo "2. Listando todos los proveedores..."
curl -s "$API_URL/api/suppliers" \
  -H "Authorization: Bearer $TOKEN" | jq '.total'

# 3. Filtrar por país
echo "3. Filtrando por Colombia..."
curl -s "$API_URL/api/suppliers?country=Colombia" \
  -H "Authorization: Bearer $TOKEN" | jq '.total'

# 4. Filtrar por categoría
echo "4. Filtrando por carne_proteinas..."
curl -s "$API_URL/api/suppliers?category=carne_proteinas" \
  -H "Authorization: Bearer $TOKEN" | jq '.total'

# 5. Crear proveedor
echo "5. Creando nuevo proveedor..."
curl -s -X POST "$API_URL/api/suppliers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Supplier",
    "country": "Colombia",
    "categories": ["bebidas"],
    "delivery_rate_usd": 25.00
  }' | jq '.id'

# 6. Actualizar tarifa
echo "6. Actualizando tarifa..."
curl -s -X PATCH "$API_URL/api/suppliers/1/rate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"delivery_rate_usd": 30.00}' | jq '.delivery_rate_usd'

# 7. Métricas
echo "7. Obteniendo métricas..."
curl -s "$API_URL/api/suppliers/summary" \
  -H "Authorization: Bearer $TOKEN" | jq

# 8. Test 404
echo "8. Verificando 404 en ID inexistente..."
curl -s "$API_URL/api/suppliers/999" \
  -H "Authorization: Bearer $TOKEN" | jq '.detail'

# 9. Test 422 (tarifa inválida)
echo "9. Verificando validación 422..."
curl -s -X POST "$API_URL/api/suppliers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"delivery_rate_usd": -10}' | jq '.detail'

echo "✅ Tests completados"
```

---

## 📊 Datos Pre-cargados

**20 proveedores** distribuidos según BRIEFING.md:

### Colombia (12 proveedores)

| Nombre | Categoría | Tarifa USD | Estado |
|--------|-----------|------------|--------|
| Carnes Premium Colombia SAS | carne_proteinas | 25.50 | activo |
| Frigorífico del Valle | carne_proteinas | 22.00 | activo |
| Agrícola Los Andes | verduras_vegetales | 15.00 | activo |
| Verdes y Frescos Medellín | verduras_vegetales | 18.50 | activo |
| Salsas Artesanales Bogotá | salsas_condimentos | 12.00 | activo |
| Condimentos del Caribe | salsas_condimentos | 14.50 | activo |
| Distribuidora de Bebidas Andina | bebidas | 30.00 | activo |
| Jugos Naturales Colombia | bebidas | 20.00 | activo |
| Empaques y Envases del Sur | packaging_embalajes | 18.00 | activo |
| EcoPack Colombia | packaging_embalajes | 22.50 | activo |
| Productos de Limpieza Industrial Medellín | productos_limpieza | 16.00 | activo |
| Higiene Total Colombia | productos_limpieza | 14.00 | activo |

### USA - Florida (8 proveedores)

| Nombre | Categoría | Tarifa USD | Estado |
|--------|-----------|------------|--------|
| Florida Premium Meats Inc | carne_proteinas | 35.00 | activo |
| Miami Butcher Supply | carne_proteinas | 32.50 | activo |
| Fresh Produce Florida LLC | verduras_vegetales | 28.00 | activo |
| South Florida Beverage Distributors | bebidas | 40.00 | activo |
| Tropical Drinks Supply | bebidas | 38.50 | activo |
| EcoPackaging Miami | packaging_embalajes | 30.00 | activo |
| Commercial Cleaning Supplies FL | productos_limpieza | 25.00 | activo |
| Global Food Supply International | multi-categoría | 45.00 | suspendido |

---

## 🔧 Troubleshooting

### Error: `ModuleNotFoundError: No module named 'tinydb'`

```bash
# Activar venv y reinstalar
cd services/api
source venv/bin/activate
pip install -r requirements.txt
```

### Error: `401 Unauthorized`

```bash
# Verificar token válido
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@brasaland.com&password=admin123"

# Usar token en header
-H "Authorization: Bearer <access_token>"
```

### Error: `422 Unprocessable Entity`

Validación Pydantic falló. Verificar:
- ✅ `delivery_rate_usd > 0`
- ✅ `status` ∈ {activo, suspendido}
- ✅ `country` ∈ {Colombia, USA}
- ✅ `categories` no vacía
- ✅ Campos requeridos presentes

### Seeder duplica registros

```bash
# El seeder es idempotente, verificar output:
python seed.py

# Si reporta "Skipped: 20", está funcionando correctamente
# Si reporta "Inserted: 20", verifica que la BD esté vacía antes
```

---

## 📚 Documentación Adicional

- **OpenAPI Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Auditoría Completa**: [`SUPPLIER_MANAGEMENT_AUDIT_REPORT.md`](../../SUPPLIER_MANAGEMENT_AUDIT_REPORT.md)
- **Schemas Pydantic**: [`app/schemas/supplier.py`](app/schemas/supplier.py)
- **Service Layer**: [`app/services/supplier_service.py`](app/services/supplier_service.py)
- **Router**: [`app/routers/suppliers.py`](app/routers/suppliers.py)

---

## ✅ Checklist de Producción

Antes de deploy a producción:

- [ ] Generar secretos seguros (`SECRET_KEY`, `RESET_TOKEN_SECRET_KEY`)
- [ ] Configurar CORS de producción en `.env`
- [ ] Ejecutar seeder en BD de producción
- [ ] Configurar rate limiting (opcional)
- [ ] Configurar logging a archivo
- [ ] Setup de backups de TinyDB (`users_db.json`)
- [ ] Configurar HTTPS/TLS
- [ ] Implementar monitoreo (health checks)

---

**Versión API**: 1.0.0  
**Última actualización**: 2026-11-18  
**Contacto**: nicolas.park@brasaland.com (CTO)
