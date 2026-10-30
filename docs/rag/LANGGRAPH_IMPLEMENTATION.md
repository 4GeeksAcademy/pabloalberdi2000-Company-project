# Sistema RAG con LangGraph - Grafo de Estados Explícito

**Fecha**: 30 de Octubre, 2026  
**Versión**: 1.0  
**Estado**: ✅ Implementado

---

## 📋 Resumen Ejecutivo

Se ha implementado exitosamente el **sistema RAG como grafo de estados explícito usando LangGraph**, transformando el flujo de "caja negra" en una máquina de estados auditable y trazable.

### Problema Resuelto
El sistema RAG original (`query()`) funcionaba como caja negra sin visibilidad de:
- Decisiones intermedias
- Transiciones de estado
- Metadata de observabilidad
- Puntos de fallo específicos

### Solución Implementada
Grafo de estados LangGraph que modela explícitamente:
- **Nodos**: `retrieve`, `generate`, `no_context`, `error`
- **Routing**: Decisión condicional basada en presencia de contexto
- **Estado**: Schema mínimo con metadata acumulativa
- **Reutilización**: Sin duplicar lógica de `rag_query.py`

---

## 🏗️ Arquitectura del Grafo

### Estructura Visual

```
┌─────────────────────────────────────────────────────────┐
│                      START                               │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │   retrieve_node     │
            │ - Ejecuta retrieve()│
            │ - Actualiza context │
            │ - Metadata: scores  │
            └─────────┬───────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │  should_generate    │
            │     (Router)        │
            └─────────┬───────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
  [context?]    [no context]   [error?]
        │             │             │
        ▼             ▼             ▼
┌──────────────┐ ┌─────────────┐ ┌──────────┐
│generate_node │ │no_context   │ │error_node│
│- generate_   │ │- Respuesta  │ │- Manejo  │
│  answer()    │ │  honesta    │ │  de error│
└──────┬───────┘ └──────┬──────┘ └────┬─────┘
       │                │              │
       └────────────────┼──────────────┘
                        │
                        ▼
                   ┌────────┐
                   │  END   │
                   └────────┘
```

---

## 📊 Schema de Estado (RAGState)

### Definición TypedDict

```python
class RAGState(TypedDict):
    """Estado mínimo para el flujo RAG."""
    question: str  # Pregunta del usuario
    context: Optional[List[Dict[str, Any]]]  # Chunks recuperados
    answer: Optional[str]  # Respuesta generada
    error: Optional[str]  # Mensaje de error (si ocurre)
    metadata: Annotated[Dict[str, Any], add]  # Accumulator para observabilidad
```

### Justificación de Campos

| Campo | Tipo | Propósito | ¿Por qué está? |
|-------|------|-----------|----------------|
| `question` | `str` | Entrada del usuario | Necesario para retrieve y generate |
| `context` | `Optional[List]` | Chunks recuperados | Decisión de routing (generate vs no_context) |
| `answer` | `Optional[str]` | Respuesta final | Output del grafo |
| `error` | `Optional[str]` | Mensaje de error | Routing a error_node |
| `metadata` | `Dict` (accumulator) | Observabilidad | Trazabilidad de decisiones (scores, tiempos, sources) |

**PROHIBIDO**: Arrastrar `history`, `messages`, `full_conversation` sin justificación técnica.

---

## 🎯 Nodos del Grafo

### 1. retrieve_node

**Propósito**: Recuperar chunks relevantes desde Qdrant.

**Reutilización**: Importa y ejecuta `data.pipelines.rag_query.retrieve()`

**Input**:
```python
{
    "question": "¿Cuántos locales tiene Brasaland?",
    "context": None,
    "answer": None,
    "error": None,
    "metadata": {}
}
```

**Output**:
```python
{
    "question": "¿Cuántos locales tiene Brasaland?",
    "context": [
        {
            "text": "Brasaland tiene 14 locales...",
            "source_document": "01-company-overview.md",
            "similarity_score": 0.92
        }
    ],
    "answer": None,
    "error": None,
    "metadata": {
        "num_chunks_retrieved": 1,
        "sources": ["01-company-overview.md"],
        "avg_similarity_score": 0.92
    }
}
```

