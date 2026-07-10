# Propuesta de Arquitectura Backend - Brasaland (FastAPI + Pydantic)

## 1. Visión General

Esta propuesta define la arquitectura backend para Brasaland usando **FastAPI** como framework web y **Pydantic** para validación de datos. La arquitectura está diseñada para:

- Manejar operaciones distribuidas en 2 países (Colombia y Florida)
- Proveer APIs para múltiples aplicaciones (Web, Mobile, Dashboards)
- Soportar agentes IA integrados
- Escalar a 14+ locales con datos en tiempo real
- Mantener consistencia de datos entre mercados

---

## 2. Estructura de Carpetas

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                        # Punto de entrada FastAPI
│   ├── config.py                      # Configuración (dev, prod, test)
│   ├── constants.py                   # Constantes globales (monedas, países)
│   │
│   ├── api/                           # Rutas y endpoints
│   │   ├── __init__.py
│   │   ├── v1/                        # Versionado de API
│   │   │   ├── __init__.py
│   │   │   ├── restaurants/           # Endpoints de locales
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py         # Pydantic models
│   │   │   │   └── service.py         # Lógica de negocio
│   │   │   ├── sales/                 # Endpoints de ventas
│   │   │   ├── inventory/             # Endpoints de inventario
│   │   │   ├── suppliers/             # Endpoints de proveedores
│   │   │   ├── customers/             # Endpoints de clientes
│   │   │   ├── employees/             # Endpoints de empleados
│   │   │   ├── menu/                  # Endpoints de menú
│   │   │   ├── orders/                # Endpoints de pedidos
│   │   │   ├── analytics/             # Endpoints de análisis
│   │   │   └── health/                # Health check
│   │   └── dependencies.py            # Dependencias compartidas
│   │
│   ├── core/                          # Funcionalidades centrales
│   │   ├── __init__.py
│   │   ├── auth.py                    # Autenticación y autorización
│   │   ├── cache.py                   # Caché (Redis)
│   │   ├── database.py                # Configuración de BD
│   │   ├── errors.py                  # Excepciones personalizadas
│   │   └── logging.py                 # Logging y telemetría
│   │
│   ├── models/                        # Modelos SQLAlchemy
│   │   ├── __init__.py
│   │   ├── base.py                    # Clase base para modelos
│   │   ├── restaurant.py
│   │   ├── sale.py
│   │   ├── inventory.py
│   │   ├── supplier.py
│   │   ├── customer.py
│   │   ├── employee.py
│   │   └── audit.py                   # Auditoría y logs
│   │
│   ├── schemas/                       # Modelos Pydantic (validación)
│   │   ├── __init__.py
│   │   ├── base.py                    # Esquema base
│   │   ├── restaurant.py
│   │   ├── sale.py
│   │   ├── inventory.py
│   │   ├── supplier.py
│   │   ├── customer.py
│   │   ├── employee.py
│   │   └── pagination.py
│   │
│   ├── services/                      # Lógica de negocio
│   │   ├── __init__.py
│   │   ├── restaurant_service.py
│   │   ├── sales_service.py
│   │   ├── inventory_service.py
│   │   ├── supplier_service.py
│   │   ├── customer_service.py
│   │   ├── employee_service.py
│   │   ├── analytics_service.py
│   │   └── ai_service.py              # Integración con agentes IA
│   │
│   ├── repositories/                  # Data Access Layer (DAL)
│   │   ├── __init__.py
│   │   ├── base.py                    # Repositorio genérico
│   │   ├── restaurant_repo.py
│   │   ├── sale_repo.py
│   │   ├── inventory_repo.py
│   │   └── ... (uno por entidad)
│   │
│   ├── websockets/                    # Real-time (WebSocket)
│   │   ├── __init__.py
│   │   ├── connection_manager.py
│   │   ├── handlers.py
│   │   └── rooms.py                   # Salas (por local, región, etc)
│   │
│   ├── utils/                         # Utilidades
│   │   ├── __init__.py
│   │   ├── currency.py                # Conversión USD/COP
│   │   ├── datetime.py                # Manejo de timezone
│   │   ├── validators.py              # Validadores personalizados
│   │   └── helpers.py
│   │
│   └── background_tasks/              # Tareas asincrónicas
│       ├── __init__.py
│       ├── worker.py                  # Celery/RQ worker
│       ├── sales_sync.py              # Sincronizar ventas
│       ├── inventory_alerts.py        # Alertas de inventario
│       └── daily_reports.py           # Reportes automáticos
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/
│   ├── test_services/
│   ├── test_repositories/
│   └── fixtures/
│
├── migrations/                        # Alembic (versionado de BD)
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── requirements.txt
├── .env.example
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 3. Stack Tecnológico

