# 🍖 Sistema de Inventario - Brasaland

## 📋 Descripción

Sistema centralizado de gestión de inventario de ingredientes (materia prima) para los 14 restaurantes de Brasaland.

**Usuario principal**: Felipe Guerrero (Operaciones)  
**Problema resuelto**: Eliminar pedidos de materia prima por WhatsApp, visibilidad en tiempo real de stock por sede.

---

## 🏗️ Arquitectura de Doble Base de Datos

El sistema implementa una **arquitectura de doble base de datos simultánea**:

| Base de Datos | Propósito | Tecnología | Ubicación |
|---------------|-----------|------------|-----------|
| **TinyDB** | Usuarios y autenticación | JSON file-based | `users_db.json` |
| **Supabase** | Datos de negocio (inventario) | PostgreSQL | Cloud (Supabase) |

### ¿Por qué Doble BD?

1. **Separación de responsabilidades**: Auth (TinyDB) vs Business Data (Supabase)
2. **Escalabilidad**: Supabase soporta crecimiento de datos de inventario
3. **Integridad referencial**: FK relacionales en Supabase para inventario
4. **No duplicación**: Users NO se replica en Supabase, solo `user_uuid` como string

---

## 🔐 Reglas de Negocio CRÍTICAS

### 1. Stock es CALCULADO, nunca editable

**Fórmula**:
```
current_stock = SUM(inbound_orders.quantity) - SUM(outbound_orders.quantity)
```

❌ **PROHIBIDO**: Editar stock directamente  
✅ **CORRECTO**: Crear InboundOrder (incrementa) o OutboundOrder (decrementa)

### 2. Stock NO puede ser negativo

Antes de crear un `OutboundOrder`, el sistema valida:

```python
if current_stock < requested_quantity:
    raise HTTP 400  # Rechaza orden
```

### 3. Trazabilidad por Usuario

Cada orden (`InboundOrder` y `OutboundOrder`) asocia el `user_uuid` del usuario autenticado proveniente de TinyDB.

**Importante**: `user_uuid` es un string (referencia lógica), NO un Foreign Key relacional.

### 4. Stock Inicial = 0

Un ingrediente nuevo inicia con stock cero y solo acumula existencias a través de `InboundOrder`.

### 5. Partición por Almacén

Stock se gestiona por `warehouse` (sede/almacén):
- `medellin_centro`, `bogota_zona_rosa`, `miami_beach`, etc.
- Permite saber exactamente cuánto hay en cada restaurante

---

## 📊 Modelos de Datos

### Ingredient (Ingrediente)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int | Primary Key |
| `name` | str | Nombre del ingrediente |
| `sku` | str | Código único (UNIQUE) |
| `description` | str | Descripción opcional |
| `unit` | enum | Unidad de medida (kg, l, unit, etc.) |
| `min_stock` | float | Nivel mínimo de alerta |
| `reorder_point` | float | Punto de reorden |
| `created_at` | datetime | Timestamp de creación |
| `updated_at` | datetime | Timestamp de actualización |

**IMPORTANTE**: NO tiene campo `current_stock` - se calcula dinámicamente.

### InboundOrder (Orden de Entrada)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int | Primary Key |
| `ingredient_id` | int | FK a Ingredient |
| `quantity` | float | Cantidad de entrada (> 0) |
| `warehouse` | enum | Almacén destino |
| `user_uuid` | str | Usuario que registró (TinyDB) |
| `notes` | str | Notas opcionales |
| `created_at` | datetime | Timestamp |

**Efecto**: Incrementa stock disponible

### OutboundOrder (Orden de Salida)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int | Primary Key |
| `ingredient_id` | int | FK a Ingredient |
| `quantity` | float | Cantidad de salida (> 0) |
| `warehouse` | enum | Almacén origen |
| `user_uuid` | str | Usuario que registró (TinyDB) |
| `reason` | str | Motivo (cocina, merma, etc.) |
| `created_at` | datetime | Timestamp |

**Efecto**: Decrementa stock disponible  
**Validación**: Rechaza si causa stock negativo

---

## 🚀 API Endpoints

### Ingredientes

#### `POST /inventory/ingredients`
Crear un nuevo ingrediente.

**Requiere**: JWT  
**Body**:
```json
{
  "name": "Carne de res (churrasco)",
  "sku": "CARNE-RES-001",
  "description": "Corte de res para churrasco a la brasa",
  "unit": "kg",
  "min_stock": 50.0,
  "reorder_point": 100.0
}
```

**Response**: `201 Created`
```json
{
  "id": 1,
  "name": "Carne de res (churrasco)",
  "sku": "CARNE-RES-001",
  "unit": "kg",
  "current_stock": 0.0,  // Siempre 0 para nuevo ingrediente
  "stock_by_warehouse": {}
}
```

---

#### `GET /inventory/ingredients`
Listar ingredientes con stock calculado.