**Transición**: Siempre → Router (`should_generate`)

---

### 2. generate_node

**Propósito**: Generar respuesta con LLM a partir del contexto.

**Reutilización**: Importa y ejecuta `data.pipelines.rag_query.generate_answer()`

**Input** (desde retrieve_node):
```python
{
    "question": "¿Cuántos locales tiene Brasaland?",
    "context": [...],  # Chunks recuperados
    "answer": None,
    "error": None,
    "metadata": {...}
}
```

**Output**:
```python
{
    "question": "¿Cuántos locales tiene Brasaland?",
    "context": [...],
    "answer": "Brasaland tiene 14 locales en total: 10 en Colombia y 4 en Estados Unidos.",
    "error": None,
    "metadata": {
        ...,
        "answer_length": 85,
        "context_used": True
    }
}
```

**Transición**: Siempre → END

---

### 3. no_context_node (handle_no_context_node)

**Propósito**: Generar respuesta honesta cuando no hay contexto relevante.

**Comportamiento**: NO alucina, informa falta de información.

**Input**:
```python
{
    "question": "¿Cuál es el precio del menú ejecutivo?",
    "context": [],  # Vacío (ningún chunk sobre min_score)
    "answer": None,
    "error": None,
    "metadata": {}
}
```

**Output**:
```python
{
    "question": "¿Cuál es el precio del menú ejecutivo?",
    "context": [],
    "answer": "No tengo información suficiente en la base de conocimiento...",
    "error": None,
    "metadata": {
        "context_used": False,
        "fallback_reason": "no_context_above_threshold"
    }
}
```

**Transición**: Siempre → END

---

### 4. error_node

**Propósito**: Manejo centralizado de errores.

**Input**:
```python
{
    "question": "...",
    "context": None,
    "answer": None,
    "error": "Error en retrieve: Connection timeout",
    "metadata": {"error_stage": "retrieve"}
}
```

**Output**:
```python
{
    "question": "...",
    "context": None,
    "answer": "Lo siento, ocurrió un error al procesar tu consulta: ...",
    "error": "Error en retrieve: Connection timeout",
    "metadata": {
        "error_stage": "retrieve",
        "handled_error": True
    }
}
```

**Transición**: Siempre → END

---

## 🔀 Routing (should_generate)

**Función**: Decide la transición desde `retrieve_node`.

**Lógica**:

```python
def should_generate(state: RAGState) -> str:
    if state.get("error"):
        return "error"  # Error ocurrido → error_node
    
    if state.get("context") and len(state["context"]) > 0:
        return "generate"  # Hay contexto → generate_node
    else:
        return "no_context"  # Sin contexto → no_context_node
```

**Tabla de Decisión**:

| Condición | Transición | Nodo Destino |
|-----------|------------|--------------|
| `error` presente | `"error"` | `error_node` |
| `context` no vacío | `"generate"` | `generate_node` |
| `context` vacío | `"no_context"` | `no_context_node` |

---

## 🔧 API Endpoints

### POST /knowledge-graph/query

**Request**:
```json
{
  "question": "¿Cuántos locales tiene Brasaland?"
}
```

**Response**:
```json
{
  "answer": "Brasaland tiene 14 locales en total: 10 en Colombia y 4 en Estados Unidos.",
  "question": "¿Cuántos locales tiene Brasaland?",
  "metadata": {
    "num_chunks_retrieved": 2,
    "sources": ["01-company-overview.md"],
    "avg_similarity_score": 0.89,
    "answer_length": 85,
    "context_used": true
  },
  "error": null
}
```

**Ventajas sobre `/knowledge/query`**:
- ✅ **Metadata de observabilidad**: Sources, scores, número de chunks
- ✅ **Trazabilidad**: Saber si usó contexto o fue fallback
- ✅ **Auditoría**: Identificar stage de error si falla
- ✅ **Debugging**: Información granular para troubleshooting

---

### GET /knowledge-graph/structure