| Componente | Tecnología | Propósito |
|---|---|---|
| **Framework Web** | FastAPI | API REST asincrónica |
| **Validación** | Pydantic v2 | Validación de datos y serialización |
| **ORM** | SQLAlchemy 2.0 | Mapeo objeto-relacional |
| **Base de Datos** | PostgreSQL | BD principal |
| **Caché** | Redis | Caché y sesiones |
| **Real-time** | WebSockets | Conexiones bidireccionales |
| **Tareas Asincrónicas** | Celery + Redis | Task queue |
| **Testing** | pytest | Framework de testing |
| **Deployment** | Docker | Containerización |

---

## 4. Patrones de Diseño

### 4.1 Estructura por módulo

Cada módulo de negocio (restaurants, sales, etc.) sigue este patrón:

```
modulo/
├── router.py          # Rutas HTTP (FastAPI)
├── schemas.py         # Validación Pydantic
├── service.py         # Lógica de negocio
└── repository.py      # Acceso a datos
```

### 4.2 Flujo de una solicitud

```
HTTP Request
    ↓
Router (validación básica + autenticación)
    ↓
Schemas Pydantic (validación de datos)
    ↓
Service (lógica de negocio)
    ↓
Repository (acceso a datos)
    ↓
SQLAlchemy Models (base de datos)
    ↓
Response JSON
```

### 4.3 Ejemplo: Crear un restaurante

**router.py**
```python
from fastapi import APIRouter, Depends, status
from . import schemas, service
from app.core.auth import get_current_user

router = APIRouter(prefix="/restaurants", tags=["restaurants"])

@router.post("/", response_model=schemas.RestaurantResponse, status_code=status.HTTP_201_CREATED)
async def create_restaurant(
    restaurant_in: schemas.RestaurantCreate,
    current_user = Depends(get_current_user),
    svc: service.RestaurantService = Depends()
):
    return await svc.create_restaurant(restaurant_in, current_user)
```

**schemas.py**
```python
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import datetime
from typing import Optional

class CountryEnum(str, Enum):
    COLOMBIA = "CO"
    USA = "US"

class RestaurantCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    country: CountryEnum
    city: str
    address: str
    phone: str = Field(..., pattern=r"^\+?[\d\s\-()]+$")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

class RestaurantResponse(BaseModel):
    id: int
    name: str
    country: CountryEnum
    city: str
    created_at: datetime
    
    model_config = {"from_attributes": True}
```

**service.py**
```python
from app.models.restaurant import Restaurant
from app.repositories.base import BaseRepository
from . import schemas

class RestaurantService:
    def __init__(self, repo: BaseRepository = Depends()):
        self.repo = repo
    
    async def create_restaurant(self, restaurant_in: schemas.RestaurantCreate, user):
        # Validaciones de negocio
        existing = await self.repo.get_by_field("Restaurant", "phone", restaurant_in.phone)
        if existing:
            raise ValueError("Este teléfono ya está registrado")
        
        restaurant = Restaurant(**restaurant_in.model_dump())
        restaurant.created_by_id = user.id
        await self.repo.create(restaurant)
        return restaurant
```

---

## 5. Modelos Pydantic

### 5.1 Base compartida

```python
# schemas/base.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class TimestampedSchema(BaseSchema):
    created_at: datetime
    updated_at: Optional[datetime] = None

class IdSchema(TimestampedSchema):
    id: int
```

### 5.2 Por dominio

**Sales**
```python
class SaleItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = Field(..., ge=1)
    price: float = Field(..., gt=0)

class SaleCreate(BaseModel):
    restaurant_id: int
    customer_id: Optional[int] = None
    items: list[SaleItemCreate]
    payment_method: str
    total_amount: float
    currency: str

class SaleResponse(IdSchema):
    restaurant_id: int
    total_amount: float
    currency: str
    status: str
```

