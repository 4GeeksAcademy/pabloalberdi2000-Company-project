"""
LangGraph Agent con Tools Vivas - Multi-Source Routing

Grafo de estados que decide autónomamente:
- Cuándo consultar RAG (conocimiento estático)
- Cuándo invocar tools (datos operativos dinámicos)
- Cuándo usar ambas fuentes

CRÍTICO:
- NO indexar datos operativos en Qdrant (mutan en tiempo real)
- Tools consumen servicios reales (no mocks)
- Timeouts estrictos (3-5s)
- Fallback honesto sin alucinación
"""

import sys
from pathlib import Path
from typing import TypedDict, Annotated, Optional, List, Dict, Any, Literal
from operator import add

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langgraph.graph import StateGraph, END
import openai
import os
from dotenv import load_dotenv

# Importar funciones RAG y tools (vía MCP)
from data.pipelines.rag_query import retrieve, generate_answer
from services.agent.mcp_adapter import execute_tool, AVAILABLE_TOOLS

# Importar sistema de memoria
from services.agent.memory import (
    AgentStructuredResponse,
    MemoryProposalSchema,
    ProposalStatus,
    get_memory_manager,
    create_proposal_audit_log,
    process_approval,
    is_approval_response,
    discard_pending_proposals
)

load_dotenv()

# ============================================================
# SCHEMA DE ESTADO EXTENDIDO
# ============================================================

class AgentState(TypedDict):
    """
    Estado extendido para agente con tools y memoria.

    Campos añadidos vs. RAGState:
    - tool_data: Resultado de invocación de tool
    - tool_name: Nombre de la tool invocada
    - needs_tool: Si se detectó necesidad de tool
    - routing_decision: Qué fuente usar (rag, tool, both)
    - pending_proposal: Propuesta de memoria pendiente de aprobación
    - conversation_id: ID de conversación (para memoria contextual)
    """
    question: str                                    # Pregunta del usuario
    context: Optional[List[Dict[str, Any]]]         # Chunks de RAG
    tool_data: Optional[Dict[str, Any]]             # Resultado de tool
    tool_name: Optional[str]                        # Nombre de tool invocada
    needs_tool: Optional[bool]                      # ¿Necesita tool?
    routing_decision: Optional[str]                 # rag | tool | both
    answer: Optional[str]                           # Respuesta final
    error: Optional[str]                            # Mensaje de error
    pending_proposal: Optional[Dict[str, Any]]      # Propuesta de memoria pendiente
    conversation_id: Optional[str]                  # ID de conversación
    metadata: Annotated[Dict[str, Any], add]        # Observabilidad

# ============================================================
# NODO: Router (Decisión de Fuente)
# ============================================================

def router_node(state: AgentState) -> AgentState:
    """
    Nodo de routing: Decide qué fuente consultar según la pregunta.

    Lógica de decisión:
    - Pregunta sobre ticket/incidente/estado → tool
    - Pregunta sobre conocimiento general/políticas → rag
    - Pregunta mixta (contexto + datos vivos) → both

    Usa LLM para clasificar intent.
    """
    print(f"\n[ROUTER_NODE] Analizando intent de: '{state['question']}'")

    question = state["question"].lower()

    # Detección simple de keywords (puede mejorarse con LLM)
    tool_keywords = ["ticket", "incidente", "estado", "progreso", "id", "inventario", "stock", "producto"]
    rag_keywords = ["política", "procedimiento", "cuántos locales", "quién es", "ceo", "horario", "empleados"]

    has_tool_keyword = any(kw in question for kw in tool_keywords)
    has_rag_keyword = any(kw in question for kw in rag_keywords)

    # Decisión de routing
    if has_tool_keyword and not has_rag_keyword:
        decision = "tool"
    elif has_rag_keyword and not has_tool_keyword:
        decision = "rag"
    elif has_tool_keyword and has_rag_keyword:
        decision = "both"
    else:
        # Default: intentar RAG primero
        decision = "rag"

    print(f"[ROUTER_NODE] ✅ Decisión: {decision}")

    metadata_update = {
        "routing_decision": decision,
        "has_tool_keyword": has_tool_keyword,
        "has_rag_keyword": has_rag_keyword
    }

    return {
        "question": state["question"],
        "context": None,
        "tool_data": None,
        "tool_name": None,
        "needs_tool": has_tool_keyword,
        "routing_decision": decision,
        "answer": None,
        "error": None,
        "metadata": metadata_update
    }


