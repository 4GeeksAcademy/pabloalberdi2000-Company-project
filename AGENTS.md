# Protocolo de Agentes - Brasaland Digital

**Versión**: 1.0  
**Última actualización**: 19 de Octubre, 2026  
**Responsable**: Nicolás Park (CTO)

---

## 📚 Archivos de Inicio de Sesión Obligatorios

Todo agente IA que trabaje en este monorepo **DEBE** leer los siguientes archivos al iniciar cada sesión **ANTES** de realizar cualquier acción:

### Lectura Obligatoria (en orden)

1. **`/memory-bank/projectbrief.md`**
   - **Propósito**: Entender el negocio de Brasaland, problemas que resuelven los sistemas, y usuarios finales
   - **Contenido crítico**: 14 locales (10 CO + 4 US), 115 empleados, $6M anuales, CEO Mariana Restrepo, áreas y necesidades
   - **Tiempo de lectura**: 5 min

2. **`/memory-bank/techContext.md`**
   - **Propósito**: Stack tecnológico, arquitectura del monorepo, convenciones de código
   - **Contenido crítico**: Next.js 15 App Router, FastAPI, TypeScript strict, patrones de diseño, paleta de colores
   - **Tiempo de lectura**: 8 min

3. **`/memory-bank/progress.md`**
   - **Propósito**: Estado actual del desarrollo, proyectos completados, backlog priorizado
   - **Contenido crítico**: ATS 100%, Incidencias 100%, próximos proyectos (Dashboard, Fidelización)
   - **Tiempo de lectura**: 4 min

### Lectura Condicional

4. **`/docs/CONTEXT.md`** (si necesitas contexto adicional del negocio)
   - Descripción completa de Brasaland, departamentos, stakeholders

5. **`/docs/BRIEFING_INCIDENCIAS.md`** (si trabajas en incidencias)
   - Especificaciones técnicas del sistema de análisis

6. **`/AUDIT_INCIDENTS.md` o `/FINAL_AUDIT.md`** (si necesitas criterios de calidad)
   - Rúbricas de evaluación y estándares de código

---

## 🔄 Flujo Pre-Commit Obligatorio

**CRÍTICO**: Antes de crear cualquier commit en este repositorio, el agente **DEBE** ejecutar los siguientes pasos en orden:

### Paso 1: Linting y Type Checking
```bash
# Frontend (TypeScript)
cd uis/backoffice
npm run lint        # ESLint
npm run type-check  # TypeScript compiler (si existe script)
# O manualmente: npx tsc --noEmit

# Backend (Python)
cd services/api
source venv/bin/activate
# flake8 app/ (si está configurado)
# mypy app/ (si está configurado)
```

**Criterios de aprobación**:
- ✅ Cero errores de linting
- ✅ Cero errores de tipos (TypeScript strict mode)
- ✅ Warnings revisados y justificados

**Acción si falla**: Corregir errores antes de continuar

---

### Paso 2: Ejecución de Tests
```bash
# Frontend
cd uis/backoffice
npm test  # (cuando existan tests)

# Backend
cd services/api
source venv/bin/activate
pytest  # (cuando existan tests)

# CLI
python scripts/analyze.py scripts/test-incidents.csv  # Smoke test
```

**Criterios de aprobación**:
- ✅ Todos los tests existentes pasan
- ✅ Cobertura de código no disminuye
- ✅ Nuevas features tienen tests asociados

**Acción si falla**: No hacer commit hasta que los tests pasen

**Nota**: Actualmente no hay tests implementados. Este paso se activa cuando se agreguen.

---

### Paso 3: Smoke Testing Manual

Ejecutar el sistema completo y verificar que funciona:

```bash
# Terminal 1: Backend
cd services/api
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd uis/backoffice
npm run dev

# Terminal 3: Verificación
curl http://localhost:8000/health  # Backend funciona
curl http://localhost:3000          # Frontend funciona
```

**Verificaciones mínimas**:
- ✅ Backend inicia sin errores
- ✅ Frontend compila sin errores
- ✅ Página principal carga correctamente
- ✅ Navegación entre páginas funciona

**Acción si falla**: Identificar y corregir errores de runtime

---

### Paso 4: Actualización de Documentación

Actualizar **obligatoriamente** los siguientes archivos si aplica:

#### 4.1. `/memory-bank/progress.md`
**Cuándo**: Siempre que completes una feature, fixes un bug, o cambies el estado de un proyecto

**Qué actualizar**:
- Marcar tasks completadas con `[x]`
- Actualizar porcentaje de progreso
- Agregar nuevas features a la sección correspondiente
- Actualizar métricas (líneas de código, endpoints, etc.)
- Agregar notas de decisiones arquitectónicas

**Ejemplo**:
```markdown
### 2. Sistema de Análisis de Incidencias
**Estado**: ✅ **100% Completado**
**Progreso**: 100% (antes 90%)

**Completado en este commit**:
- [x] Botón de exportación CSV en frontend
```

#### 4.2. `/memory-bank/techContext.md`
**Cuándo**: Cuando cambies decisiones arquitectónicas, agregues dependencias, o modifiques convenciones

**Qué actualizar**:
- Stack tecnológico (nuevas librerías)
- Estructura de archivos (nuevas carpetas)
- Patrones de diseño (nuevos patterns)
- Restricciones técnicas

#### 4.3. README o documentación específica
**Cuándo**: Cuando agregues nuevos endpoints, componentes públicos, o cambies el setup