**Inventory**
```python
class InventoryItemCreate(BaseModel):
    supplier_id: int
    product_name: str
    quantity: float
    unit: str
    expiration_date: Optional[date] = None
    cost: float

class InventoryResponse(IdSchema):
    product_name: str
    quantity: float
    unit: str
```

**Employees**
```python
class EmployeeCreate(BaseModel):
    first_name: str = Field(..., min_length=2)
    last_name: str = Field(..., min_length=2)
    email: EmailStr
    phone: str
    position: str
    restaurant_id: int
    country: str
    hire_date: date
    salary: float

class EmployeeResponse(IdSchema):
    first_name: str
    last_name: str
    email: str
    position: str
    status: str
```

---

## 6. Configuración y Variables de Entorno

### 6.1 Estructura de archivos .env

```
.env                  # Variables locales (NO commitear a git)
.env.example          # Plantilla para documentar variables (sí commitear)
.env.local            # Overrides locales opcionales (NO commitear)
.env.development      # Variables de desarrollo
.env.staging          # Variables de staging
.env.production       # Variables de producción (usando secrets manager)
```

### 6.2 Archivo .env.example (plantilla - COMMITEADO a git)

```bash
# ============================================
# BRASALAND API - Variables de Entorno
# ============================================
# Copia este archivo a .env y rellena los valores
# NUNCA commitees .env con valores reales
# ============================================

# BASE
DEBUG=True
ENVIRONMENT=development
PROJECT_NAME=Brasaland API
VERSION=1.0.0

# DATABASE - PostgreSQL
DATABASE_URL=postgresql://brasaland:password@localhost:5432/brasaland
DATABASE_ECHO=True
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_PRE_PING=true

# REDIS - Caché y sesiones
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600

# SECURITY - JWT y autenticación
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS - Orígenes permitidos
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080

# EMAIL - SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM=noreply@brasaland.com
SMTP_TLS=true

# AWS - S3 para archivos (opcional)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=brasaland-files
AWS_REGION=us-east-1

# CURRENCY - Configuración de monedas
DEFAULT_CURRENCY=COP
SUPPORTED_CURRENCIES=COP,USD
EXCHANGE_RATE_API_KEY=your-api-key

# TIMEZONE
TIMEZONE=America/Bogota

# CELERY - Tareas asincrónicas
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# LOGGING
LOG_LEVEL=INFO
LOG_FORMAT=json

# FEATURE FLAGS
ENABLE_AI_FEATURES=true
ENABLE_WEBHOOKS=false
ENABLE_ANALYTICS=true
```

### 6.3 Archivo .env para desarrollo (.env - NO commitear)

**Ejemplo para desarrollo local:**

```bash
# BASE
DEBUG=True
ENVIRONMENT=development
PROJECT_NAME=Brasaland API
VERSION=1.0.0

# DATABASE
DATABASE_URL=postgresql://brasaland:password@localhost:5432/brasaland
DATABASE_ECHO=True
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_PRE_PING=true

# REDIS
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600

# SECURITY
SECRET_KEY=dev-secret-key-change-in-production-min-32-characters-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080

# EMAIL
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail@gmail.com
SMTP_PASSWORD=your-app-password-16-chars
SMTP_FROM=noreply@brasaland.dev
SMTP_TLS=true

# AWS (opcional para dev)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=

# CURRENCY
DEFAULT_CURRENCY=COP
SUPPORTED_CURRENCIES=COP,USD

# TIMEZONE
TIMEZONE=America/Bogota

# CELERY
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# LOGGING
LOG_LEVEL=DEBUG
LOG_FORMAT=json

# FEATURE FLAGS
ENABLE_AI_FEATURES=true
ENABLE_WEBHOOKS=false
ENABLE_ANALYTICS=true
```

### 6.4 Archivo .gitignore

**Asegúrate de agregar esto a .gitignore:**

```bash
# Archivos de entorno (NUNCA commitear)
.env
.env.local
.env.*.local

# Variables secretas
.env.production
.env.staging

# Cache y temporales
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/

# Otros
.vscode/
.idea/
*.log
*.egg-info/
dist/
build/
venv/
```

### 6.5 Clase Settings (config.py)

