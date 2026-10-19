# Brasaland ATS - Guía de Instalación y Ejecución

Sistema de gestión de candidaturas completo (Backend + Frontend) para el departamento de Personas y Cultura de Brasaland.

## 📋 Resumen del Sistema

**Problema:** Ashley Turner (Personas y Cultura, Miami) gestiona 115 empleados en 14 locales de 2 países (Colombia/Florida) con procesos completamente manuales (email/Excel) y alta rotación en cocina.

**Solución:** ATS (Applicant Tracking System) que permite:
- Centralizar candidaturas
- Filtrar por estado y etapa del proceso
- Gestionar notas de seguimiento
- Reducir tiempo de contratación

**Stack Técnico:**
- Backend: FastAPI + SQLAlchemy + SQLite/PostgreSQL
- Frontend: Next.js 15 + TypeScript + Tailwind CSS

---

## 🚀 Instalación Completa

### Prerequisitos

- Python 3.10+ instalado
- Node.js 18+ instalado
- npm o yarn instalado

### Paso 1: Instalar el Backend (FastAPI)

```bash
# Navegar al directorio del backend
cd apps/ats-api

# Crear entorno virtual de Python
python -m venv venv

# Activar entorno virtual
# En macOS/Linux:
source venv/bin/activate
# En Windows:
# venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno (opcional)
cp .env.example .env
# Editar .env si es necesario (SQLite funciona sin configuración)
```

### Paso 2: Instalar el Frontend (Next.js)

```bash
# Navegar al directorio del frontend
cd ../ats-web

# Instalar dependencias
npm install

# Configurar variables de entorno
cp .env.local.example .env.local
# NEXT_PUBLIC_API_URL ya está configurado para http://localhost:8000
```

---

## 🏃 Ejecutar el Sistema

### Terminal 1: Iniciar el Backend

```bash
cd apps/ats-api

# Activar entorno virtual si no está activo
source venv/bin/activate  # macOS/Linux
# o venv\Scripts\activate en Windows

# Iniciar servidor FastAPI
uvicorn app.main:app --reload
```

✅ El backend estará disponible en: **http://localhost:8000**
📚 Documentación de la API: **http://localhost:8000/docs**

### Terminal 2: Iniciar el Frontend

```bash
cd apps/ats-web

# Iniciar servidor Next.js
npm run dev
```

✅ El frontend estará disponible en: **http://localhost:3000**

---

## ✅ Verificar que Funciona

### 1. Verificar Backend

Abre http://localhost:8000/docs en tu navegador. Deberías ver la documentación interactiva de Swagger UI.

O prueba desde la terminal:

```bash
curl http://localhost:8000/health
# Debería responder: {"status":"healthy"}

curl http://localhost:8000/records
# Debería responder: [] (array vacío, aún no hay candidatos)
```

### 2. Verificar Frontend

Abre http://localhost:3000 en tu navegador. Deberías ver:
- Página con el header "Sistema de Candidaturas"
- Filtros de búsqueda
- Mensaje "0 candidatos encontrados" (porque la BD está vacía)
- Botón "Nueva Candidatura"

### 3. Crear Primera Candidatura

1. Click en "Nueva Candidatura"
2. Completa el formulario:
   - Nombre: Juan Pérez
   - Email: juan@example.com
   - Teléfono: +57 300 123 4567
   - Puesto: Cocinero
   - País: Colombia
   - Años experiencia: 5
3. Click en "Crear Candidatura"
4. Deberías ser redirigido a la página de detalle del candidato

### 4. Probar Filtros y Búsqueda

1. Volver al listado (/)
2. Buscar por "Juan"
3. Filtrar por estado "Activo"
4. Filtrar por etapa "Aplicación"

### 5. Probar Gestión de Notas

1. Entrar al detalle de un candidato
2. Agregar una nota:
   - Autor: Ashley Turner
   - Contenido: "Excelente experiencia en parrilla"
3. La nota debería aparecer inmediatamente
4. Probar eliminar la nota

### 6. Probar Actualización de Estado/Etapa

1. En el detalle del candidato
2. Cambiar Estado a "Contratado"
3. Cambiar Etapa a "Finalizado"
4. Volver al listado y verificar que los cambios se reflejan

---