# ============================================================
# NODO: Tool Calling
# ============================================================

def tool_calling_node(state: AgentState) -> AgentState:
    """
    Nodo de tool calling: Identifica y ejecuta tool apropiada.

    Extrae parámetros de la pregunta y llama a la tool.
    """
    print(f"\n[TOOL_CALLING_NODE] Procesando pregunta para tool")

    question = state["question"].lower()

    # Detectar qué tool usar y extraer parámetros
    tool_name = None
    tool_params = {}

    # Detección de get_incident_by_id
    if "ticket" in question or "incidente" in question:
        tool_name = "get_incident_by_id"

        # Extraer ID (buscar número en la pregunta)
        import re
        numbers = re.findall(r'\d+', question)
        if numbers:
            tool_params["ticket_id"] = numbers[0]
        else:
            return {
                **state,
                "tool_data": None,
                "tool_name": None,
                "error": "No se pudo extraer ID de ticket de la pregunta",
                "metadata": {"tool_error": "missing_ticket_id"}
            }

    # Detección de list_incidents
    elif "incidentes" in question and "listar" in question:
        tool_name = "list_incidents"
        # Extraer filtros si los hay
        if "abierto" in question:
            tool_params["status"] = "open"
        if "técnico" in question:
            tool_params["category"] = "técnico"

    # Detección de inventario
    elif "inventario" in question or "stock" in question or "producto" in question:
        tool_name = "get_inventory_products"
        # Extraer location_id si se menciona
        numbers = re.findall(r'\d+', question)
        if numbers:
            tool_params["location_id"] = int(numbers[0])

    else:
        return {
            **state,
            "tool_data": None,
            "tool_name": None,
            "error": "No se pudo identificar tool apropiada",
            "metadata": {"tool_error": "no_tool_match"}
        }

    print(f"[TOOL_CALLING_NODE] 🔧 Llamando tool: {tool_name} con params: {tool_params}")

    # Ejecutar tool
    try:
        result = execute_tool(tool_name, **tool_params)

        print(f"[TOOL_CALLING_NODE] ✅ Tool ejecutada: success={result.get('success')}")

        metadata_update = {
            "tool_name": tool_name,
            "tool_params": tool_params,
            "tool_success": result.get("success")
        }

        return {
            **state,
            "tool_data": result,
            "tool_name": tool_name,
            "error": None if result.get("success") else result.get("error"),
            "metadata": metadata_update
        }

    except Exception as e:
        print(f"[TOOL_CALLING_NODE] ❌ Error: {e}")
        return {
            **state,
            "tool_data": None,
            "tool_name": tool_name,
            "error": f"Error ejecutando tool: {str(e)}",
            "metadata": {"tool_error": str(e)}
        }


# ============================================================
# NODO: RAG Retrieve
# ============================================================

def rag_retrieve_node(state: AgentState) -> AgentState:
    """
    Nodo de RAG: Recupera contexto de knowledge base.

    Reutiliza retrieve() de rag_query.py
    """
    print(f"\n[RAG_RETRIEVE_NODE] Recuperando contexto para: '{state['question']}'")

    try:
        context = retrieve(state["question"])

        print(f"[RAG_RETRIEVE_NODE] ✅ Recuperados {len(context)} chunks")

        metadata_update = {
            "num_chunks_retrieved": len(context),
            "sources": [c["source_document"] for c in context] if context else []
        }

        return {
            **state,
            "context": context,
            "metadata": metadata_update
        }

    except Exception as e:
        print(f"[RAG_RETRIEVE_NODE] ❌ Error: {e}")
        return {
            **state,
            "context": [],
            "error": f"Error en RAG retrieve: {str(e)}",
            "metadata": {"rag_error": str(e)}
        }


# ============================================================
# NODO: Synthesis (Generación Final)
# ============================================================

