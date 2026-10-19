# API de Análisis de Incidencias - Brasaland

## Endpoint Implementado

### `POST /incidents/analyze`

Analiza un archivo CSV de incidencias postventa y retorna métricas completas.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: Archivo CSV con incidencias

**Response:** `AnalysisResponse` (JSON)

```json
{
  "total_procesados": 10,
  "total_validos": 10,
  "total_invalidos": 0,
  "registros_invalidos": [],
  "por_categoria": [
    {
      "categoria": "calidad_comida",
      "cantidad": 4,
      "porcentaje": 40.0
    }
  ],
  "por_estado": [
    {
      "estado": "cerrado",
      "cantidad": 5,
      "porcentaje": 50.0
    }
  ],
  "por_pais": [
    {
      "pais": "CO",
      "pais_nombre": "Colombia",
      "cantidad": 6,
      "porcentaje": 60.0
    }
  ],
  "satisfaccion_promedio": 3.6,
  "satisfaccion_evaluacion": "BUENO"
}
```

## Uso

### Con curl

```bash
curl -X POST "http://localhost:8000/incidents/analyze" \
  -F "file=@incidents.csv"
```

### Con Python (requests)

```python
import requests

with open('incidents.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/incidents/analyze',
        files={'file': ('incidents.csv', f, 'text/csv')}
    )
    data = response.json()
```

### Con JavaScript (fetch)

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/incidents/analyze', {
  method: 'POST',
  body: formData
});
const data = await response.json();
```

## Iniciar el Servidor

```bash
cd apps/ats-api
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

El servidor estará disponible en `http://localhost:8000`

Documentación interactiva: `http://localhost:8000/docs`

## Validaciones

El endpoint valida automáticamente:
- Formato de archivo (debe ser .csv)
- Codificación (debe ser UTF-8)
- Campos obligatorios
- Categorías, estados, países y locales permitidos
- Formato de fechas (YYYY-MM-DD)
- Rangos de satisfacción (1-5)
- Reglas de negocio (ej: estado "cerrado" requiere satisfacción)

Ver especificaciones completas en [`docs/BRIEFING_INCIDENCIAS.md`](../../docs/BRIEFING_INCIDENCIAS.md)

## Health Check

```bash
curl http://localhost:8000/incidents/health
```

Respuesta:
```json
{
  "status": "ok",
  "service": "Incidents Analysis API",
  "version": "1.0.0"
}
```

---

**Implementado:** Fase 2 - Backend API  
**Pendiente:** Fase 3 - Frontend UI (Next.js)