**Response**:
```json
{
  "nodes": ["retrieve", "generate", "no_context", "error"],
  "edges": [
    {"from": "START", "to": "retrieve"},
    {"from": "retrieve", "to": "generate", "condition": "context_not_empty"},
    {"from": "retrieve", "to": "no_context", "condition": "context_empty"},
    {"from": "retrieve", "to": "error", "condition": "error_occurred"},
    {"from": "generate", "to": "END"},
    {"from": "no_context", "to": "END"},
    {"from": "error", "to": "END"}
  ],
  "description": "Grafo de estados para flujo RAG..."
}
```

**Uso**: Visualización en UI, documentación automática.

---

## 🧪 Tests Unitarios

### Cobertura (18 tests)

| Categoría | Tests | Descripción |
|-----------|-------|-------------|
| **Nodos** | 6 | retrieve_node (success, no_context, error), generate_node (success, error), handle_no_context_node |
| **Routing** | 3 | should_generate con contexto, sin contexto, con error |
| **Integración** | 3 | Flujo completo con contexto, sin contexto, con error de retrieve |
| **Estado** | 2 | Schema mínimo, metadata accumulator |
| **Reutilización** | 2 | Verifica importación de retrieve y generate_answer |
| **Error Handling** | 2 | Manejo de errores en retrieve y generate |

**Total**: 18 tests ✅

**Ejecución**:
```bash
pytest tests/pipelines/test_rag_graph.py -v
```

---

## 📈 Metadata de Observabilidad

### Campos de Metadata

| Campo | Tipo | Nodo que lo agrega | Propósito |
|-------|------|-------------------|-----------|
| `num_chunks_retrieved` | `int` | retrieve_node | Cuántos chunks se recuperaron |
| `sources` | `List[str]` | retrieve_node | Documentos fuente consultados |
| `avg_similarity_score` | `float` | retrieve_node | Score promedio de similitud |
| `answer_length` | `int` | generate_node | Longitud de respuesta generada |
| `context_used` | `bool` | generate_node / no_context_node | Si se usó contexto o fue fallback |
| `fallback_reason` | `str` | no_context_node | Por qué se usó fallback |
| `error_stage` | `str` | retrieve_node / generate_node | En qué stage ocurrió el error |
| `handled_error` | `bool` | error_node | Si el error fue manejado |

### Ejemplo de Metadata Completa

```python
{
    "num_chunks_retrieved": 3,
    "sources": ["01-company-overview.md", "02-departments-operations.md"],
    "avg_similarity_score": 0.87,
    "answer_length": 142,
    "context_used": True
}
```

---

## 🔄 Reutilización de Código

### Principio: NO Duplicar Lógica

**CORRECTO** ✅:
```python
# rag_graph.py
from data.pipelines.rag_query import retrieve, generate_answer

def retrieve_node(state: RAGState) -> RAGState:
    context = retrieve(state["question"])  # Reutiliza
    return {...}

def generate_node(state: RAGState) -> RAGState:
    answer = generate_answer(state["question"], state["context"])  # Reutiliza
    return {...}
```

**INCORRECTO** ❌:
```python
# rag_graph.py
def retrieve_node(state: RAGState) -> RAGState:
    # ❌ Duplicar lógica de Qdrant aquí
    client = QdrantClient(...)
    result = client.search(...)
    ...
```

**Garantía**: Test unitarios verifican que se importan las funciones originales.

---

## 🚀 Ejecución

### CLI

```bash
# Demo con preguntas de ejemplo
python data/pipelines/rag_graph.py

# Pregunta específica
python data/pipelines/rag_graph.py "¿Quién es el CEO de Brasaland?"
```

**Output**:
```
======================================================================
🚀 Ejecutando RAG Graph para: '¿Quién es el CEO de Brasaland?'
======================================================================

[RETRIEVE_NODE] Recuperando contexto para: '¿Quién es el CEO de Brasaland?'
🔍 Recuperados 2 chunks (k=5, min_score=0.7)
  [1] 01-company-overview.md (score: 0.924)
  [2] 02-departments-operations.md (score: 0.812)
[RETRIEVE_NODE] ✅ Recuperados 2 chunks

[GENERATE_NODE] Generando respuesta con 2 chunks
🤖 Generando respuesta...
[GENERATE_NODE] ✅ Respuesta generada (95 caracteres)

======================================================================
✅ RAG Graph completado
======================================================================

📊 Metadata de Ejecución:
  - num_chunks_retrieved: 2
  - sources: ['01-company-overview.md', '02-departments-operations.md']
  - avg_similarity_score: 0.868
  - answer_length: 95
  - context_used: True

💬 Respuesta:
El CEO de Brasaland es Mariana Restrepo, hija del fundador. Asumió el cargo en 2019.
```