```python
from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # ============ BASE ============
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    PROJECT_NAME: str = "Brasaland API"
    VERSION: str = "1.0.0"
    
    # ============ DATABASE ============
    DATABASE_URL: str
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_PRE_PING: bool = True
    
    # ============ REDIS ============
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600
    
    # ============ SECURITY ============
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ============ CORS ============
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # ============ EMAIL ============
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "noreply@brasaland.com"
    SMTP_TLS: bool = True
    
    # ============ AWS S3 ============
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    # ============ CURRENCY ============
    DEFAULT_CURRENCY: str = "COP"
    SUPPORTED_CURRENCIES: List[str] = ["COP", "USD"]
    EXCHANGE_RATE_API_KEY: Optional[str] = None
    
    # ============ TIMEZONE ============
    TIMEZONE: str = "America/Bogota"
    
    # ============ CELERY ============
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    
    # ============ LOGGING ============
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json o text
    
    # ============ FEATURE FLAGS ============
    ENABLE_AI_FEATURES: bool = True
    ENABLE_WEBHOOKS: bool = False
    ENABLE_ANALYTICS: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()
```

### 6.6 Validación de variables de entorno

**Crear archivo app/core/config_validator.py:**

```python
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def validate_settings():
    """Valida que todas las variables críticas estén configuradas"""
    
    errors = []
    
    # Variables requeridas
    required_vars = {
        "DATABASE_URL": settings.DATABASE_URL,
        "SECRET_KEY": settings.SECRET_KEY,
        "REDIS_URL": settings.REDIS_URL,
    }
    
    for var_name, value in required_vars.items():
        if not value:
            errors.append(f"Variable {var_name} es requerida")
    
    # Validaciones específicas
    if len(settings.SECRET_KEY) < 32 and settings.ENVIRONMENT == "production":
        errors.append("SECRET_KEY debe tener al menos 32 caracteres en producción")
    
    if not settings.DEBUG and settings.ENVIRONMENT == "production":
        logger.warning("DEBUG=True detectado en PRODUCCIÓN")
    
    if settings.ENVIRONMENT not in ["development", "staging", "production"]:
        errors.append(f"ENVIRONMENT inválido: {settings.ENVIRONMENT}")
    
    if errors:
        for error in errors:
            logger.error(f"❌ {error}")
        raise ValueError(f"Configuración inválida: {', '.join(errors)}")
    
    logger.info(f"✅ Configuración validada para {settings.ENVIRONMENT}")
```

**Llamar en main.py:**

```python
from app.core.config_validator import validate_settings

@app.on_event("startup")
async def startup():
    validate_settings()
    logger.info("Aplicación iniciada")
```

### 6.7 Cómo configurar los entornos

#### Desarrollo Local

1. **Copiar archivo ejemplo:**
```bash
cp .env.example .env
```

2. **Editar .env con valores locales:**
```bash
DEBUG=True
ENVIRONMENT=development
DATABASE_URL=postgresql://brasaland:password@localhost:5432/brasaland
SECRET_KEY=dev-secret-key-min-32-chars-here-1234567890ab
REDIS_URL=redis://localhost:6379/0
```

3. **Levantar servicios:**
```bash
docker-compose up -d postgres redis
```

4. **Crear base de datos:**
```bash
psql postgresql://brasaland:password@localhost:5432 -c "CREATE DATABASE brasaland;"
```

#### Staging

**Variables en .env.staging (NO commitear):**
```bash
DEBUG=False
ENVIRONMENT=staging
DATABASE_URL=postgresql://user:password@staging-db.example.com:5432/brasaland_staging
SECRET_KEY=staging-secret-key-min-32-chars-XXXXXXXXXXXXXX
REDIS_URL=redis://staging-redis.example.com:6379/0
ALLOWED_ORIGINS=https://staging.brasaland.com
```

**Iniciar con:**
```bash
python -m dotenv -f .env.staging run uvicorn app.main:app
```

#### Producción

**NO usar archivos .env en producción. Usar:**
- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault
- Variables de entorno del sistema

**Ejemplo con Docker:**
```bash
docker run \
  -e DATABASE_URL="postgresql://..." \
  -e SECRET_KEY="prod-secret-key" \
  -e REDIS_URL="redis://..." \
  -e ENVIRONMENT="production" \
  brasaland-api:latest
```

