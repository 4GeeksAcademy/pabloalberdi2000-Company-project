# Brasaland ATS - Frontend

Sistema de gestión de candidaturas (ATS) en Next.js para el departamento de Personas y Cultura de Brasaland.

## Tecnologías

- **Framework:** Next.js 15 (App Router)
- **Lenguaje:** TypeScript 5
- **Estilos:** Tailwind CSS 3.4
- **Estado:** React Hooks nativos (`useState`, `useEffect`)

## Instalación

```bash
# Instalar dependencias
npm install

# Configurar variables de entorno
cp .env.local.example .env.local
# Editar .env.local con la URL de tu API
```

## Ejecutar

```bash
# Modo desarrollo
npm run dev

# La aplicación estará en http://localhost:3000
```

## Estructura

```
app/
├── page.tsx                    # Listado de candidatos (/)
├── layout.tsx                  # Layout principal
├── globals.css                 # Estilos globales
├── candidates/
│   └── [id]/
│       └── page.tsx            # Detalle del candidato
└── new/
    └── page.tsx                # Formulario de nueva candidatura

components/                     # Componentes reutilizables (vacío por ahora)
lib/
└── api.ts                      # Cliente API con fetch
types/
└── index.ts                    # Tipos TypeScript compartidos
```

## Funcionalidades

### Listado de Candidatos (`/`)
- ✅ Muestra todos los candidatos con paginación
- ✅ Filtros por estado y etapa sincronizados con URL
- ✅ Búsqueda en tiempo real por nombre/email
- ✅ Estados de loading/success/error

### Detalle de Candidato (`/candidates/[id]`)
- ✅ Información completa del candidato
- ✅ Actualización de estado (activo, archivado, contratado, rechazado)
- ✅ Actualización de etapa (aplicación, revisión, entrevista, oferta, finalizado)
- ✅ Sistema de notas con creación y eliminación
- ✅ Enlaces a LinkedIn y CV

### Nueva Candidatura (`/new`)
- ✅ Formulario completo con validación
- ✅ Mensajes de error específicos por campo
- ✅ Redirección automática al detalle tras crear

## Contexto de Brasaland

Este sistema está adaptado al contexto real de Brasaland:

- **Colores:** Paleta amber/orange de la marca
- **Países:** Colombia (CO) y Florida, USA (US)
- **Puestos:** Roles específicos de restaurante (Cocinero, Mesero, Supervisor, etc.)
- **Lenguaje:** Español, terminología del sector

**Responsable:** Ashley Turner (Personas y Cultura, Miami)
**Necesidad:** Gestionar contrataciones para 115 empleados en 14 locales con alta rotación en cocina.

## Desarrollo

```bash
# Linter
npm run lint

# Build para producción
npm run build

# Ejecutar build
npm start
```

## Variables de Entorno

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000  # URL del backend FastAPI
```

## Dependencias del Backend

Este frontend requiere que el backend FastAPI (`apps/ats-api/`) esté ejecutándose en el puerto 8000.

Ver [apps/ats-api/README.md](../ats-api/README.md) para instrucciones del backend.