**Requiere**: JWT  
**Query Params**:
- `skip=0`: Offset de paginación
- `limit=100`: Límite de resultados
- `warehouse=medellin_poblado`: Filtrar por almacén

**Response**: `200 OK`
```json
[
  {
    "id": 1,
    "name": "Carne de res (churrasco)",
    "sku": "CARNE-RES-001",
    "unit": "kg",
    "current_stock": 123.0,  // Calculado dinámicamente
    "stock_by_warehouse": {
      "medellin_poblado": 25.0,
      "bogota_zona_rosa": 40.0,
      "miami_beach": 58.0
    },
    "min_stock": 50.0,
    "reorder_point": 100.0
  }
]
```

---

#### `GET /inventory/ingredients/{id}`
Obtener ingrediente específico con stock.

**Requiere**: JWT  
**Response**: `200 OK` (mismo formato que lista)

---

#### `PUT /inventory/ingredients/{id}`
Actualizar datos de ingrediente (NO afecta stock).

**Requiere**: JWT  
**Body**:
```json
{
  "name": "Nuevo nombre",
  "min_stock": 60.0
}
```

**IMPORTANTE**: Stock NO es actualizable aquí, solo mediante órdenes.

---

### Órdenes de Entrada

#### `POST /inventory/orders/inbound`
Registrar entrada de stock (llegada de materia prima).

**Requiere**: JWT  
**Body**:
```json
{
  "ingredient_id": 1,
  "quantity": 100.0,
  "warehouse": "medellin_poblado",
  "notes": "Proveedor principal - Carne Argentina"
}
```

**Response**: `201 Created`
```json
{
  "id": 1,
  "ingredient_id": 1,
  "quantity": 100.0,
  "warehouse": "medellin_poblado",
  "user_uuid": "1",  // Automático del JWT
  "notes": "Proveedor principal",
  "created_at": "2026-10-28T10:00:00Z",
  "ingredient_name": "Carne de res (churrasco)",
  "ingredient_sku": "CARNE-RES-001"
}
```

**Efecto**: Stock de "Carne de res" en "medellin_poblado" aumenta en 100.0 kg

---

### Órdenes de Salida

#### `POST /inventory/orders/outbound`
Registrar salida de stock (uso en cocina, merma).

**Requiere**: JWT  
**Body**:
```json
{
  "ingredient_id": 1,
  "quantity": 25.0,
  "warehouse": "medellin_poblado",
  "reason": "Uso en cocina - Servicio del día"
}
```

**Response**: `201 Created` o `400 Bad Request`

**Validación Crítica**:
```json
// Si stock actual = 20.0 y se solicita 25.0
{
  "detail": "Insufficient stock for 'Carne de res' in medellin_poblado. Available: 20.0 kg, Requested: 25.0 kg"
}
```

---

### Listado de Órdenes

#### `GET /inventory/orders`
Listar todas las órdenes (inbound + outbound).

**Requiere**: JWT  
**Query Params**:
- `order_type=inbound|outbound`: Filtrar por tipo
- `ingredient_id=1`: Filtrar por ingrediente
- `warehouse=miami_beach`: Filtrar por almacén

**Response**: `200 OK`
```json
[
  {
    "id": 1,
    "type": "inbound",
    "ingredient_id": 1,
    "ingredient_name": "Carne de res",
    "quantity": 100.0,
    "warehouse": "medellin_poblado",
    "user_uuid": "1",
    "notes_or_reason": "Proveedor principal",
    "created_at": "2026-10-28T10:00:00Z"
  },
  {
    "id": 2,
    "type": "outbound",
    "ingredient_id": 1,
    "ingredient_name": "Carne de res",
    "quantity": 25.0,
    "warehouse": "medellin_poblado",
    "user_uuid": "1",
    "notes_or_reason": "Uso en cocina",
    "created_at": "2026-10-28T15:00:00Z"
  }
]
```

---

### Reporte de Stock

#### `GET /inventory/stock-report`
Generar reporte completo de stock.

**Requiere**: JWT  
**Query Params**:
- `low_stock_only=true`: Solo ingredientes con stock < reorder_point

**Response**: `200 OK`
```json
{
  "total_ingredients": 17,
  "low_stock_count": 3,
  "items": [
    {
      "ingredient_id": 1,
      "ingredient_name": "Carne de res (churrasco)",
      "ingredient_sku": "CARNE-RES-001",
      "unit": "kg",
      "current_stock": 75.0,
      "min_stock": 50.0,
      "reorder_point": 100.0,
      "needs_reorder": true,  // stock < reorder_point
      "stock_by_warehouse": {
        "medellin_poblado": 25.0,
        "bogota_zona_rosa": 20.0,
        "miami_beach": 30.0
      }
    }
  ],
  "generated_at": "2026-10-28T16:00:00Z"
}
```

---

## ⚙️ Setup e Instalación

### 1. Instalar Dependencias

```bash
cd services/api
source venv/bin/activate
pip install sqlmodel
```

### 2. Configurar Supabase

