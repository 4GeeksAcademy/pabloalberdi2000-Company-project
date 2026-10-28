# Brasaland ATS API

Backend API para el sistema de gestión de candidaturas (ATS) de Brasaland.

🔒 **Estado de Seguridad**: ✅ Auditado y certificado (Oct 2026)  
📋 **Auditoría de Serialización**: [Ver Informe Completo](docs/serialization-audit.md)

## Tecnologías

- **Framework:** FastAPI 0.110.0
- **Base de datos:** SQLite (desarrollo) / PostgreSQL (producción)
- **ORM:** SQLAlchemy 2.0
- **Validación:** Pydantic 2.6

## Instalación

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus configuraciones
```

## Ejecutar

```bash
# Modo desarrollo (con hot-reload)
uvicorn app.main:app --reload

# O directamente con Python
python -m app.main
```

La API estará disponible en:
- **API:** http://localhost:8000
- **Documentación interactiva:** http://localhost:8000/docs
- **Documentación alternativa:** http://localhost:8000/redoc

## Endpoints Principales

### Candidatos
- `GET /records` - Listar candidatos (con filtros opcionales)
- `GET /records/{id}` - Obtener candidato por ID
- `POST /records` - Crear nuevo candidato
- `PUT /records/{id}` - Actualizar candidato
- `PATCH /records/{id}/status` - Actualizar estado
- `PATCH /records/{id}/stage` - Actualizar etapa

### Notas
- `GET /records/{id}/notes` - Obtener notas del candidato
- `POST /records/{id}/notes` - Crear nota
- `DELETE /records/{id}/notes/{note_id}` - Eliminar nota

## Modelos de Datos

### Candidate
- Nombre completo, email, teléfono
- Puesto solicitado
- País (CO/US)
- LinkedIn y CV URLs
- Años de experiencia
- Estado: activo, archivado, contratado, rechazado
- Etapa: aplicacion, revision, entrevista, oferta, finalizado

### Note
- Contenido de la nota
- Autor
- Fecha de creación
- Candidato asociado

## Base de Datos

Por defecto usa SQLite (`brasaland_ats.db`). Las tablas se crean automáticamente al iniciar la aplicación.

Para usar PostgreSQL en producción, actualiza `DATABASE_URL` en `.env`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/brasaland_ats
```

## Desarrollo

```bash
# Instalar dependencias de desarrollo
pip install black flake8 pytest

# Formatear código
black app/

# Linter
flake8 app/
```

## 🔒 Seguridad y Auditorías

### Auditoría de Serialización API (Oct 2026)

**Estado**: ✅ **APROBADO - 100% CUMPLIMIENTO**

El backend ha sido auditado exhaustivamente en términos de:
- Serialización y exposición de datos
- Fugas de información sensible
- Seguridad de contratos API
- Patrones arquitectónicos

**Resultados clave**:
- ✅ 42/42 endpoints con `response_model` explícito (100%)
- ✅ 0 fugas de contraseñas detectadas
- ✅ 0 objetos ORM expuestos en crudo
- ✅ Separación entrada/salida implementada (100%)

**Documentación**:
- [Informe Completo](docs/serialization-audit.md) - 25+ páginas de análisis técnico
- [Resumen Ejecutivo](docs/SERIALIZATION_AUDIT_SUMMARY.md) - Métricas y certificación

### Protección de Datos Sensibles

El API implementa las siguientes medidas de seguridad:

1. **Contraseñas**:
   - ✅ Nunca devueltas en responses (ni plain ni hashed)
   - ✅ Hashing con bcrypt en todos los flujos de auth
   - ✅ Reset tokens enviados solo por email

2. **Emails**:
   - ✅ Exposición controlada y justificada
   - ✅ Solo visible por usuario propio o admin autorizado

3. **Serialización**:
   - ✅ Todos los endpoints usan esquemas Pydantic explícitos
   - ✅ Ningún objeto ORM/TinyDB devuelto en crudo
   - ✅ Construcción manual de responses (control total)

## 📚 Documentación Técnica

### Estructura de Documentos

```
docs/
├── serialization-audit.md          # Auditoría completa (25+ páginas)
├── SERIALIZATION_AUDIT_SUMMARY.md  # Resumen ejecutivo
└── [Futuros documentos de arquitectura]
```

### Catálogo de Endpoints

El API expone 42 endpoints distribuidos en 7 routers:

- **`/auth`** (5): Autenticación y gestión de contraseñas
- **`/users`** (5): Gestión de usuarios internos
- **`/candidates`** (5): Sistema ATS
- **`/incidents`** (8): Sistema de incidencias
- **`/inventory`** (8): Gestión de inventario Supabase
- **`/profiles`** (3): Perfiles de usuario
- **`/health`** (1): Health check

Ver [serialization-audit.md](docs/serialization-audit.md) para detalles completos de cada endpoint.

## Contexto

Este sistema es parte del proyecto de transformación digital de Brasaland, específicamente para el departamento de Personas y Cultura liderado por Ashley Turner (Miami).

**Necesidad:** Gestionar 115 empleados en 14 locales de 2 países (Colombia y Florida) con alta rotación en personal de cocina.