## 📁 Estructura del Proyecto

```
apps/
├── ats-api/                    # Backend FastAPI
│   ├── app/
│   │   ├── main.py             # Punto de entrada
│   │   ├── models/             # Modelos SQLAlchemy
│   │   ├── schemas/            # Schemas Pydantic
│   │   ├── routers/            # Endpoints API
│   │   ├── database.py         # Configuración BD
│   │   └── config.py           # Settings
│   ├── requirements.txt        # Dependencias Python
│   └── README.md
│
└── ats-web/                    # Frontend Next.js
    ├── app/
    │   ├── page.tsx            # Listado (/)
    │   ├── candidates/[id]/    # Detalle
    │   └── new/                # Formulario
    ├── lib/
    │   └── api.ts              # Cliente API
    ├── types/
    │   └── index.ts            # Tipos TypeScript
    ├── package.json
    └── README.md
```

---

## 🎨 Características Implementadas

### Backend (FastAPI)
- ✅ CRUD completo de candidatos
- ✅ Filtros por estado, etapa y búsqueda
- ✅ Sistema de notas
- ✅ Actualización parcial de estado/etapa
- ✅ Validación con Pydantic
- ✅ Base de datos SQLite (desarrollo)
- ✅ Documentación automática con Swagger
- ✅ CORS configurado

### Frontend (Next.js)
- ✅ Listado con filtros y búsqueda en tiempo real
- ✅ Detalle completo del candidato
- ✅ Formulario de alta con validación
- ✅ Gestión de notas (crear/eliminar)
- ✅ Actualización de estado y etapa
- ✅ Estados de loading/success/error
- ✅ Navegación sin recargas (App Router)
- ✅ Diseño responsive con Tailwind
- ✅ Colores de marca Brasaland
- ✅ TypeScript estricto

---

## 🔧 Solución de Problemas

### Backend no inicia

```bash
# Verificar que el puerto 8000 no está ocupado
lsof -ti:8000
# Si está ocupado, matar el proceso:
kill -9 $(lsof -ti:8000)

# Verificar que las dependencias están instaladas
pip list | grep fastapi
```

### Frontend no conecta con Backend

1. Verificar que el backend está corriendo en http://localhost:8000
2. Verificar `.env.local` tiene: `NEXT_PUBLIC_API_URL=http://localhost:8000`
3. Reiniciar el servidor Next.js: Ctrl+C y `npm run dev`

### Error de CORS

Si ves errores de CORS en la consola del navegador:
1. Verifica que el backend tiene CORS configurado en `app/main.py`
2. Verifica que `http://localhost:3000` está en la lista de orígenes permitidos

---

## 📊 Endpoints de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/records` | Listar candidatos (con filtros) |
| GET | `/records/{id}` | Obtener candidato por ID |
| POST | `/records` | Crear candidato |
| PUT | `/records/{id}` | Actualizar candidato completo |
| PATCH | `/records/{id}/status` | Actualizar solo estado |
| PATCH | `/records/{id}/stage` | Actualizar solo etapa |
| GET | `/records/{id}/notes` | Obtener notas |
| POST | `/records/{id}/notes` | Crear nota |
| DELETE | `/records/{id}/notes/{note_id}` | Eliminar nota |

---

## 🎯 Próximos Pasos

Para continuar desarrollando el sistema:

1. **Autenticación:** Agregar login para Ashley y su equipo
2. **Dashboard:** Métricas de contratación (tiempo medio, tasas de conversión)
3. **Email:** Notificaciones automáticas a candidatos
4. **Calendario:** Integración para agendar entrevistas
5. **Reportes:** Exportar datos a Excel/PDF
6. **Multi-local:** Filtrar por local específico
7. **Tests:** Pruebas unitarias y de integración

---

## 📞 Soporte

Este sistema fue desarrollado como parte del proyecto de Ingeniería de IA de 4Geeks Academy para Brasaland.

**Contexto del negocio:** Ver `/docs/CONTEXT.md` para entender la empresa.
**Propuesta de arquitectura:** Ver `/architecture-proposal.md` para el diseño completo del sistema.

---

## 🎉 ¡Listo!

El sistema ATS de Brasaland está funcionando. Puedes empezar a agregar candidatos y gestionar el proceso de contratación.
