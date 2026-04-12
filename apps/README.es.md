# Carpeta `apps`

Esta carpeta contiene **todas las aplicaciones del monorepo** relacionadas con la compañía para el proyecto transversal de AI Engineering (por ejemplo: aplicaciones web, APIs, dashboards internos, portales de clientes, etc.).

Cada subcarpeta dentro de `apps/` debe corresponder a **una aplicación concreta** (por ejemplo `web-portal`, `admin-api`, `backoffice-dashboard`) e incluir su propia documentación técnica y funcional.

- **Propósito principal**: centralizar en un único monorepo todas las aplicaciones que dan soporte a los casos de uso de la compañía.
- **Recomendación**: documenta en este archivo (o en sub-READMEs) las aplicaciones que vayas añadiendo, su objetivo, tecnología usada y cómo ejecutarlas en desarrollo, pruebas y producción.

## Aplicaciones actuales

- `brasaland-web`: landing (`apps/index.html`) y un único formulario de aplicación (`apps/application.html`) con validación en JavaScript vanilla (`apps/validation.js`), accesibilidad orientada a WCAG y datos estructurados SEO básicos.
