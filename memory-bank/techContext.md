# Tech Context - Brasaland Monorepo

## Arquitectura del Monorepo

```
/pabloalberdi2000-Company-project/
├── uis/                    # Interfaces de usuario
│   └── backoffice/        # Frontend Next.js (ATS + Incidencias)
├── services/              # Servicios backend
│   └── api/               # Backend FastAPI (ATS + Incidencias)
├── scripts/               # Scripts CLI (analyze.py)
├── docs/                  # Documentación técnica
├── memory-bank/           # Memoria del agente
└── .agents/               # Configuración de agentes
```

## Stack Tecnológico

### Frontend
- **Framework**: Next.js 15.1.0 (App Router, NO Pages Router)
- **Lenguaje**: TypeScript 5 (modo estricto)
- **Styling**: Tailwind CSS 3.4
- **UI Components**: React 19
- **State Management**: React Hooks nativos (useState, useEffect, useRouter, useSearchParams)
- **HTTP Client**: Fetch API nativa
- **Routing**: App Router con carpetas dinámicas `[id]`

**Decisiones clave:**
- Sin librerías externas de estado (Redux, Zustand)
- Client components (`'use client'`) para interactividad
- Server components por defecto para mejor performance
- Uso de `useSearchParams` para filtros en URL
- Navegación con `<Link>` y `useRouter()` sin page reloads

### Backend
- **Framework**: FastAPI 0.110+
- **Lenguaje**: Python 3.9+
- **ORM**: SQLAlchemy 2.0
- **Validación**: Pydantic 2.6+ (schemas)
- **Base de datos**: SQLite (desarrollo), PostgreSQL (producción)
- **ASGI Server**: Uvicorn
- **CORS**: Configurado para localhost:3000

**Decisiones clave:**
- Routers modulares por dominio (candidates, incidents)
- Schemas Pydantic para validación automática
- Services layer para lógica de negocio reutilizable
- Endpoints REST semánticos (GET, POST, PUT, PATCH, DELETE)
- Response models documentados en OpenAPI

### Scripts CLI
- **Lenguaje**: Python 3.7+ (solo stdlib)
- **Argumentos**: argparse
- **Sin dependencias externas** para portabilidad

### Base de Datos

**Schema ATS (Candidatos)**:
```sql
CREATE TABLE candidates (
    id INTEGER PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    position VARCHAR(100) NOT NULL,  -- Cocinero, Mesero, etc.
    country ENUM('CO', 'US') NOT NULL,
    location_preference VARCHAR(100),
    linkedin_url VARCHAR(255),
    cv_url VARCHAR(255),
    years_experience INTEGER,
    status ENUM('activo', 'archivado', 'contratado', 'rechazado') DEFAULT 'activo',
    stage ENUM('aplicacion', 'revision', 'entrevista', 'oferta', 'finalizado') DEFAULT 'aplicacion',
    application_date DATE NOT NULL
);

CREATE TABLE notes (
    id INTEGER PRIMARY KEY,
    candidate_id INTEGER REFERENCES candidates(id),
    content TEXT NOT NULL,
    author VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Schema Incidencias**:
- No persistente (análisis on-demand)
- Validación contra especificaciones en BRIEFING_INCIDENCIAS.md

## Convenciones de Código

### TypeScript
- Modo strict activado
- Interfaces explícitas para todos los tipos
- No usar `any`
- Preferir `type` para unions, `interface` para objetos
- Props de componentes tipadas explícitamente
- Async/await en lugar de .then()

### Python
- Type hints en funciones públicas
- Docstrings para funciones complejas
- PEP 8 para naming (snake_case)
- Async/await para operaciones I/O
- Try/except con HTTPException en FastAPI

### Naming Conventions

**Frontend (TypeScript)**:
- Componentes: PascalCase (`CandidateCard.tsx`)
- Funciones: camelCase (`getCandidates`, `handleSubmit`)
- Tipos: PascalCase (`Candidate`, `Status`)
- Constantes: UPPER_SNAKE_CASE (`API_BASE_URL`)

**Backend (Python)**:
- Archivos: snake_case (`candidate.py`)
- Clases: PascalCase (`CandidateCreate`)
- Funciones: snake_case (`get_candidates`, `validar_registro`)
- Constantes: UPPER_SNAKE_CASE (`CATEGORIAS_PERMITIDAS`)

## Estructura de Archivos

### App Next.js
```
uis/backoffice/app/
├── page.tsx                    # Listado principal (/)
├── layout.tsx                  # Layout raíz
├── globals.css                 # Estilos globales
├── candidates/[id]/
│   ├── page.tsx               # Detalle candidato
│   └── edit/
│       └── page.tsx           # Editar candidato (PUT)
├── new/
│   └── page.tsx               # Crear candidato (POST)
└── incidents/
    └── page.tsx               # Análisis de incidencias