**Archivos candidatos**:
- `services/api/INCIDENTS_API.md`
- `scripts/ANALYZE_INCIDENTS_README.md`
- `docs/INCIDENTS_SYSTEM_GUIDE.md`

---

### Paso 5: Revisión de Cambios

Antes de hacer commit, ejecutar:

```bash
git status
git diff
```

**Verificar**:
1. ✅ Solo archivos intencionados están staged
2. ✅ No hay archivos temporales (*.log, *.tmp, results.csv)
3. ✅ No hay secrets o API keys
4. ✅ No hay `console.log` o `print()` de debug olvidados
5. ✅ `.gitignore` está actualizado si se generan nuevos temporales
6. ✅ Commits atómicos (un propósito por commit)

**Criterios de mensaje de commit**:
```
<tipo>: <descripción corta>

<descripción detallada opcional>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Tipos válidos**:
- `feat`: Nueva funcionalidad
- `fix`: Corrección de bug
- `docs`: Solo documentación
- `style`: Formato (no afecta lógica)
- `refactor`: Cambio de código sin cambiar comportamiento
- `test`: Agregar o corregir tests
- `chore`: Mantenimiento (deps, config)

**Ejemplo**:
```
feat: agregar botón de exportación CSV en sistema de incidencias

- Función exportToCSV() convierte resultados a CSV
- Botón verde aparece después de análisis exitoso
- Nombre de archivo incluye timestamp
- Actualizado uis/backoffice/app/incidents/page.tsx

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## 🚫 Zonas Protegidas

Las siguientes carpetas y archivos **NO DEBEN MODIFICARSE** sin confirmación explícita y previa del desarrollador:

### Archivos de Configuración Crítica
```
/.gitignore                          # Requiere revisión de seguridad
/package.json (raíz)                 # Si existe
/uis/backoffice/package.json         # Cambios de dependencias
/services/api/requirements.txt       # Cambios de dependencias
/uis/backoffice/tsconfig.json        # Config TypeScript
/uis/backoffice/tailwind.config.ts   # Config Tailwind
/services/api/app/config.py          # Settings de producción
```

**Razón**: Cambios aquí pueden romper builds, deploys, o seguridad

**Protocolo**: Avisar al desarrollador antes de modificar, explicar cambio propuesto, esperar aprobación

---

### Base de Datos y Migraciones
```
/services/api/*.db                 # Base de datos SQLite
/services/api/alembic/             # Migraciones (si existen)
```

**Razón**: Pérdida de datos, corrupción de schema

**Protocolo**: Solo leer para debugging, nunca modificar directamente

---

### Archivos de Producción/Deploy
```
/Dockerfile (si existe)
/docker-compose.yml (si existe)
/.github/workflows/ (si existe)
/vercel.json (si existe)
```

**Razón**: Afectan deployments en producción

**Protocolo**: Cambios solo con plan de rollback documentado

---

### Documentación de Auditoría
```
/AUDIT_REPORT.md
/FINAL_AUDIT.md
/VERIFICATION_100.md
/AUDIT_INCIDENTS.md
```

**Razón**: Registros históricos de calidad

**Protocolo**: No modificar. Crear nuevos archivos para nuevas auditorías

---

### Memory Bank (Modificación Controlada)
```
/memory-bank/*.md
```

**Razón**: Memoria crítica del agente

**Protocolo**: Actualizar `progress.md` en cada commit significativo. Modificar `projectbrief.md` o `techContext.md` solo si cambia contexto fundamental.

---

## ⚙️ Configuración del Agente

### Modelo Recomendado
- **Primario**: Claude Sonnet 4.5 (razonamiento + código)
- **Secundario**: Claude Opus 4 (tareas complejas de arquitectura)
- **Fast**: Claude Haiku (tareas simples, linting)

### Contexto Máximo
- Cargar memory bank completo (3 archivos)
- Mantener ventana de contexto para archivos recientes
- Usar herramientas de búsqueda para archivos grandes

### Especialización
- **Dominio**: Restaurantes, operaciones multicountry, RRHH
- **Stack**: Next.js 15 + FastAPI + TypeScript + Python
- **Terminología**: Usar lenguaje de Brasaland (locales, candidatos, incidencias)

---

## 🎯 Reglas de Oro

1. **Contexto primero**: Lee memory bank antes de codear
2. **Brasaland-first**: Usa terminología y datos reales del negocio
3. **No suposiciones**: Si algo no está claro, pregunta antes de implementar
4. **Tests obligatorios**: Toda feature nueva requiere tests (cuando se implemente testing)
5. **Documentación sincronizada**: Actualiza `progress.md` en cada commit significativo
6. **Commits atómicos**: Un propósito, un commit
7. **Pre-commit ritual**: Los 5 pasos son obligatorios
8. **Zonas protegidas**: Confirmar antes de tocar archivos críticos

---

## 📞 Escalación

Si el agente encuentra:
- **Decisión arquitectónica importante** → Preguntar al desarrollador
- **Cambio que afecta producción** → Requiere aprobación explícita
- **Bug crítico en producción** → Notificar inmediatamente
- **Duda sobre requisitos de negocio** → Consultar con stakeholder (vía desarrollador)

---

**Protocolo aprobado por**: Nicolás Park (CTO Brasaland)  
**Vigencia**: Indefinida (hasta nueva versión)  
**Revisión**: Cada 3 meses o cuando cambien procesos fundamentales
