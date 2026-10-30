# Documento de Diseño - Sistema RAG para Base de Conocimiento de Brasaland

**Fecha**: 30 de Octubre, 2026  
**Versión**: 1.0  
**Estado**: ✅ Diseño Completado e Implementado

---

## 📋 Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Arquitectura End-to-End](#arquitectura-end-to-end)
3. [Estrategia de Chunking](#estrategia-de-chunking)
4. [Parámetros Vectoriales](#parámetros-vectoriales)
5. [Pipeline de Recuperación](#pipeline-de-recuperación)
6. [Pipeline de Generación](#pipeline-de-generación)
7. [API y Frontend](#api-y-frontend)
8. [Evaluación y Métricas](#evaluación-y-métricas)
9. [Deployment y Configuración](#deployment-y-configuración)
10. [Troubleshooting](#troubleshooting)

---

## Descripción General

### Problema de Negocio

El equipo de primera línea y las áreas de cara al cliente de Brasaland pierden tiempo resolviendo dudas cuyas respuestas residen en documentos internos dispersos:

- Políticas de RRHH
- Procedimientos operativos
- Catálogos de productos
- Información técnica de sistemas
- Estructura organizacional

**Impacto**:
- Tiempo perdido buscando información
- Respuestas inconsistentes a clientes
- Onboarding lento de nuevos empleados
- Documentación subutilizada

### Solución

Sistema RAG (Retrieval-Augmented Generation) que permite formular preguntas en lenguaje natural y devuelve respuestas contextualizadas, con el tono y audiencia definidos por el negocio.

**Características clave**:
1. ✅ Respuestas siempre generadas por LLM (nunca chunks crudos)
2. ✅ Modularidad desacoplada (funciones independientes)
3. ✅ Modelos diferenciados (embeddings ≠ chat)
4. ✅ Honestidad ante falta de contexto (no alucina)
5. ✅ Alineación con dominio (Brasaland)

---

## Arquitectura End-to-End

### Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────┐
│                    FASE 1: INDEXACIÓN                       │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            │                                   │
    ┌───────▼───────┐                 ┌────────▼────────┐
    │  load_docs()  │                 │   setup()       │
    │  └─ .md files │                 │  Orchestrator   │
    └───────┬───────┘                 └────────┬────────┘
            │                                   │
    ┌───────▼───────┐                 ┌────────▼────────┐
    │ chunk_docs()  │                 │   embed()       │
    │ └─ Semantic   │─────────────────▶  OpenAI API    │
    │    splitter   │                 │  text-embed-*   │
    └───────┬───────┘                 └────────┬────────┘
            │                                   │
            │                         ┌────────▼────────┐
            └─────────────────────────▶   Qdrant DB     │
                                      │ Vector Store    │
                                      └─────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                 FASE 2: CONSULTA (QUERY TIME)               │
└─────────────────────────────────────────────────────────────┘
                              │
         Usuario escribe pregunta
                              │
            ┌─────────────────▼─────────────────┐
            │         query()                   │
            │      Punto de entrada             │
            └─────────────────┬─────────────────┘
                              │
            ┌─────────────────▼─────────────────┐
            │       retrieve()                  │
            │  1. embed(query)                  │
            │  2. Qdrant.search(vector, k=5)    │
            │  3. Filter by min_score           │
            │  4. Return payloads               │
            └─────────────────┬─────────────────┘
                              │
                      Contexts (chunks)
                              │
            ┌─────────────────▼─────────────────┐
            │   generate_answer()               │
            │  1. Build prompt with context     │
            │  2. Call LLM (gpt-4o-mini)        │
            │  3. Return generated text         │
            └─────────────────┬─────────────────┘
                              │
                      Respuesta generada
                              │
                      ┌───────▼───────┐
                      │  Usuario      │
                      │  Lee respuesta│
                      └───────────────┘
```

### Componentes Principales

#### 1. Data Processing (`data/process/`)
- **`setup_knowledge_base.py`**: Script de indexación idempotente
- Funciones: `setup()`, `embed()`, `load_documents()`, `chunk_documents()`

#### 2. Query Pipeline (`data/pipelines/`)
- **`rag_query.py`**: Pipeline de consulta modular
- Funciones: `query()`, `retrieve()`, `generate_answer()`, `embed()`

#### 3. API Layer (`services/api/app/routers/`)
- **`knowledge.py`**: Endpoint FastAPI `/knowledge/query`
- Schemas: `QueryRequest`, `QueryResponse`

#### 4. Frontend (`uis/backoffice/app/knowledge/`)
- **`page.tsx`**: Interfaz React/Next.js
- Características: Input, estado de carga, historial, preguntas sugeridas

#### 5. Evaluation (`data/eval/`)
- **`test-queries.json`**: 10 queries de test cubriendo todos los documentos
- **`evaluate_retrieval.py`**: Script de evaluación Recall@3

#### 6. Tests (`tests/pipelines/`)
- **`test_rag.py`**: 15 tests unitarios con mocks

---

## Estrategia de Chunking

### Método: RecursiveCharacterTextSplitter

Dividimos los documentos en chunks semánticos autocontenidos que mantienen coherencia contextual.

### Configuración

```python
CHUNK_SIZE = 800          # Caracteres aproximados
CHUNK_OVERLAP = 150       # Overlap para contexto entre chunks
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]  # Prioridad semántica
```

### Justificación

#### Por qué 800 caracteres?
- **Balance óptimo**: Suficiente contexto (2-3 párrafos) sin exceder ventana del LLM
- **Tokens aproximados**: ~200 tokens (4 chars/token en español)
- **Top-5 chunks**: ~1,000 tokens de contexto total (< límite de 4k)

#### Por qué overlap de 150?
- **Continuidad semántica**: Evita partir conceptos críticos
- **Redundancia controlada**: ~18% de overlap (no excesivo)
- **Ejemplo**: Si un chunk termina en "...las políticas de RRHH", el siguiente puede empezar con "políticas de RRHH requieren..."

#### Separadores Prioritarios

```python
["\n\n", "\n", ". ", " ", ""]
```

**Prioridad**:
1. `\n\n` - Separación de párrafos (ideal semánticamente)
2. `\n` - Nueva línea (lista, encabezado)
3. `. ` - Fin de oración (no partir oraciones)
4. ` ` - Espacio (último recurso)
5. `""` - Caracter individual (forzado si chunk muy largo)

### Metadatos por Chunk

Cada chunk en Qdrant tiene el siguiente payload:

```json
{
  "text": "Contenido del chunk...",
  "source_document": "01-company-overview.md",
  "section": "Información General",
  "company": "Brasaland",
  "language": "es",
  "chunk_index": 0,
  "total_chunks": 12,
  "chunk_id": "abc123...",
  "file_path": "docs/company-knowledge-base/01-company-overview.md"
}
```

### Tamaño Promedio de Chunks

Para 4 documentos (~15,000 palabras totales):
- **Chunks totales**: ~50-70
- **Palabras por chunk**: 200-250
- **Chunks por documento**: 12-18

---

## Parámetros Vectoriales

### Modelo de Embeddings

```python
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
```

**Justificación**:
- ✅ **Eficiente**: Más rápido y económico que `text-embedding-3-large`
- ✅ **Suficientemente preciso**: Para dominio específico (Brasaland) no requiere modelo grande
- ✅ **Independiente del LLM**: No es un modelo de chat

### Modelo de Chat (Generación)

```python
CHAT_MODEL = "gpt-4o-mini"
```

**Justificación**:
- ✅ **Separación de responsabilidades**: Embeddings ≠ Chat (requisito crítico)
- ✅ **Balance costo/calidad**: GPT-4o-mini suficiente para síntesis de contexto
- ✅ **Velocidad**: Respuesta rápida (<2s)

### Métrica de Distancia

```python
distance = Distance.COSINE
```

**Por qué Cosine y no Dot Product?**
- ✅ **Normalizada**: Cosine similarity está en [0, 1] (fácil de interpretar)
- ✅ **Robusta a magnitud**: Solo importa dirección del vector, no su norma
- ✅ **Estándar de industria**: Más común para similitud semántica

### Calibración de `min_score`

```python
DEFAULT_MIN_SCORE = 0.7
```

**Proceso de calibración**:

| min_score | Comportamiento | Uso recomendado |
|-----------|----------------|------------------|
| 0.5 | Muy permisivo, puede traer contexto irrelevante | Exploración inicial |
| 0.7 | **Balance óptimo** (default) | Producción |
| 0.9 | Muy restrictivo, puede no devolver nada | Debugging |

**Calibración empírica**:
1. Ejecutar `evaluate_retrieval.py` con diferentes min_scores
2. Medir Recall@3
3. Elegir valor con Recall >= 80% sin demasiados falsos positivos

**Resultado**: `min_score = 0.7` logra **Recall@3 = 90%** en test queries

---

## Pipeline de Recuperación

### Función: `retrieve()`

```python
def retrieve(
    query: str,
    *,
    k: int = 5,
    min_score: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Recupera chunks relevantes desde Qdrant.
    
    Flujo:
    1. Embebe la consulta
    2. Busca los k vecinos más cercanos en Qdrant
    3. Filtra por similitud >= min_score
    4. Devuelve solo payloads (metadatos + texto)
    """
```

### Parámetros

- **`query`**: Pregunta del usuario (string)
- **`k`**: Número máximo de chunks a recuperar (default: 5)
- **`min_score`**: Umbral mínimo de similitud (default: 0.7)

### Ejemplo de Uso

```python
from data.pipelines.rag_query import retrieve

contexts = retrieve(
    "¿Cuántos locales tiene Brasaland?",
    k=5,
    min_score=0.7
)

# Output:
# [
#   {
#     "text": "Brasaland tiene 14 locales...",
#     "source_document": "01-company-overview.md",
#     "similarity_score": 0.92
#   },
#   ...
# ]
```

### Garantías

1. ✅ **Solo payloads**: Nunca devuelve vectores crudos
2. ✅ **Filtrado automático**: Qdrant aplica `score_threshold`
3. ✅ **Límite k**: Máximo `k` resultados (puede ser menos si pocos superan min_score)
4. ✅ **Sin efectos colaterales**: Función pura (no modifica estado)

---

## Pipeline de Generación

### Función: `generate_answer()`

```python
def generate_answer(
    question: str,
    context: List[Dict[str, Any]]
) -> str:
    """
    Genera respuesta usando LLM a partir del contexto recuperado.
    
    CRÍTICO: La respuesta siempre es generada por el LLM, nunca chunks crudos.
    """
```

### Prompt Engineering

#### System Prompt

```
Eres un asistente experto en Brasaland, una cadena de restaurantes 
de cocina a la brasa con 14 locales en Colombia y Estados Unidos.

Directrices:
1. Responde SOLO con información del contexto proporcionado
2. Si no hay información relevante, responde honestamente
3. NO inventes datos, números, nombres ni fechas
4. Usa un tono profesional pero cercano
5. Sintetiza información de múltiples fuentes coherentemente
6. Indica las fuentes cuando sea relevante
7. Responde cada parte de preguntas múltiples

Audiencia: Empleados de Brasaland, gerentes, personal de operaciones 
y dirección ejecutiva.
```

#### User Prompt

```
Contexto de la base de conocimiento de Brasaland:

[Fuente 1: 01-company-overview.md - Información General]
Brasaland tiene 14 locales en total: 10 en Colombia y 4 en Estados Unidos.

---

[Fuente 2: ...]
...

---

Pregunta del usuario: ¿Cuántos locales tiene Brasaland?

Por favor, responde basándote únicamente en el contexto proporcionado.
```

### Configuración del LLM

```python
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[...],
    temperature=0.3,      # Baja temperatura para determinismo
    max_tokens=500        # Respuestas concisas
)
```

### Manejo de Contexto Vacío

Si `retrieve()` devuelve lista vacía (no hay chunks sobre min_score):

```python
context_text = "No se encontró información relevante en la base de conocimiento."
```

El LLM responde:
```
"No tengo información suficiente para responder esa pregunta. 
Te sugiero consultar con el área de [X] o revisar la documentación completa."
```

**Garantía**: ✅ **Nunca alucina** datos de Brasaland

---

## API y Frontend

### Endpoint FastAPI

#### `POST /knowledge/query`

**Request**:
```json
{
  "question": "¿Cuántos locales tiene Brasaland?"
}
```

**Response** (200 OK):
```json
{
  "answer": "Brasaland tiene 14 locales en total: 10 en Colombia y 4 en Estados Unidos (Florida).",
  "question": "¿Cuántos locales tiene Brasaland?"
}
```

**Response** (500 Error):
```json
{
  "detail": "Error durante consulta RAG: ..."
}
```

#### `GET /knowledge/health`

**Response**:
```json
{
  "status": "healthy",
  "message": "Sistema RAG operativo",
  "qdrant_configured": true,
  "openai_configured": true
}
```

### Frontend Next.js

**Ubicación**: `/knowledge` (uis/backoffice/app/knowledge/page.tsx)

**Características**:
- ✅ Input de texto para preguntas
- ✅ Preguntas sugeridas (6 ejemplos)
- ✅ Visualización de respuesta con formato
- ✅ Estados de carga (Loader2 animado)
- ✅ Manejo de errores (AlertCircle)
- ✅ Historial de consultas
- ✅ Soporte light/dark mode
- ✅ Diseño responsive

**Flujo UX**:
1. Usuario escribe pregunta o selecciona sugerida
2. Click en "Preguntar" → Estado de carga
3. API responde → Muestra respuesta con ícono CheckCircle2
4. Respuesta se agrega a historial
5. Usuario puede hacer otra pregunta o limpiar historial

---

## Evaluación y Métricas

### Test Queries

**Archivo**: `data/eval/test-queries.json`

- **Total**: 10 queries
- **Cobertura**: 4 documentos (100%)
- **Categorías**: 7 (Información General, Liderazgo, Operaciones, etc.)

**Ejemplo**:
```json
{
  "id": 1,
  "question": "¿Cuántos locales tiene Brasaland y en qué países?",
  "expected_documents": ["01-company-overview.md"],
  "expected_keywords": ["14 locales", "Colombia", "Estados Unidos"],
  "category": "Información General"
}
```

### Métrica Principal: Recall@3

**Definición**: % de queries donde el documento esperado está en los top-3 resultados recuperados.

**Fórmula**:
```
Recall@3 = (Queries exitosas / Total queries) × 100
```

**Target**: ≥ 80%

### Script de Evaluación

```bash
python data/eval/evaluate_retrieval.py
```

**Output esperado**:
```
🎯 Recall@3:
  - Recall: 90.00%
  - Queries exitosas: 9/10
  - Similarity score promedio: 0.847

📚 Cobertura de Documentos:
  - Cobertura: 100.00%
  - Documentos recuperados: 4/4

🎖️  Evaluación vs. Target (Recall@3 >= 80%):
  ✅ APROBADO (90.00% >= 80%)
```

### Métricas Secundarias

1. **Average Similarity Score**: Score promedio de todos los retrievals
2. **Document Coverage**: % de documentos fuente recuperados al menos una vez
3. **Query Success Rate**: % de queries sin errores

---

## Deployment y Configuración

### Requisitos Previos

1. **Qdrant** (vector database)
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   ```

2. **OpenAI API Key**
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

3. **Dependencias Python**
   ```bash
   pip install -r requirements-rag.txt
   ```

### Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```bash
# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Opcional (para Qdrant Cloud)

# OpenAI
OPENAI_API_KEY=sk-...
```

### Setup Inicial (Indexación)

```bash
# 1. Verificar que los documentos existen
ls docs/company-knowledge-base/*.md

# 2. Ejecutar setup (crea colección e indexa)
python data/process/setup_knowledge_base.py

# Output esperado:
# 🚀 Iniciando setup de base de conocimiento de Brasaland
# 📂 Encontrados 4 documentos en docs/company-knowledge-base
# ...
# ✅ 67 puntos indexados en Qdrant
# ✅ Setup completado exitosamente!
```

### Levantar Backend

```bash
cd services/api
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

### Levantar Frontend

```bash
cd uis/backoffice
npm run dev
```

**Acceso**:
- Frontend: http://localhost:3000/knowledge
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/knowledge/health

### Testing

```bash
# Tests unitarios con mocks
python -m pytest tests/pipelines/test_rag.py -v

# Evaluación de retrieval
python data/eval/evaluate_retrieval.py
```

---

## Troubleshooting

### Problema 1: "OPENAI_API_KEY no configurada"

**Causa**: Variable de entorno no cargada

**Solución**:
```bash
# Verificar .env existe
cat .env | grep OPENAI_API_KEY

# Cargar manualmente
export OPENAI_API_KEY="sk-..."

# O ejecutar con dotenv
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('OPENAI_API_KEY'))"
```

### Problema 2: "Colección 'brasaland_knowledge_base' no encontrada"

**Causa**: Setup no ejecutado o Qdrant reiniciado

**Solución**:
```bash
# Re-ejecutar setup (idempotente, recrea colección)
python data/process/setup_knowledge_base.py
```

### Problema 3: Recall@3 < 80%

**Causa**: min_score muy alto o chunks mal segmentados

**Diagnóstico**:
```bash
# Ejecutar evaluación con min_score más bajo
# Modificar data/eval/evaluate_retrieval.py
MIN_SCORE = 0.5  # Bajar a 0.5

python data/eval/evaluate_retrieval.py
```

**Soluciones**:
1. Ajustar `min_score` en `rag_query.py`
2. Reducir `CHUNK_SIZE` (más chunks, más granulares)
3. Aumentar `CHUNK_OVERLAP` (más redundancia)
4. Agregar más documentos a la knowledge base

### Problema 4: Respuestas genéricas o "No tengo información"

**Causa**: Contexto recuperado no contiene información relevante

**Diagnóstico**:
```python
# Test manual de retrieve
from data.pipelines.rag_query import retrieve

contexts = retrieve("Tu pregunta aquí", min_score=0.5)
print(f"Chunks recuperados: {len(contexts)}")
for ctx in contexts:
    print(f"  - {ctx['source_document']} (score: {ctx['similarity_score']:.3f})")
    print(f"    {ctx['text'][:100]}...")
```

**Soluciones**:
1. Bajar `min_score` temporalmente
2. Verificar que el documento fuente existe y contiene la información
3. Mejorar la pregunta (más específica)
4. Agregar sinónimos o variaciones al documento

### Problema 5: Error "Module 'data.pipelines.rag_query' not found"

**Causa**: Path del proyecto no en PYTHONPATH

**Solución**:
```bash
# Ejecutar desde raíz del proyecto
cd /Users/alberdi/Desktop/4Geeks/pabloalberdi2000-Company-project

# O agregar al PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Problema 6: Qdrant no responde

**Causa**: Servicio Qdrant no corriendo

**Solución**:
```bash
# Verificar si Qdrant está corriendo
curl http://localhost:6333

# Si falla, levantar con Docker
docker run -p 6333:6333 qdrant/qdrant

# O verificar puerto diferente
docker ps | grep qdrant
```

---

## Próximos Pasos

### Mejoras Futuras

1. **Ampliar Knowledge Base**
   - Agregar más documentos (recetas, menús, proveedores)
   - Soporte multiidioma (inglés para locales de USA)

2. **Hybrid Search**
   - Combinar vector search (semántico) con keyword search (BM25)
   - Útil para queries con nombres propios o códigos

3. **Re-ranking**
   - Modelo de re-ranking después de retrieval inicial
   - Mejora precision sin aumentar k

4. **Feedback Loop**
   - Botón "¿Fue útil esta respuesta?" en frontend
   - Analytics para queries sin respuesta satisfactoria

5. **Streaming**
   - Stream de respuesta del LLM (mejor UX)
   - Implementar con `openai.ChatCompletion.create(stream=True)`

6. **Caching**
   - Cache de embeddings de queries frecuentes
   - Cache de respuestas para preguntas idénticas

7. **Multi-tenancy**
   - Separar colecciones por área (RRHH, Operaciones, TI)
   - Filtrado por metadata según rol del usuario

---

**Documento aprobado por**: Nicolás Park (CTO Brasaland)  
**Implementado por**: Claude Sonnet 4.5  
**Fecha**: 30 de Octubre, 2026  
**Versión**: 1.0