### API

```bash
# Consulta con grafo
curl -X POST http://localhost:8000/knowledge-graph/query \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Cuántos locales tiene Brasaland?"}'

# Estructura del grafo
curl http://localhost:8000/knowledge-graph/structure
```

---

## 🔍 Comparación: Original vs. LangGraph

| Aspecto | `/knowledge/query` (Original) | `/knowledge-graph/query` (LangGraph) |
|---------|-------------------------------|--------------------------------------|
| **Trazabilidad** | ❌ Caja negra | ✅ Estados explícitos |
| **Metadata** | ❌ Solo answer + question | ✅ Observabilidad completa |
| **Debugging** | ❌ Difícil identificar stage de fallo | ✅ Error stage en metadata |
| **Auditoría** | ❌ Sin logs de decisiones | ✅ Transiciones auditables |
| **Extensibilidad** | ❌ Difícil agregar re-ranking | ✅ Agregar nodos fácilmente |
| **Performance** | ✅ Más rápido (sin overhead) | ⚠️ Overhead mínimo de grafo |
| **Uso** | ✅ Producción actual | ✅ Producción + observabilidad |

**Recomendación**:
- **Producción**: Usar `/knowledge-graph/query` (observabilidad)
- **Performance crítico**: Usar `/knowledge/query` (más rápido)

---

## 🎯 Próximas Capacidades (Roadmap)

Con el grafo como base, se pueden agregar fácilmente:

### 1. Re-ranking Node
```
retrieve → re_rank → generate
```
- Reordenar chunks con modelo de re-ranking
- Mejorar precision sin aumentar k

### 2. Query Routing
```
         ┌→ factual_retrieve → generate
START → route_query
         └→ conversational_retrieve → generate
```
- Detectar tipo de pregunta (factual, conversacional, navegacional)
- Routing a estrategias específicas

### 3. Fallback Chains
```
retrieve → [no context] → web_search → generate
```
- Si no hay contexto en knowledge base, buscar en web
- Escalamiento graceful

### 4. Multi-hop Reasoning
```
retrieve → generate_subquestions → retrieve_each → aggregate → generate
```
- Descomponer preguntas complejas
- Responder cada sub-pregunta
- Agregar respuestas

### 5. Human-in-the-Loop
```
retrieve → [low confidence] → request_human_approval → generate
```
- Si avg_similarity_score < threshold, pedir confirmación
- Evitar respuestas de baja confianza

---

## ✅ Checklist de Implementación

- [x] Schema de estado mínimo (RAGState TypedDict)
- [x] Nodo retrieve_node reutiliza retrieve()
- [x] Nodo generate_node reutiliza generate_answer()
- [x] Nodo no_context_node (respuesta honesta)
- [x] Nodo error_node (manejo de errores)
- [x] Router should_generate (decisión condicional)
- [x] Grafo compilado con LangGraph
- [x] Función pública query_with_graph()
- [x] Endpoint `/knowledge-graph/query`
- [x] Endpoint `/knowledge-graph/structure`
- [x] Tests unitarios (18 tests)
- [x] Metadata de observabilidad
- [x] Documentación completa

---

## 📚 Referencias

- **Código**: `data/pipelines/rag_graph.py`
- **API**: `services/api/app/routers/knowledge_graph.py`
- **Tests**: `tests/pipelines/test_rag_graph.py`
- **Diseño RAG original**: `docs/rag/rag-design.md`

---

**Implementado por**: Claude Sonnet 4.5  
**Fecha**: 30 de Octubre, 2026  
**Estado**: ✅ Production-Ready con Observabilidad Completa
