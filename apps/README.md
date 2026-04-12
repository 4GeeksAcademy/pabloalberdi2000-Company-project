# `apps` Folder

This folder contains **all the applications of the monorepo** related to the company for the cross-functional AI Engineering project (for example: web applications, APIs, internal dashboards, customer portals, etc.).

Each subfolder inside `apps/` must correspond to **one specific application** (for example: `web-portal`, `admin-api`, `backoffice-dashboard`) and include its own technical and functional documentation.

- **Main purpose**: to centralize in a single monorepo all the applications that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the applications you add, their objective, the technology used, and how to run them in development, testing, and production environments.

## Current apps

- `brasaland-web`: landing page (`apps/index.html`) and a single application form (`apps/application.html`) with vanilla JavaScript validation (`apps/validation.js`), WCAG-oriented accessibility, and SEO structured data.
