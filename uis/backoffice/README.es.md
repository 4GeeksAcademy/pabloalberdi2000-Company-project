# Brasaland ATS - Frontend

[🇬🇧 English](./README.md) | 🇪🇸 Español

Sistema de gestión de candidaturas (Applicant Tracking System) desarrollado en Next.js para el departamento de Personas y Cultura de Brasaland.

## 🎯 Propósito

Facilitar la gestión de contrataciones para Ashley Turner (Personas y Cultura) quien administra 115 empleados en 14 locales distribuidos entre Colombia y Florida, con especial atención a la alta rotación de personal de cocina.

## 🚀 Inicio Rápido

```bash
# 1. Instalar dependencias
npm install

# 2. Configurar entorno
cp .env.local.example .env.local

# 3. Ejecutar en modo desarrollo
npm run dev
```

Abre [http://localhost:3000](http://localhost:3000) en tu navegador.

## 📋 Características

- **Listado de Candidatos:** Filtros por estado/etapa + búsqueda en tiempo real
- **Perfil Completo:** Visualización de datos + actualización de estado/etapa
- **Gestión de Notas:** Sistema de comentarios y seguimiento
- **Formulario de Alta:** Validación completa con feedback inmediato
- **Navegación Fluida:** Sin recargas de página usando Next.js App Router

## 🛠️ Tecnologías

- Next.js 15 (App Router)
- TypeScript 5
- Tailwind CSS 3.4
- Hooks nativos de React (sin librerías de estado externas)

## 🎨 Diseño

Colores de la marca Brasaland (paleta amber/orange) con diseño responsive optimizado para dispositivos móviles y desktop.

## 📦 Scripts Disponibles

```bash
npm run dev      # Desarrollo
npm run build    # Build de producción
npm start        # Servidor de producción
npm run lint     # Linter
```

## 🔗 Backend

Este frontend requiere el backend FastAPI ejecutándose en `http://localhost:8000`.

Ver [../ats-api/README.md](../ats-api/README.md) para instrucciones del backend.

## 📄 Licencia

Proyecto interno de Brasaland para uso del programa de Ingeniería de IA de 4Geeks Academy.
