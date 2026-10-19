# Brasaland ATS API

Backend API para el sistema de gestión de candidaturas (ATS) de Brasaland.

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

## Contexto

Este sistema es parte del proyecto de transformación digital de Brasaland, específicamente para el departamento de Personas y Cultura liderado por Ashley Turner (Miami).

**Necesidad:** Gestionar 115 empleados en 14 locales de 2 países (Colombia y Florida) con alta rotación en personal de cocina.
