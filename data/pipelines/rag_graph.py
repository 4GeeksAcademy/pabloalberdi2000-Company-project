"""
LangGraph State Machine para Sistema RAG

Modelado explícito del flujo RAG como grafo de estados para:
- Trazabilidad completa de decisiones
- Observabilidad granular del razonamiento
- Auditoría de transiciones de estado
- Base para futuras capacidades (re-ranking, routing, etc.)

CRÍTICO: Reutiliza funciones existentes (retrieve, generate_answer) sin duplicar lógica.

Ejecución:
    python data/pipelines/rag_graph.py "¿Cuántos locales tiene Brasaland?"
"""

import sys
from pathlib import Path
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from operator import add

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

# Importar funciones RAG existentes (NO duplicar lógica)
from data.pipelines.rag_query import retrieve, generate_answer

# ============================================================
# SCHEMA DE ESTADO (Mínimo y Explícito)
# ============================================================

class RAGState(TypedDict):
    """
    Estado mínimo para el flujo RAG.

    Contiene únicamente la información imprescindible para decidir transiciones:
    - question: Pregunta del usuario
    - context: Chunks recuperados (lista de dicts con payloads)
    - answer: Respuesta generada por el LLM
    - error: Mensaje de error (si ocurre)
    - metadata: Metadatos de observabilidad (scores, tiempos, etc.)

    PROHIBIDO: Arrastrar historial conversacional completo sin justificación.
    """
    question: str
    context: Optional[List[Dict[str, Any]]]
    answer: Optional[str]
    error: Optional[str]
    metadata: Annotated[Dict[str, Any], add]  # Accumulator para observabilidad


# ============================================================
# NODOS DEL GRAFO (Funciones de Estado)
# ============================================================

def retrieve_node(state: RAGState) -> RAGState:
    """
    Nodo de recuperación: Ejecuta retrieve() y actualiza estado con contexto.

    Reutiliza: data.pipelines.rag_query.retrieve()

    Transición:
    - Si context no vacío → generate_node
    - Si context vacío → handle_no_context_node
    """
    print(f"\n[RETRIEVE_NODE] Recuperando contexto para: '{state['question']}'")

    try:
        # Reutilizar función existente
        context = retrieve(state["question"])

        # Actualizar metadata con información de recuperación
        metadata_update = {
            "num_chunks_retrieved": len(context),
            "sources": [c["source_document"] for c in context] if context else [],
            "avg_similarity_score": sum(c["similarity_score"] for c in context) / len(context) if context else 0.0
        }

        print(f"[RETRIEVE_NODE] ✅ Recuperados {len(context)} chunks")

        return {
            "question": state["question"],
            "context": context,
            "answer": None,
            "error": None,
            "metadata": metadata_update
        }

    except Exception as e:
        print(f"[RETRIEVE_NODE] ❌ Error: {e}")
        return {
            "question": state["question"],
            "context": None,
            "answer": None,
            "error": f"Error en retrieve: {str(e)}",
            "metadata": {"error_stage": "retrieve"}
        }


def generate_node(state: RAGState) -> RAGState:
    """
    Nodo de generación: Ejecuta generate_answer() con contexto recuperado.

    Reutiliza: data.pipelines.rag_query.generate_answer()

    Transición:
    - Siempre → END (respuesta generada)
    """
    print(f"\n[GENERATE_NODE] Generando respuesta con {len(state['context'])} chunks")

    try:
        # Reutilizar función existente
        answer = generate_answer(state["question"], state["context"])

        # Actualizar metadata con información de generación
        metadata_update = {
            "answer_length": len(answer),
            "context_used": True
        }

        print(f"[GENERATE_NODE] ✅ Respuesta generada ({len(answer)} caracteres)")

        return {
            "question": state["question"],
            "context": state["context"],
            "answer": answer,
            "error": None,
            "metadata": metadata_update
        }

    except Exception as e:
        print(f"[GENERATE_NODE] ❌ Error: {e}")
        return {
            "question": state["question"],
            "context": state["context"],
            "answer": None,
            "error": f"Error en generate: {str(e)}",
            "metadata": {"error_stage": "generate"}
        }


def handle_no_context_node(state: RAGState) -> RAGState:
    """
    Nodo de manejo de ausencia de contexto: Genera respuesta honesta.

    Comportamiento defensivo: No alucina, informa falta de información.

    Transición:
    - Siempre → END (respuesta de "no tengo información")
    """
    print(f"\n[NO_CONTEXT_NODE] Sin contexto relevante, generando respuesta honesta")

    # Generar respuesta honesta (sin alucinar)
    answer = (
        "No tengo información suficiente en la base de conocimiento para responder "
        "esa pregunta de manera precisa. Te sugiero:\n\n"
        "1. Reformular la pregunta con más detalles\n"
        "2. Consultar con el área correspondiente de Brasaland\n"
        "3. Revisar la documentación completa en el repositorio interno"
    )

    metadata_update = {
        "context_used": False,
        "fallback_reason": "no_context_above_threshold"
    }

    print(f"[NO_CONTEXT_NODE] ✅ Respuesta honesta generada")

    return {
        "question": state["question"],
        "context": [],
        "answer": answer,
        "error": None,
        "metadata": metadata_update
    }