def synthesis_node(state: AgentState) -> AgentState:
    """
    Nodo de síntesis: Genera respuesta final con propuesta de memoria (Structured Output).

    Comportamiento:
    - Construye prompt según fuentes disponibles (RAG/tool/both)
    - Usa Structured Output para generar {response_text, memory_proposal}
    - Evalúa si hay algo memorable (corrección, solución, preferencia)
    - Registra propuesta en audit log si is_memorable=True
    - Si tool failed: respuesta honesta de fallback (sin propuesta)
    """
    print(f"\n[SYNTHESIS_NODE] Generando respuesta final con evaluación de memoria")

    question = state["question"]
    context = state.get("context", [])
    tool_data = state.get("tool_data")
    routing = state.get("routing_decision")
    conversation_id = state.get("conversation_id", "unknown")

    # Recuperar memorias relevantes del metadata (si existen)
    relevant_memories = state.get("metadata", {}).get("relevant_memories", [])

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # System prompt con instrucciones de memoria
    system_prompt = """Eres un asistente de Brasaland que responde basándose en datos proporcionados, sin inventar información.

MEMORIA PERSISTENTE:
Si la conversación contiene algo que debería recordarse para futuras interacciones:

✅ RECORDAR (is_memorable=True):
- Correcciones explícitas del usuario ("en realidad es X", "no, el procedimiento correcto es Y")
- Soluciones a problemas que no están en la documentación oficial
- Preferencias explícitas del usuario sobre cómo trabajar
- Flujos de trabajo aprendidos que funcionan
- Hechos verificables del negocio confirmados por el usuario

❌ NUNCA RECORDAR (is_memorable=False):
- Datos personales (DNI, nombres completos, direcciones, teléfonos)
- Contraseñas, tokens, API keys, secrets, credentials
- Información confidencial o marcada como sensible
- Datos financieros (tarjetas, cuentas bancarias)
- Información médica o privada

Si hay algo memorable, propón recordarlo en memory_proposal con:
- content: Lo específico a recordar (corto y concreto)
- category: resolution | user_correction | workflow | preference | fact
- reason: Por qué es útil recordarlo (1 línea)

Si no hay nada memorable, memory_proposal debe ser null."""

    # Construir prompt de usuario según fuentes disponibles
    user_prompt = ""

    if routing == "tool" and tool_data:
        # Solo tool
        if tool_data.get("success"):
            data = tool_data.get("data", {})
            user_prompt = f"""Pregunta del usuario: {question}

Datos operativos obtenidos de la tool '{state.get('tool_name')}':
{data}

Responde basándote ÚNICAMENTE en estos datos operativos. Sé conciso y directo."""

        else:
            # Tool falló - respuesta honesta sin propuesta de memoria
            error = tool_data.get("error", "Error desconocido")
            answer = f"Lo siento, no pude obtener esa información en este momento. Error: {error}"

            print(f"[SYNTHESIS_NODE] ⚠️  Tool falló, respuesta honesta (sin memoria)")

            return {
                **state,
                "answer": answer,
                "pending_proposal": None,
                "metadata": {**state.get("metadata", {}), "synthesis_type": "tool_fallback"}
            }

    elif routing == "rag" and context:
        # Solo RAG
        context_text = "\n\n".join([c["text"] for c in context[:3]])
        user_prompt = f"""Pregunta del usuario: {question}

Contexto de la base de conocimiento (documentos internos):
{context_text}

Responde basándote en este contexto."""

    elif routing == "both":
        # Combinar RAG + tool
        context_text = "\n\n".join([c["text"] for c in context[:3]]) if context else "No hay contexto de documentos."
        tool_text = str(tool_data.get("data", {})) if tool_data and tool_data.get("success") else "No hay datos operativos disponibles."

        user_prompt = f"""Pregunta del usuario: {question}

Contexto de la base de conocimiento (documentos internos):
{context_text}

Datos operativos en tiempo real:
{tool_text}

Responde combinando información de ambas fuentes cuando sea apropiado."""

    else:
        # Sin fuentes (fallback)
        answer = "No tengo información suficiente para responder esa pregunta en este momento."

        print(f"[SYNTHESIS_NODE] ⚠️  Sin fuentes disponibles")

        return {
            **state,
            "answer": answer,
            "pending_proposal": None,
            "metadata": {**state.get("metadata", {}), "synthesis_type": "no_sources"}
        }

    # Agregar memorias relevantes al contexto (si existen)
    if relevant_memories:
        memories_text = "\n".join([f"- {m['content']}" for m in relevant_memories])
        user_prompt += f"\n\nMemorias relevantes de interacciones previas:\n{memories_text}"

    # Llamar a LLM con Structured Output
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=AgentStructuredResponse,
            temperature=0.3,
            max_tokens=500
        )

        structured_response = response.choices[0].message.parsed

        print(f"[SYNTHESIS_NODE] ✅ Respuesta estructurada generada")

        # Procesar propuesta de memoria si existe
        pending_proposal = None
        if structured_response.memory_proposal and structured_response.memory_proposal.is_memorable:
            proposal = structured_response.memory_proposal

            # Validar políticas negativas
            is_valid, reject_reason = proposal.validate_negative_policies()

            if is_valid:
                # Registrar propuesta como PENDING en audit log
                memory_manager = get_memory_manager()
                audit_log = create_proposal_audit_log(
                    proposal=proposal,
                    status=ProposalStatus.PENDING,
                    conversation_id=conversation_id
                )
                memory_manager.log_proposal(audit_log)

                pending_proposal = {
                    "id": audit_log.id,
                    "content": proposal.content,
                    "category": proposal.category,
                    "reason": proposal.reason
                }

                print(f"[SYNTHESIS_NODE] 💡 Propuesta de memoria creada: {audit_log.id}")
                print(f"  Categoría: {proposal.category}")
                print(f"  Contenido: {proposal.content[:50]}...")
            else:
                print(f"[SYNTHESIS_NODE] ⚠️  Propuesta rechazada por política negativa: {reject_reason}")

        return {
            **state,
            "answer": structured_response.response_text,
            "pending_proposal": pending_proposal,
            "metadata": {
                **state.get("metadata", {}),
                "synthesis_type": routing,
                "has_memory_proposal": pending_proposal is not None,
                "used_memories_count": len(relevant_memories)
            }
        }

    except Exception as e:
        print(f"[SYNTHESIS_NODE] ❌ Error: {e}")
        answer = f"Lo siento, ocurrió un error al generar la respuesta: {str(e)}"
        return {
            **state,
            "answer": answer,
            "pending_proposal": None,
            "error": str(e),
            "metadata": {**state.get("metadata", {}), "synthesis_error": str(e)}
        }