```

### API FastAPI
```
services/api/app/
├── main.py                    # App principal + CORS
├── config.py                  # Settings (Pydantic)
├── database.py                # SQLAlchemy setup
├── models/
│   ├── candidate.py           # ORM models
│   └── note.py
├── schemas/
│   ├── candidate.py           # Pydantic schemas
│   └── incident.py
├── routers/
│   ├── candidates.py          # Endpoints ATS
│   └── incidents.py           # Endpoints incidencias
└── services/
    └── incident_analyzer.py   # Lógica compartida
```

## API Endpoints

### ATS Candidates
- `GET /records` - Listar (filtros: status, stage, search)
- `GET /records/{id}` - Detalle
- `POST /records` - Crear
- `PUT /records/{id}` - Actualizar completo
- `PATCH /records/{id}/status` - Actualizar estado
- `PATCH /records/{id}/stage` - Actualizar etapa
- `GET /records/{id}/notes` - Listar notas
- `POST /records/{id}/notes` - Crear nota
- `DELETE /records/{id}/notes/{note_id}` - Eliminar nota

### Incidents Analysis
- `POST /incidents/analyze` - Analizar CSV (multipart/form-data)
- `GET /incidents/health` - Health check

## Patrones de Diseño

### Frontend Patterns
1. **Three-state UI**: loading/success/error en cada operación async
2. **Optimistic Updates**: Actualizar UI inmediatamente en operaciones rápidas
3. **URL State Sync**: Filtros en query params para compartir URLs
4. **Form Validation**: Validación en cliente antes de enviar al backend
5. **Error Boundaries**: Manejo de errores en catch blocks con UI feedback

### Backend Patterns
1. **Service Layer**: Lógica de negocio en `/services`, no en routers
2. **Schema Validation**: Pydantic valida automáticamente en endpoints
3. **Response Models**: Todos los endpoints tienen response_model
4. **Error Handling**: HTTPException con status codes semánticos
5. **DRY Principle**: Código compartido entre CLI y API

## Configuración de Desarrollo

### Backend Setup
```bash
cd services/api
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn python-multipart pydantic-settings sqlalchemy email-validator
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd uis/backoffice
npm install
npm run dev  # http://localhost:3000
```

### CLI Usage
```bash
python scripts/analyze.py archivo.csv [--export]
```

## Paleta de Colores Brasaland

**Tailwind Config**:
```typescript
colors: {
  primary: colors.orange[600],    // #ea580c
  secondary: colors.amber[100],   // #fef3c7
  accent: colors.orange[700],     // #c2410c
}
```

**Uso**:
- Botones principales: `bg-orange-600 hover:bg-orange-700`
- Backgrounds: `bg-amber-50`
- Bordes: `border-amber-200`
- Texto destacado: `text-amber-950`

## Restricciones Técnicas

1. **No usar librerías de estado externas** (Redux, MobX, Zustand)
2. **No usar Pages Router** de Next.js (solo App Router)
3. **TypeScript estricto** (no `any`, no implicit any)
4. **Python 3.7+** compatible (stdlib en CLI)
5. **UTF-8 encoding** obligatorio en CSVs
6. **CORS** configurado para desarrollo (localhost:3000)

## Testing (Pendiente)

- Unit tests: pytest (backend), Jest (frontend)
- Integration tests: Playwright/Cypress
- E2E: Flujos completos de usuario

## Deployment (Futuro)

- Backend: Render/Railway/Fly.io
- Frontend: Vercel/Netlify
- Database: PostgreSQL en producción
- Env vars: `.env.local` (frontend), `.env` (backend)

## Documentación

- **Técnica**: `docs/` (BRIEFING, guides, API docs)
- **API**: OpenAPI en `/docs` (FastAPI autodoc)
- **Scripts**: README en `scripts/`
- **Setup**: `ATS_SETUP.md`, `INCIDENTS_API.md`