def error_node(state: RAGState) -> RAGState:
    """
    Nodo de manejo de errores: Captura errores y genera respuesta de error.

    Transición:
    - Siempre → END
    """
    print(f"\n[ERROR_NODE] Manejando error: {state.get('error', 'Unknown')}")

    error_message = state.get("error", "Error desconocido en el sistema RAG")

    answer = (
        f"Lo siento, ocurrió un error al procesar tu consulta:\n\n"
        f"{error_message}\n\n"
        f"Por favor intenta nuevamente o contacta al equipo de soporte técnico."
    )

    return {
        "question": state["question"],
        "context": None,
        "answer": answer,
        "error": state.get("error"),
        "metadata": {"handled_error": True}
    }


# ============================================================
# FUNCIONES DE ROUTING (Decisión de Transiciones)
# ============================================================

def should_generate(state: RAGState) -> str:
    """
    Router: Decide si generar respuesta o manejar ausencia de contexto.

    Lógica:
    - Si context no está vacío → "generate"
    - Si context está vacío → "no_context"
    - Si hay error → "error"
    """
    if state.get("error"):
        return "error"

    if state.get("context") and len(state["context"]) > 0:
        return "generate"
    else:
        return "no_context"


# ============================================================
# CONSTRUCCIÓN DEL GRAFO
# ============================================================

def build_rag_graph() -> StateGraph:
    """
    Construye el grafo de estados para el flujo RAG.

    Estructura:
        START
          ↓
       retrieve
          ↓
       [router: should_generate]
          ├─→ generate → END (si context no vacío)
          ├─→ no_context → END (si context vacío)
          └─→ error → END (si error)

    Returns:
        Grafo compilado de LangGraph
    """
    # Crear grafo
    workflow = StateGraph(RAGState)

    # Agregar nodos
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("no_context", handle_no_context_node)
    workflow.add_node("error", error_node)

    # Definir punto de entrada
    workflow.set_entry_point("retrieve")

    # Agregar edges condicionales (routing)
    workflow.add_conditional_edges(
        "retrieve",
        should_generate,
        {
            "generate": "generate",
            "no_context": "no_context",
            "error": "error"
        }
    )

    # Agregar edges a END
    workflow.add_edge("generate", END)
    workflow.add_edge("no_context", END)
    workflow.add_edge("error", END)

    # Compilar grafo
    return workflow.compile()


# ============================================================
# FUNCIÓN PÚBLICA (Compatible con API)
# ============================================================

def query_with_graph(question: str) -> Dict[str, Any]:
    """
    Ejecuta consulta RAG usando el grafo de estados.

    Compatible con la API existente: misma firma que query() original.

    Args:
        question: Pregunta del usuario

    Returns:
        Dict con answer, metadata y traza de estados
    """
    print("=" * 70)
    print(f"🚀 Ejecutando RAG Graph para: '{question}'")
    print("=" * 70)

    # Construir grafo
    graph = build_rag_graph()

    # Estado inicial
    initial_state: RAGState = {
        "question": question,
        "context": None,
        "answer": None,
        "error": None,
        "metadata": {}
    }

    # Ejecutar grafo
    final_state = graph.invoke(initial_state)

    print("\n" + "=" * 70)
    print("✅ RAG Graph completado")
    print("=" * 70)

    # Mostrar metadata de observabilidad
    print(f"\n📊 Metadata de Ejecución:")
    for key, value in final_state.get("metadata", {}).items():
        print(f"  - {key}: {value}")

    print(f"\n💬 Respuesta:")
    print(f"{final_state['answer']}\n")

    return {
        "answer": final_state["answer"],
        "question": final_state["question"],
        "metadata": final_state.get("metadata", {}),
        "error": final_state.get("error")
    }


# ============================================================
# VISUALIZACIÓN DEL GRAFO
# ============================================================

def visualize_graph():
    """
    Genera visualización del grafo de estados.

    Requiere: graphviz instalado
    """
    graph = build_rag_graph()

    try:
        # Intentar generar visualización
        from IPython.display import Image, display

        print("📊 Generando visualización del grafo...")
        display(Image(graph.get_graph().draw_mermaid_png()))
        print("✅ Visualización generada")

    except ImportError:
        print("⚠️  IPython no disponible, mostrando estructura en texto:")
        print("\nEstructura del Grafo:")
        print("""
        START
          ↓
        retrieve_node
          ↓
        [should_generate router]
          ├─→ generate_node → END (si context no vacío)
          ├─→ no_context_node → END (si context vacío)
          └─→ error_node → END (si error)
        """)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    # Ejemplo de uso
    sample_questions = [
        "¿Cuántos locales tiene Brasaland?",
        "¿Quién es el CEO de Brasaland?",
        "¿Cuál es el precio del menú ejecutivo?"  # Pregunta sin respuesta (no_context)
    ]

    if len(sys.argv) > 1:
        # Consulta desde argumentos
        question = " ".join(sys.argv[1:])
        query_with_graph(question)
    else:
        # Demo con preguntas de ejemplo
        print("🎯 Demo de RAG Graph - LangGraph State Machine\n")

        for idx, q in enumerate(sample_questions, 1):
            print(f"\n{'='*70}")
            print(f"Pregunta {idx}/{len(sample_questions)}")
            print(f"{'='*70}")

            result = query_with_graph(q)

            if idx < len(sample_questions):
                input("\nPresiona Enter para continuar...\n")

        # Mostrar visualización
        print(f"\n{'='*70}")
        visualize_graph()