# ============================================================
# ROUTING FUNCTIONS
# ============================================================

def should_call_tool(state: AgentState) -> Literal["tool", "rag", "both"]:
    """
    Router: Decide transición desde router_node.
    """
    decision = state.get("routing_decision", "rag")
    return decision


def should_synthesize(state: AgentState) -> Literal["synthesis"]:
    """
    Router: Siempre va a synthesis después de tool o rag.
    """
    return "synthesis"


# ============================================================
# CONSTRUCCIÓN DEL GRAFO
# ============================================================

def build_agent_graph() -> StateGraph:
    """
    Construye el grafo del agente con tools.

    Flujo:
        START
          ↓
        router (decide: rag | tool | both)
          ├─→ tool_calling → synthesis → END
          ├─→ rag_retrieve → synthesis → END
          └─→ both → tool_calling + rag_retrieve → synthesis → END
    """
    workflow = StateGraph(AgentState)

    # Agregar nodos
    workflow.add_node("router", router_node)
    workflow.add_node("tool_calling", tool_calling_node)
    workflow.add_node("rag_retrieve", rag_retrieve_node)
    workflow.add_node("synthesis", synthesis_node)

    # Entry point
    workflow.set_entry_point("router")

    # Edges condicionales desde router
    workflow.add_conditional_edges(
        "router",
        should_call_tool,
        {
            "tool": "tool_calling",
            "rag": "rag_retrieve",
            "both": "tool_calling"  # En "both" hacemos tool primero, luego rag
        }
    )

    # Tool → synthesis
    workflow.add_edge("tool_calling", "synthesis")

    # RAG → synthesis
    workflow.add_edge("rag_retrieve", "synthesis")

    # Synthesis → END
    workflow.add_edge("synthesis", END)

    # TODO: Para "both", después de tool_calling, deberíamos ir a rag_retrieve
    # Esto requiere un edge condicional adicional o un nodo intermedio
    # Por simplicidad, actualmente "both" solo hace tool

    return workflow.compile()


# ============================================================
# FUNCIÓN PÚBLICA
# ============================================================