Crear archivo `.env` (copiar de `.env.example`):

```bash
cp .env.example .env
```

Editar `.env`:
```env
SUPABASE_DATABASE_URL=postgresql://postgres.lpmnfgqkvtbmhdchsyla:[YOUR-PASSWORD]@aws-0-eu-west-1.pooler.supabase.com:6543/postgres
```

**Reemplazar `[YOUR-PASSWORD]`** con la contraseña real de Supabase.

### 3. Inicializar Base de Datos

El sistema crea tablas automáticamente al iniciar la aplicación (ver `main.py`).

Alternativamente, ejecutar el seed:

```bash
cd services/api
python scripts/seed_inventory.py
```

Esto crea:
- 17 ingredientes (carnes, vegetales, especias, bebidas)
- Órdenes de entrada (llegadas de materia prima)
- Órdenes de salida (consumo en cocina)

### 4. Iniciar Servidor

```bash
cd services/api
uvicorn app.main:app --reload --port 8000
```

### 5. Acceder a la API

- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## 🔒 Autenticación

Todos los endpoints de `/inventory` requieren autenticación JWT.

### 1. Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@brasaland.com",
    "password": "admin123"
  }'
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Usar Token

```bash
export TOKEN="<access_token>"

curl "http://localhost:8000/inventory/ingredients" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📁 Estructura de Archivos

```
services/api/
├── app/
│   ├── database_supabase.py          # Config Supabase (nuevo)
│   ├── tinydb_database.py            # Config TinyDB (existente)
│   ├── models/
│   │   └── inventory.py              # ORM Models (Ingredient, InboundOrder, OutboundOrder)
│   ├── schemas/
│   │   └── inventory.py              # Pydantic Schemas (desacoplados)
│   ├── routers/
│   │   └── inventory.py              # Endpoints /inventory
│   └── main.py                       # Registro de router + init_db
├── scripts/
│   └── seed_inventory.py             # Script de datos semilla
├── .env.example                      # Template de configuración
└── INVENTORY_SYSTEM.md               # Esta documentación
```

---

## 🧪 Testing Manual

### Ejemplo: Flujo Completo

```bash
# 1. Login
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@brasaland.com", "password": "admin123"}' \
  | jq -r '.access_token' > token.txt

export TOKEN=$(cat token.txt)

# 2. Crear ingrediente
curl -X POST "http://localhost:8000/inventory/ingredients" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sal marina",
    "sku": "SAL-001",
    "unit": "kg",
    "min_stock": 10.0,
    "reorder_point": 20.0
  }'

# 3. Registrar entrada (stock pasa de 0 a 50)
curl -X POST "http://localhost:8000/inventory/orders/inbound" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": 1,
    "quantity": 50.0,
    "warehouse": "medellin_poblado",
    "notes": "Pedido inicial"
  }'

# 4. Registrar salida (stock pasa de 50 a 40)
curl -X POST "http://localhost:8000/inventory/orders/outbound" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": 1,
    "quantity": 10.0,
    "warehouse": "medellin_poblado",
    "reason": "Uso en cocina"
  }'

# 5. Consultar stock actual (debería ser 40.0)
curl "http://localhost:8000/inventory/ingredients/1" \
  -H "Authorization: Bearer $TOKEN"

# 6. Intentar salida que cause stock negativo (debería fallar)
curl -X POST "http://localhost:8000/inventory/orders/outbound" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": 1,
    "quantity": 100.0,
    "warehouse": "medellin_poblado",
    "reason": "Test"
  }'
# Esperado: HTTP 400 "Insufficient stock"
```

---

## 🎯 Casos de Uso

### 1. Consultar Stock Bajo en un Almacén

```bash
curl "http://localhost:8000/inventory/stock-report?low_stock_only=true" \
  -H "Authorization: Bearer $TOKEN"
```

### 2. Ver Historial de un Ingrediente

```bash
curl "http://localhost:8000/inventory/orders?ingredient_id=1" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Stock por Almacén Específico

```bash
curl "http://localhost:8000/inventory/ingredients?warehouse=miami_beach" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🚨 Troubleshooting

### Error: "Database connection failed"

**Causa**: Credenciales de Supabase incorrectas  
**Solución**: Verificar `SUPABASE_DATABASE_URL` en `.env`

### Error: "Insufficient stock"

**Causa**: Intentando crear OutboundOrder que causa stock negativo  
**Solución**: Registrar InboundOrder primero o reducir quantity

### Error: "Ingredient with SKU 'XXX' already exists"

**Causa**: SKU duplicado  
**Solución**: Usar SKU único o actualizar ingrediente existente

---

## 📚 Referencias

- **Supabase Docs**: https://supabase.com/docs
- **SQLModel**: https://sqlmodel.tiangolo.com/
- **FastAPI**: https://fastapi.tiangolo.com/

---

**Versión**: 1.0  
**Fecha**: 28 de octubre, 2026  
**Equipo**: Brasaland Digital - Nicolás Park (CTO)