**Ejemplo con Kubernetes:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: brasaland-config
data:
  ENVIRONMENT: production
  LOG_LEVEL: INFO

---
apiVersion: v1
kind: Secret
metadata:
  name: brasaland-secrets
type: Opaque
stringData:
  DATABASE_URL: postgresql://...
  SECRET_KEY: prod-secret-key-min-32-chars
  REDIS_URL: redis://...

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: brasaland-api
spec:
  template:
    spec:
      containers:
      - name: api
        image: brasaland-api:latest
        envFrom:
        - configMapRef:
            name: brasaland-config
        - secretRef:
            name: brasaland-secrets
```

### 6.8 Script de setup para desarrollo

**Crear archivo setup-env.sh:**

```bash
#!/bin/bash

echo "🚀 Configurando Brasaland API - Entorno de Desarrollo"
echo ""

# Validar si existe .env
if [ -f .env ]; then
    echo "✅ Archivo .env encontrado"
else
    echo "📋 Creando .env desde .env.example..."
    cp .env.example .env
    echo "⚠️  Por favor edita .env con tus valores locales"
    exit 1
fi

# Crear venv si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar venv
source venv/bin/activate

# Instalar dependencias
echo "📥 Instalando dependencias..."
pip install -r requirements.txt

# Crear base de datos
echo "🗄️  Inicializando base de datos..."
alembic upgrade head

# Crear usuario admin (opcional)
echo "👤 Crear usuario admin? (s/n)"
read -r create_admin
if [ "$create_admin" = "s" ]; then
    python -c "
from app.core.security import get_password_hash
from app.models import User
from app.core.database import SessionLocal

db = SessionLocal()
user = User(
    email='admin@brasaland.local',
    hashed_password=get_password_hash('password'),
    role='super_admin'
)
db.add(user)
db.commit()
print('✅ Usuario admin creado: admin@brasaland.local / password')
"
fi

echo ""
echo "✅ Setup completado!"
echo ""
echo "Para iniciar:"
echo "  uvicorn app.main:app --reload"
```

**Usar:**
```bash
chmod +x setup-env.sh
./setup-env.sh
```

### 6.9 Checklist de configuración

- [ ] `.env.example` creado con todas las variables
- [ ] `.env` agregado a `.gitignore`
- [ ] Validation de settings en `app/core/config_validator.py`
- [ ] Variables requeridas documentadas
- [ ] Script de setup para desarrollo creado
- [ ] Instrucciones de staging configuradas
- [ ] Plan de secrets para producción definido
- [ ] Tests con variables de entorno configurados
- [ ] Docker compose con valores de desarrollo
- [ ] Documentación en README actualizada

---

## 7. Estructura de Base de Datos

### 7.1 Tablas principales

```sql
CREATE TABLE restaurants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(2) NOT NULL,
    city VARCHAR(255),
    address TEXT,
    phone VARCHAR(20),
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    customer_id INTEGER REFERENCES customers(id),
    total_amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'COP',
    status VARCHAR(20) DEFAULT 'completed',
    payment_method VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sale_items (
    id SERIAL PRIMARY KEY,
    sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    menu_item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL
);