def query_with_agent(question: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Ejecuta consulta con agente multi-source + memoria.

    Args:
        question: Pregunta del usuario
        conversation_id: ID de conversación (para memoria contextual). Si None, se genera uno nuevo.

    Returns:
        Dict con answer, metadata, pending_proposal y trace
    """
    import uuid

    # Generar conversation_id si no se proporciona
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    print("=" * 70)
    print(f"🤖 Ejecutando Agent Graph para: '{question}'")
    print(f"📝 Conversation ID: {conversation_id[:8]}...")
    print("=" * 70)

    # Obtener gestor de memoria
    memory_manager = get_memory_manager()

    # Verificar si hay propuestas pendientes en esta conversación
    pending_proposals = memory_manager.get_pending_proposals(conversation_id)

    # Si hay propuesta pendiente Y usuario está respondiendo a ella
    if pending_proposals and is_approval_response(question):
        # Usuario está respondiendo a la propuesta
        proposal = pending_proposals[0]  # Tomar la más reciente
        proposal_id = proposal.get("id")

        print(f"\n📋 Detectada respuesta a propuesta {proposal_id[:8]}...")
        print("⚙️  Procesando decisión del usuario...\n")

        # Procesar aprobación/rechazo
        result = process_approval(
            proposal_id=proposal_id,
            user_response=question,
            user_id="current_user",  # TODO: Obtener del contexto de autenticación
            memory_manager=memory_manager,
            conversation_id=conversation_id
        )

        # Retornar directamente sin ejecutar el grafo
        print("=" * 70)
        print(result["message"])
        print("=" * 70 + "\n")

        return {
            "answer": result["message"],
            "question": question,
            "metadata": {
                "conversation_id": conversation_id,
                "is_approval_response": True,
                "approval_status": result["status"],
                "proposal_id": proposal_id
            },
            "error": None,
            "routing_decision": None,
            "tool_used": None,
            "pending_proposal": None,
            "conversation_id": conversation_id
        }

    # Si hay propuestas pendientes pero usuario NO está respondiendo → descartar
    if pending_proposals and not is_approval_response(question):
        discarded_count = discard_pending_proposals(
            conversation_id=conversation_id,
            memory_manager=memory_manager,
            reason="user_changed_topic"
        )

        if discarded_count > 0:
            print(f"\n⚠️  {discarded_count} propuesta(s) pendiente(s) descartada(s) (cambio de tema)\n")

    # Recuperar memorias relevantes antes de ejecutar el grafo
    relevant_memories = memory_manager.read_memories(
        query=question,
        limit=3,
        min_score=0.75
    )

    if relevant_memories:
        print(f"\n💾 Memorias relevantes recuperadas: {len(relevant_memories)}")
        for mem in relevant_memories:
            print(f"  - [{mem['category']}] {mem['content'][:60]}... (score: {mem['score']:.2f})")

    graph = build_agent_graph()

    initial_state: AgentState = {
        "question": question,
        "context": None,
        "tool_data": None,
        "tool_name": None,
        "needs_tool": None,
        "routing_decision": None,
        "answer": None,
        "error": None,
        "pending_proposal": None,
        "conversation_id": conversation_id,
        "metadata": {
            "conversation_id": conversation_id,
            "relevant_memories": relevant_memories
        }
    }

    final_state = graph.invoke(initial_state)

    print("\n" + "=" * 70)
    print("✅ Agent Graph completado")
    print("=" * 70)

    print(f"\n📊 Metadata:")
    for key, value in final_state.get("metadata", {}).items():
        if key != "relevant_memories":  # No imprimir las memorias completas
            print(f"  - {key}: {value}")

    print(f"\n💬 Respuesta:")
    print(f"{final_state['answer']}\n")

    # Si hay propuesta de memoria, mostrarla al usuario
    if final_state.get("pending_proposal"):
        proposal = final_state["pending_proposal"]
        print("=" * 70)
        print("💡 PROPUESTA DE MEMORIA")
        print("=" * 70)
        print(f"📝 Contenido: {proposal['content']}")
        print(f"🏷️  Categoría: {proposal['category']}")
        print(f"💭 Razón: {proposal['reason']}")
        print(f"🆔 Proposal ID: {proposal['id']}")
        print("\n¿Quieres que guarde esta información? (Responde: sí/no/editar)")
        print("=" * 70 + "\n")

    return {
        "answer": final_state["answer"],
        "question": final_state["question"],
        "metadata": final_state.get("metadata", {}),
        "error": final_state.get("error"),
        "routing_decision": final_state.get("routing_decision"),
        "tool_used": final_state.get("tool_name"),
        "pending_proposal": final_state.get("pending_proposal"),
        "conversation_id": conversation_id
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    # Ejemplos de uso
    questions = [
        "¿En qué estado está el ticket 482?",  # Tool
        "¿Cuántos locales tiene Brasaland?",    # RAG
        "¿Cuál es la política de vacaciones en USA y cuántos incidentes técnicos están abiertos?"  # Both
    ]

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        query_with_agent(question)
    else:
        for idx, q in enumerate(questions, 1):
            print(f"\n{'='*70}")
            print(f"Pregunta {idx}/{len(questions)}")
            print(f"{'='*70}")

            query_with_agent(q)

            if idx < len(questions):
                input("\nPresiona Enter para continuar...")
