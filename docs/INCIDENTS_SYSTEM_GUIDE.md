# Sistema de Análisis de Incidencias Postventa - Brasaland

## Guía Completa de Implementación

Sistema completo para validar y analizar incidencias postventa de los 14 locales de Brasaland (Colombia y Florida). Implementado en 3 fases: CLI, API y Frontend.

---

## 📋 Tabla de Contenidos

1. [Fase 1: Script CLI](#fase-1-script-cli)
2. [Fase 2: Backend API](#fase-2-backend-api)
3. [Fase 3: Frontend Web](#fase-3-frontend-web)
4. [Instalación Completa](#instalación-completa)
5. [Flujo de Uso](#flujo-de-uso)

---

## Fase 1: Script CLI

### Ubicación
- **Script**: `scripts/analyze.py`
- **Documentación**: `scripts/ANALYZE_INCIDENTS_README.md`
- **Archivo de prueba**: `scripts/test-incidents.csv`
- **Especificaciones**: `docs/BRIEFING_INCIDENCIAS.md`

### Uso Rápido

```bash
# Análisis básico (output en consola)
python scripts/analyze.py scripts/test-incidents.csv

# Con exportación a CSV
python scripts/analyze.py scripts/test-incidents.csv --export

# Ver ayuda
python scripts/analyze.py --help
```

### Características
✅ Validación contra especificaciones del BRIEFING  
✅ Detección de registros inválidos con razón específica  
✅ Métricas por categoría, estado y país  
✅ Índice de satisfacción promedio  
✅ Exportación opcional a CSV  
✅ Sin dependencias externas (solo stdlib)

---

## Fase 2: Backend API

### Ubicación
- **Endpoint**: `apps/ats-api/app/routers/incidents.py`
- **Servicio**: `apps/ats-api/app/services/incident_analyzer.py`
- **Schemas**: `apps/ats-api/app/schemas/incident.py`
- **Documentación**: `apps/ats-api/INCIDENTS_API.md`

### Iniciar Servidor

```bash
cd apps/ats-api
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

**Documentación interactiva**: http://localhost:8000/docs

### Endpoint Principal

**`POST /incidents/analyze`**

```bash
curl -X POST "http://localhost:8000/incidents/analyze" \
  -F "file=@incidents.csv"
```

**Response:**
```json
{
  "total_procesados": 10,
  "total_validos": 10,
  "total_invalidos": 0,
  "registros_invalidos": [],
  "por_categoria": [...],
  "por_estado": [...],
  "por_pais": [...],
  "satisfaccion_promedio": 3.6,
  "satisfaccion_evaluacion": "BUENO"
}
```

### Características
✅ Upload de archivos CSV  
✅ Validación completa según BRIEFING  
✅ Respuesta JSON estructurada  
✅ Manejo de errores detallado  
✅ CORS configurado para desarrollo  
✅ Health check endpoint

---

## Fase 3: Frontend Web

### Ubicación
- **Página**: `apps/ats-web/app/incidents/page.tsx`
- **URL**: http://localhost:3000/incidents

### Iniciar Frontend

```bash
cd apps/ats-web
npm install
npm run dev
```

**Acceso**: http://localhost:3000/incidents

### Características
✅ Upload drag-and-drop de archivos CSV  
✅ Visualización de métricas en tiempo real  
✅ Cards resumen (total procesados, válidos, inválidos)  
✅ Gráficos por categoría, estado y país  
✅ Índice de satisfacción con evaluación visual  
✅ Detalle de registros inválidos  
✅ Diseño responsive con Tailwind CSS  
✅ Integración con paleta de marca Brasaland

---

## Instalación Completa

### Prerequisitos
- Python 3.7+
- Node.js 16+
- npm o yarn

### Backend API

```bash
cd apps/ats-api
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install fastapi uvicorn python-multipart pydantic-settings sqlalchemy email-validator
```

### Frontend Next.js

```bash
cd apps/ats-web
npm install
```

### Iniciar Sistema Completo

Terminal 1 (Backend):
```bash
cd apps/ats-api
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

Terminal 2 (Frontend):
```bash
cd apps/ats-web
npm run dev
```

**Acceder a**:
- Frontend: http://localhost:3000/incidents
- API Docs: http://localhost:8000/docs
- ATS Principal: http://localhost:3000

---

## Flujo de Uso

### 1. Preparar Archivo CSV

El archivo debe seguir el formato especificado en `docs/BRIEFING_INCIDENCIAS.md`:

```csv
id_incidencia,fecha,categoria,descripcion,estado,local,pais,satisfaccion,email_cliente,telefono
INC001,2026-10-15,calidad_comida,Carne poco cocida,cerrado,medellin_centro,CO,4,cliente@email.com,+573001234567
INC002,2026-10-16,servicio_cliente,Tiempo de espera excesivo,en_proceso,miami_beach,US,,cliente2@email.com,+1234567890
```

### 2. Análisis con CLI (Rápido)

```bash
python scripts/analyze.py mi-archivo.csv
```

### 3. Análisis con Web UI (Completo)

1. Abrir http://localhost:3000/incidents
2. Click en "Seleccionar archivo" o arrastrar CSV
3. Click en "Analizar Incidencias"
4. Ver resultados visualizados con gráficos

### 4. Integración Programática

```javascript
// JavaScript/TypeScript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/incidents/analyze', {
  method: 'POST',
  body: formData
});

const data = await response.json();
console.log(`Satisfacción promedio: ${data.satisfaccion_promedio}`);
```

```python
# Python
import requests

with open('incidents.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/incidents/analyze',
        files={'file': ('incidents.csv', f, 'text/csv')}
    )
    data = response.json()
    print(f"Total válidos: {data['total_validos']}")
```

---

## Validaciones Implementadas

El sistema valida automáticamente:

1. ✅ **Campos obligatorios** presentes
2. ✅ **Categorías** en lista permitida
3. ✅ **Estados** en lista permitida
4. ✅ **Países** válidos (CO/US)
5. ✅ **Locales** existentes (14 locales)
6. ✅ **Formato de fecha** (YYYY-MM-DD)
7. ✅ **Rango de satisfacción** (1-5)
8. ✅ **Regla de negocio**: estado "cerrado" requiere satisfacción

Ver detalles completos en `docs/BRIEFING_INCIDENCIAS.md`

---

## Métricas Calculadas

### Por Categoría
- calidad_comida
- servicio_cliente
- operaciones
- infraestructura
- pedidos_online
- facturacion

### Por Estado
- abierto (pendiente de atención)
- en_proceso (trabajando en solución)
- cerrado (resuelto)
- descartado (no procede)

### Por País
- Colombia (10 locales)
- Florida, USA (4 locales)

### Índice de Satisfacción
- **Rango**: 1.0 - 5.0
- **Evaluación**:
  - 🟢 EXCELENTE (4.0 - 5.0)
  - 🟡 BUENO (3.0 - 3.9)
  - 🔴 REQUIERE ATENCIÓN (1.0 - 2.9)

---

## Estructura de Archivos

```
.
├── docs/
│   ├── BRIEFING_INCIDENCIAS.md          # Especificaciones completas
│   └── INCIDENTS_SYSTEM_GUIDE.md        # Esta guía
│
├── scripts/
│   ├── analyze.py                       # Script CLI
│   ├── test-incidents.csv               # Datos de prueba
│   └── ANALYZE_INCIDENTS_README.md      # Documentación CLI
│
├── apps/ats-api/
│   ├── app/
│   │   ├── routers/incidents.py         # Endpoints FastAPI
│   │   ├── services/incident_analyzer.py # Lógica de análisis
│   │   └── schemas/incident.py          # Schemas Pydantic
│   └── INCIDENTS_API.md                 # Documentación API
│
└── apps/ats-web/
    └── app/
        └── incidents/
            └── page.tsx                  # Página Next.js
```

---

## Troubleshooting

### Backend no inicia

```bash
# Verificar que el venv esté activado
which python  # Debe mostrar ruta del venv

# Reinstalar dependencias
pip install --upgrade fastapi uvicorn python-multipart
```

### Frontend no carga

```bash
# Limpiar cache
rm -rf .next node_modules
npm install
npm run dev
```

### Error CORS

Verificar que el backend esté en puerto 8000 y el frontend esté configurado para apuntar a `http://localhost:8000`

### Archivo CSV rechazado

- Verificar que tenga extensión `.csv`
- Verificar codificación UTF-8
- Verificar que tenga header con nombres correctos
- Consultar ejemplos en `scripts/test-incidents.csv`

---

## Próximas Mejoras

- [ ] Persistencia de análisis históricos
- [ ] Gráficos interactivos (Chart.js)
- [ ] Export de resultados a PDF
- [ ] Filtros avanzados en frontend
- [ ] Comparación entre períodos
- [ ] Dashboard ejecutivo
- [ ] Notificaciones automáticas
- [ ] Integración con sistema de tickets

---

**Responsable**: Nicolás Park (CTO - Brasaland Digital)  
**Departamento**: Tecnología + Operaciones  
**Versión**: 1.0  
**Fecha**: Octubre 2026  
**Estado**: ✅ Sistema completo (3/3 fases)