CREATE TABLE inventory (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    product_name VARCHAR(255) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    unit VARCHAR(50),
    expiration_date DATE,
    cost DECIMAL(10,2),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    position VARCHAR(50),
    country VARCHAR(2),
    hire_date DATE,
    salary DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    loyalty_points INTEGER DEFAULT 0,
    country VARCHAR(2),
    preferred_restaurant_id INTEGER REFERENCES restaurants(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    country VARCHAR(2),
    contact_person VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(20),
    payment_terms VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 7.2 Índices para rendimiento

```sql
CREATE INDEX idx_sales_restaurant_date 
    ON sales(restaurant_id, created_at DESC);

CREATE INDEX idx_inventory_restaurant_id 
    ON inventory(restaurant_id);

CREATE INDEX idx_employees_restaurant_id 
    ON employees(restaurant_id);

CREATE INDEX idx_customers_email 
    ON customers(email);
```

---

## 8. Endpoints API (v1)

### 8.1 Restaurants
```
GET    /api/v1/restaurants               # Listar con paginación
GET    /api/v1/restaurants/{id}          # Obtener uno
POST   /api/v1/restaurants               # Crear
PUT    /api/v1/restaurants/{id}          # Actualizar
DELETE /api/v1/restaurants/{id}          # Soft delete
GET    /api/v1/restaurants/{id}/stats    # Estadísticas
```

### 8.2 Sales
```
GET    /api/v1/sales                     # Listar
GET    /api/v1/sales/{id}                # Obtener
POST   /api/v1/sales                     # Crear venta
GET    /api/v1/sales/range               # Por rango de fechas
GET    /api/v1/sales/analytics           # Análisis
```

### 8.3 Inventory
```
GET    /api/v1/inventory                 # Listar
POST   /api/v1/inventory                 # Agregar item
PUT    /api/v1/inventory/{id}            # Actualizar cantidad
GET    /api/v1/inventory/low-stock       # Items bajo stock
```

### 8.4 Employees
```
GET    /api/v1/employees                 # Listar
POST   /api/v1/employees                 # Crear
GET    /api/v1/employees/{id}            # Obtener
PUT    /api/v1/employees/{id}            # Actualizar
GET    /api/v1/employees/restaurant/{id} # Por restaurante
```

### 8.5 Customers
```
GET    /api/v1/customers                 # Listar
POST   /api/v1/customers                 # Crear
GET    /api/v1/customers/{id}            # Obtener
GET    /api/v1/customers/{id}/history    # Historial
```

### 8.6 Analytics
```
GET    /api/v1/analytics/dashboard       # Dashboard ejecutivo
GET    /api/v1/analytics/revenue         # Ingresos
GET    /api/v1/analytics/inventory-cost  # Costos
GET    /api/v1/analytics/employees-kpi   # KPIs
```

---

## 9. Real-time con WebSockets

### 9.1 Connection Manager

```python
# websockets/connection_manager.py
from fastapi import WebSocket
from typing import Dict, Set

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = set()
        self.active_connections[room].add(websocket)
    
    async def disconnect(self, websocket: WebSocket, room: str):
        self.active_connections[room].discard(websocket)
    
    async def broadcast(self, room: str, message: dict):
        for connection in self.active_connections.get(room, set()):
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()
```

### 9.2 WebSocket Endpoints

```python
# api/v1/ws.py
from fastapi import APIRouter, WebSocket
from app.websockets import manager

router = APIRouter()

@router.websocket("/ws/sales/{restaurant_id}")
async def websocket_sales(websocket: WebSocket, restaurant_id: int):
    room = f"sales_{restaurant_id}"
    await manager.connect(websocket, room)
    try:
        while True:
            data = await websocket.receive_text()
    except:
        await manager.disconnect(websocket, room)

@router.websocket("/ws/inventory/{restaurant_id}")
async def websocket_inventory(websocket: WebSocket, restaurant_id: int):
    room = f"inventory_{restaurant_id}"
    await manager.connect(websocket, room)
    try:
        while True:
            data = await websocket.receive_text()
    except:
        await manager.disconnect(websocket, room)
```

### 9.3 Broadcasting desde servicios

```python
# services/sales_service.py
async def create_sale(self, sale_in: SaleCreate, user):
    sale = await self.repo.create(Sale(**sale_in.model_dump()))
    
    # Notificar a todos los clientes conectados a este local
    await manager.broadcast(
        f"sales_{sale.restaurant_id}",
        {
            "event": "sale_created",
            "sale": sale.__dict__,
            "timestamp": datetime.now().isoformat()
        }
    )
    return sale
```

---

## 10. Autenticación y Autorización

### 10.1 Modelos

```python
# models/user.py
from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum
from enum import Enum

class RoleEnum(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"
    CUSTOMER = "customer"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.STAFF)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    is_active = Column(Boolean, default=True)
```

### 10.2 JWT y dependencias

```python
# core/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from jose import jwt, JWTError
from app.config import settings

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

def require_role(required_role: str):
    async def role_checker(current_user = Depends(get_current_user)):
        if current_user.get("role") != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permisos insuficientes"
            )
        return current_user
    return role_checker
```

---

## 11. Integración con Agentes IA

```python
# services/ai_service.py
class AIService:
    async def get_sales_insight(self, restaurant_id: int, period: str):
        """Genera insights sobre ventas usando IA"""
        sales = await self.sales_repo.get_by_date_range(restaurant_id, period)
        
        insights = await call_agent_api(
            agent_name="sales_analyst",
            data=sales,
            prompt=f"Analiza las ventas del último {period}"
        )
        return insights
    
    async def get_inventory_recommendations(self, restaurant_id: int):
        """Recomendaciones de compra basadas en historial"""
        inventory = await self.inventory_repo.get_by_restaurant(restaurant_id)
        sales_history = await self.sales_repo.get_trends(restaurant_id)
        
        recommendations = await call_agent_api(
            agent_name="inventory_optimizer",
            data={
                "current_inventory": inventory,
                "sales_trends": sales_history
            }
        )
        return recommendations
```

---

## 12. Tareas Asincrónicas

### 12.1 Worker Celery

```python
# background_tasks/worker.py
from celery import Celery
from app.config import settings

celery_app = Celery(
    "brasaland",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

@celery_app.task
def sync_sales_to_analytics(restaurant_id: int):
    """Sincroniza ventas cada hora"""
    pass

@celery_app.task
def check_inventory_alerts():
    """Verifica alertas cada 30 minutos"""
    pass

@celery_app.task
def generate_daily_report():
    """Reporte diario a las 6 AM"""
    pass
```

### 12.2 Scheduled tasks en main.py

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'sync-sales': {
        'task': 'app.background_tasks.sync_sales_to_analytics',
        'schedule': crontab(minute=0),  # Cada hora
    },
    'check-inventory': {
        'task': 'app.background_tasks.check_inventory_alerts',
        'schedule': crontab(minute='*/30'),  # Cada 30 min
    },
    'daily-report': {
        'task': 'app.background_tasks.generate_daily_report',
        'schedule': crontab(hour=6, minute=0),  # 6 AM
    },
}
```

---

## 13. Testing

### 13.1 Configuración (conftest.py)

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

### 13.2 Ejemplo de tests

```python
# tests/test_api/test_restaurants.py
def test_create_restaurant(client, auth_headers):
    response = client.post(
        "/api/v1/restaurants",
        headers=auth_headers,
        json={
            "name": "Brasaland Centro",
            "country": "CO",
            "city": "Medellín",
            "address": "Calle 1 #1",
            "phone": "+573001234567",
            "latitude": 6.2442,
            "longitude": -75.5898
        }
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Brasaland Centro"

def test_get_restaurants(client, auth_headers):
    response = client.get("/api/v1/restaurants", headers=auth_headers)
    assert response.status_code == 200
```

---

## 14. Error Handling

```python
# core/errors.py
class BrasalandException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

class RestaurantNotFound(BrasalandException):
    def __init__(self):
        super().__init__("Restaurante no encontrado", 404)

class InsufficientInventory(BrasalandException):
    def __init__(self, product: str):
        super().__init__(f"Inventario insuficiente para {product}", 400)

# En main.py
@app.exception_handler(BrasalandException)
async def brasaland_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )
```

---

## 15. Logging y Monitoreo

```python
# core/logging.py
import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# En servicios
async def create_sale(self, sale_in: SaleCreate):
    logger.info("Creating sale", extra={
        "restaurant_id": sale_in.restaurant_id,
        "amount": sale_in.total_amount
    })
    try:
        sale = await self.repo.create(Sale(**sale_in.model_dump()))
        logger.info("Sale created", extra={"sale_id": sale.id})
        return sale
    except Exception as e:
        logger.error("Error creating sale", extra={"error": str(e)})
        raise
```

---

## 16. Deployment

### 16.1 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 16.2 Docker Compose

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: brasaland
      POSTGRES_USER: brasaland
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --reload
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://brasaland:password@postgres:5432/brasaland
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - .:/app

volumes:
  postgres_data:
```

---

## 17. Main Application (app/main.py)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1 import restaurants, sales, inventory, employees, customers, suppliers, analytics
from app.core.errors import BrasalandException
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Brasaland API")
    yield
    # Shutdown
    print("Shutting down Brasaland API")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers v1
app.include_router(restaurants.router, prefix="/api/v1")
app.include_router(sales.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(employees.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
app.include_router(suppliers.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")

# Health check
@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}

# Exception handlers
@app.exception_handler(BrasalandException)
async def brasaland_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
```

---

**Propuesta de arquitectura completa y lista para implementación.**
