"""
RFP Generation Graph - Multi-Agent Generator-Evaluator Loop

Pipeline multi-agente para generación y evaluación de propuestas RFP:
1. Coordinator: Lee handoff de Parte 1 (key_aspects + workstreams)
2. Parallel Generators: 8 departamentos generan secciones en paralelo
3. Parallel Evaluators: 3 dimensiones (readability, relevance, compliance) por sección
4. Feedback Loop: Re-generación con feedback si falla (max 3 iteraciones)
5. Human Review Handoff: Si se agotan iteraciones → needs_human_review

CRÍTICO:
- Consume handoff de Parte 1 (NO re-parsea PDF)
- Evaluadores en paralelo (NO secuencial)
- Límite de iteraciones: 3 (configurable)
- NUNCA descarta ticket: siempre conserva último borrador
- Estados: generando_borrador, en_evaluación, needs_human_review
"""

import os
import sys
from pathlib import Path
from typing import TypedDict, Dict, Any, List, Optional, Literal
from datetime import datetime
import json

# Agregar raíz al path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

from services.models.rfp import (
    RFPTicket,
    RFPSynthesis,
    DepartmentSection,
    DepartmentType,
    RFPTicketStatus
)
from services.models.rfp_eval import (
    DraftSection,
    EvaluationRecord,
    GenerationFeedback,
    EvaluationResult
)
from data.pipelines.rfp_generation.generator import generate_section_for_department
from data.pipelines.rfp_generation.evaluators import (
    evaluate_readability,
    evaluate_relevance,
    evaluate_compliance,
    aggregate_evaluation
)

load_dotenv()


# ============================================================
# STATE SCHEMA
# ============================================================

class GenerationState(TypedDict):
    """Estado compartido del grafo de generación de RFP"""

    # Input
    ticket_id: int

    # Handoff de Parte 1 (cargado desde BD)
    synthesis_data: Optional[Dict[str, Any]]  # RFPSynthesis
    department_sections: Dict[str, Dict[str, Any]]  # key_aspects por dept

    # Generación por departamento
    draft_sections: Dict[str, Dict[str, Any]]  # {dept: {technical, economic}}
    draft_section_ids: Dict[str, int]  # {dept: draft_section_id en BD}

    # Evaluación
    evaluation_results: Dict[str, EvaluationResult]  # {dept: EvaluationResult}

    # Control de iteraciones
    current_iteration: int
    max_iterations: int
    departments_to_regenerate: List[str]  # Departamentos que fallaron evaluación

    # Estado final
    all_sections_approved: bool
    needs_human_review: bool

    # Error handling
    error: Optional[str]


# ============================================================
# NODO 1: COORDINATOR (Carga Handoff de Parte 1)
# ============================================================

def coordinator_node(state: GenerationState) -> GenerationState:
    """
    Nodo 1: Coordinator

    Carga handoff de Parte 1 desde la base de datos:
    - RFPSynthesis (recommended_workstreams)
    - DepartmentSection[] (key_aspects por departamento)

    CRÍTICO: NO vuelve a parsear PDF original.
    """
    print(f"\n🎯 [Coordinator] Cargando handoff de Parte 1 para ticket {state['ticket_id']}")

    ticket_id = state["ticket_id"]

    # TODO: Implementar con db_session real
    # Por ahora, simulación

    # Mock de handoff (reemplazar con query real)
    synthesis_data = {
        "executive_summary": "Sistema digital para Brasaland...",
        "involved_departments": ["operaciones", "tecnologia", "marketing"],
        "recommended_workstreams": {
            "operaciones": {
                "lead": "Felipe Guerrero",
                "tasks": ["Dashboard ventas real-time", "Sistema alertas"],
                "deadline": "2024-12-01"
            },
            "tecnologia": {
                "lead": "Nicolás Park",
                "tasks": ["API central", "Telemetría"],
                "deadline": "2024-12-15"
            },
            "marketing": {
                "lead": "Camila Ospina",
                "tasks": ["App fidelización", "CRM"],
                "deadline": "2024-12-10"
            }
        }
    }

    department_sections = {
        "operaciones": {
            "requirements": ["Dashboard ventas", "Sistema alertas"],
            "constraints": ["Debe funcionar en 14 locales"],
            "missing_data": [],
            "estimated_effort": "alto"
        },
        "tecnologia": {
            "requirements": ["API REST", "Real-time telemetry"],
            "constraints": ["Stack actual: Next.js + FastAPI"],
            "missing_data": ["Presupuesto específico"],
            "estimated_effort": "medio"
        },
        "marketing": {
            "requirements": ["App móvil", "CRM"],
            "constraints": ["2 idiomas: ES/EN"],
            "missing_data": [],
            "estimated_effort": "alto"
        }
    }

    print(f"✅ [Coordinator] Handoff cargado: {len(department_sections)} departamentos")

    return {
        **state,
        "synthesis_data": synthesis_data,
        "department_sections": department_sections,
        "current_iteration": 1,
        "max_iterations": state.get("max_iterations", 3),
        "draft_sections": {},
        "evaluation_results": {},
        "departments_to_regenerate": [],
        "all_sections_approved": False,
        "needs_human_review": False
    }


# ============================================================
# NODO 2: PARALLEL GENERATORS
# ============================================================

def generator_node(state: GenerationState, department: str) -> GenerationState:
    """
    Nodo 2: Generator (por departamento)

    Genera borrador de sección técnica + económica.

    Si iteration > 1: Usa feedback de evaluadores previos.
    """
    iteration = state["current_iteration"]
    dept_key = department

    print(f"\n📝 [Generator-{dept_key}] Iteración {iteration}")

    # Obtener input de Parte 1
    key_aspects = state["department_sections"].get(dept_key, {})
    workstream = state["synthesis_data"]["recommended_workstreams"].get(dept_key, {})

    # Feedback de iteración anterior (si aplica)
    feedback = None
    if iteration > 1 and dept_key in state["evaluation_results"]:
        prev_eval = state["evaluation_results"][dept_key]
        feedback = prev_eval.feedback_for_generator

    # Generar sección
    try:
        result = generate_section_for_department(
            department=DepartmentType(dept_key),
            key_aspects=key_aspects,
            workstream=workstream,
            iteration=iteration,
            feedback=feedback
        )

        # Persistir en BD (mock - reemplazar con db_session real)
        draft_section_id = iteration * 100 + hash(dept_key) % 100  # Mock ID

        # Actualizar estado
        draft_sections = state.get("draft_sections", {})
        draft_sections[dept_key] = result

        draft_section_ids = state.get("draft_section_ids", {})
        draft_section_ids[dept_key] = draft_section_id

        print(f"✅ [Generator-{dept_key}] Borrador generado: {len(result['technical_content'])} chars técnico, {len(result['economic_content'])} chars económico")

        return {
            **state,
            "draft_sections": draft_sections,
            "draft_section_ids": draft_section_ids
        }

    except Exception as e:
        print(f"❌ [Generator-{dept_key}] Error: {e}")
        return {
            **state,
            "error": f"Error generando {dept_key}: {str(e)}"
        }


# ============================================================
# NODO 3: PARALLEL EVALUATORS (Batch)
# ============================================================

def evaluator_batch_node(state: GenerationState) -> GenerationState:
    """
    Nodo 3: Evaluator Batch

    Evalúa TODAS las secciones generadas en paralelo.

    Para cada sección:
    1. Evalúa legibilidad (py-readability-metrics)
    2. Evalúa pertinencia (vs. key_aspects)
    3. Evalúa compliance (políticas corporativas)
    4. Agrega resultados
    """
    print(f"\n🔍 [Evaluators] Evaluando {len(state['draft_sections'])} secciones...")

    evaluation_results = {}

    for dept_key, draft in state["draft_sections"].items():
        print(f"\n  ├─ Evaluando {dept_key}...")

        technical_content = draft.get("technical_content", "")
        economic_content = draft.get("economic_content", "")
        key_aspects = state["department_sections"].get(dept_key, {})

        # EVALUADOR 1: Readability
        readability_score = evaluate_readability(
            technical_content=technical_content,
            economic_content=economic_content,
            target_flesch=60.0
        )
        print(f"     📖 Legibilidad: {'✅' if readability_score.pass_ else '❌'} (Flesch: {readability_score.flesch_reading_ease:.1f})")

        # EVALUADOR 2: Relevance
        relevance_score = evaluate_relevance(
            technical_content=technical_content,
            economic_content=economic_content,
            key_aspects=key_aspects
        )
        print(f"     🎯 Pertinencia: {'✅' if relevance_score.pass_ else '❌'} (Cobertura: {relevance_score.coverage_percentage:.0%})")

        # EVALUADOR 3: Compliance
        compliance_score = evaluate_compliance(
            technical_content=technical_content,
            economic_content=economic_content
        )
        print(f"     ⚖️  Compliance: {'✅' if compliance_score.pass_ else '❌'} ({len(compliance_score.violations)} violaciones)")

        # AGREGADOR
        section_id = f"draft_{state['draft_section_ids'].get(dept_key, 0)}"
        evaluation_result = aggregate_evaluation(
            section_id=section_id,
            department=dept_key,
            iteration=state["current_iteration"],
            readability=readability_score,
            relevance=relevance_score,
            compliance=compliance_score
        )

        evaluation_results[dept_key] = evaluation_result

        # Persistir en BD (mock)
        print(f"     {'✅ APROBADO' if evaluation_result.overall_pass else '❌ REQUIERE MEJORAS'}")

    return {
        **state,
        "evaluation_results": evaluation_results
    }


# ============================================================
# NODO 4: DECISION (¿Iterar o Finalizar?)
# ============================================================

def decision_node(state: GenerationState) -> GenerationState:
    """
    Nodo 4: Decision

    Analiza resultados de evaluación y decide:
    1. Si TODAS las secciones pasan → all_sections_approved = True
    2. Si alguna falla Y iterations < max → Identificar departamentos para regenerar
    3. Si iterations >= max → needs_human_review = True (conservar último borrador)
    """
    print(f"\n⚖️  [Decision] Analizando resultados...")

    evaluation_results = state["evaluation_results"]
    current_iteration = state["current_iteration"]
    max_iterations = state["max_iterations"]

    # Identificar secciones que fallaron
    failed_departments = [
        dept for dept, eval_result in evaluation_results.items()
        if not eval_result.overall_pass
    ]

    print(f"   Iteración: {current_iteration}/{max_iterations}")
    print(f"   Secciones aprobadas: {len(evaluation_results) - len(failed_departments)}/{len(evaluation_results)}")

    if not failed_departments:
        # ✅ Todas las secciones pasaron
        print(f"   ✅ TODAS LAS SECCIONES APROBADAS")
        return {
            **state,
            "all_sections_approved": True,
            "needs_human_review": False
        }

    elif current_iteration < max_iterations:
        # 🔄 Hay fallos pero quedan iteraciones
        print(f"   🔄 Regenerando {len(failed_departments)} departamentos: {', '.join(failed_departments)}")
        return {
            **state,
            "departments_to_regenerate": failed_departments,
            "current_iteration": current_iteration + 1,
            "all_sections_approved": False,
            "needs_human_review": False
        }

    else:
        # ⚠️ Se agotaron iteraciones → Human review
        print(f"   ⚠️  LÍMITE DE ITERACIONES ALCANZADO ({max_iterations})")
        print(f"   → Conservando últimos borradores para revisión humana")
        return {
            **state,
            "all_sections_approved": False,
            "needs_human_review": True
        }


# ============================================================
# NODO 5: REGENERATOR (Solo departamentos que fallaron)
# ============================================================

def regenerator_node(state: GenerationState) -> GenerationState:
    """
    Nodo 5: Regenerator

    Re-genera SOLO las secciones que fallaron evaluación.
    Usa feedback_for_generator de los evaluadores.
    """
    print(f"\n🔁 [Regenerator] Re-generando secciones fallidas...")

    departments_to_regenerate = state["departments_to_regenerate"]

    for dept_key in departments_to_regenerate:
        # Llamar al generador con feedback
        state = generator_node(state, dept_key)

    # Limpiar lista de regeneración
    return {
        **state,
        "departments_to_regenerate": []
    }


# ============================================================
# NODO 6: FINALIZER (Persistir resultados finales)
# ============================================================

def finalizer_node(state: GenerationState) -> GenerationState:
    """
    Nodo 6: Finalizer

    Persiste resultados finales en BD:
    - Marca DraftSection como is_final=True
    - Actualiza RFPTicket status según resultado
    - Genera handoff para Parte 3 (si all_sections_approved)
    """
    print(f"\n💾 [Finalizer] Persistiendo resultados finales...")

    ticket_id = state["ticket_id"]

    if state["all_sections_approved"]:
        # ✅ Todo aprobado → Listo para Parte 3
        print(f"   ✅ Todas las secciones aprobadas")
        print(f"   → Estado del ticket: listo_para_consolidacion (Parte 3)")

        # TODO: Actualizar BD
        # ticket.status = "listo_para_consolidacion"
        # for draft in draft_sections:
        #     draft.is_final = True
        #     draft.passed_evaluation = True

    else:
        # ⚠️ Necesita revisión humana
        print(f"   ⚠️  Requiere revisión humana")
        print(f"   → Estado del ticket: needs_human_review")

        # TODO: Actualizar BD
        # ticket.status = RFPTicketStatus.NEEDS_HUMAN_REVIEW
        # for draft in draft_sections:
        #     draft.is_final = True
        #     draft.passed_evaluation = False

    return {
        **state
    }


# ============================================================
# EDGES CONDICIONALES
# ============================================================

def should_regenerate(state: GenerationState) -> Literal["regenerate", "finalize"]:
    """
    Edge condicional: ¿Regenerar o finalizar?

    Regenerate: Si hay departamentos para regenerar
    Finalize: Si todo aprobado O needs_human_review
    """
    if state.get("departments_to_regenerate"):
        return "regenerate"
    else:
        return "finalize"


# ============================================================
# BUILD GRAPH
# ============================================================

def build_rfp_generation_graph() -> StateGraph:
    """
    Construye grafo LangGraph para generación y evaluación de RFP.

    Topología:

    START → Coordinator → Parallel Generators → Evaluators → Decision
                                                                │
                                    ┌───────────────────────────┘
                                    │
                              ┌─────┴─────┐
                              │           │
                         [regenerate]  [finalize]
                              │           │
                              ↓           ↓
                        Regenerator → Evaluators (loop)
                                          │
                                          └→ Finalizer → END
    """
    workflow = StateGraph(GenerationState)

    # NODO 1: Coordinator
    workflow.add_node("coordinator", coordinator_node)

    # NODO 2: Generators (por departamento)
    # Nota: En producción, usar paralelización real (Celery, Ray)
    # Por ahora, simulamos con nodos secuenciales
    for dept in ["operaciones", "tecnologia", "marketing"]:  # Subset para demo
        workflow.add_node(
            f"generator_{dept}",
            lambda s, d=dept: generator_node(s, d)
        )

    # NODO 3: Evaluators (batch)
    workflow.add_node("evaluators", evaluator_batch_node)

    # NODO 4: Decision
    workflow.add_node("decision", decision_node)

    # NODO 5: Regenerator
    workflow.add_node("regenerator", regenerator_node)

    # NODO 6: Finalizer
    workflow.add_node("finalizer", finalizer_node)

    # EDGES
    workflow.set_entry_point("coordinator")

    # Coordinator → Generators
    for dept in ["operaciones", "tecnologia", "marketing"]:
        workflow.add_edge("coordinator", f"generator_{dept}")

    # Generators → Evaluators
    for dept in ["operaciones", "tecnologia", "marketing"]:
        workflow.add_edge(f"generator_{dept}", "evaluators")

    # Evaluators → Decision
    workflow.add_edge("evaluators", "decision")

    # Decision → Regenerate OR Finalize
    workflow.add_conditional_edges(
        "decision",
        should_regenerate,
        {
            "regenerate": "regenerator",
            "finalize": "finalizer"
        }
    )

    # Regenerator → Evaluators (loop)
    workflow.add_edge("regenerator", "evaluators")

    # Finalizer → END
    workflow.add_edge("finalizer", END)

    return workflow.compile()


# ============================================================
# EXECUTE PIPELINE
# ============================================================

def execute_rfp_generation_pipeline(
    ticket_id: int,
    max_iterations: int = 3,
    db_session = None
) -> Dict[str, Any]:
    """
    Ejecuta pipeline completo de generación y evaluación.

    Args:
        ticket_id: ID del ticket con status=analisis_completo
        max_iterations: Límite de iteraciones (default: 3)
        db_session: Sesión de BD para persistencia

    Returns:
        {
            "status": "approved" | "needs_human_review",
            "sections_approved": 3,
            "total_sections": 3,
            "iterations_used": 2,
            "evaluation_summary": {...}
        }
    """
    print(f"\n{'='*60}")
    print(f"🚀 Iniciando Pipeline de Generación RFP - Ticket #{ticket_id}")
    print(f"{'='*60}")

    # Construir grafo
    graph = build_rfp_generation_graph()

    # Estado inicial
    initial_state: GenerationState = {
        "ticket_id": ticket_id,
        "synthesis_data": None,
        "department_sections": {},
        "draft_sections": {},
        "draft_section_ids": {},
        "evaluation_results": {},
        "current_iteration": 1,
        "max_iterations": max_iterations,
        "departments_to_regenerate": [],
        "all_sections_approved": False,
        "needs_human_review": False,
        "error": None
    }

    # Ejecutar grafo
    final_state = graph.invoke(initial_state)

    # Construir resumen
    evaluation_results = final_state.get("evaluation_results", {})
    sections_approved = sum(1 for e in evaluation_results.values() if e.overall_pass)
    total_sections = len(evaluation_results)

    result = {
        "status": "approved" if final_state["all_sections_approved"] else "needs_human_review",
        "sections_approved": sections_approved,
        "total_sections": total_sections,
        "iterations_used": final_state["current_iteration"],
        "all_sections_approved": final_state["all_sections_approved"],
        "needs_human_review": final_state["needs_human_review"],
        "evaluation_summary": {
            dept: {
                "overall_pass": eval_result.overall_pass,
                "readability_pass": eval_result.readability.pass_,
                "relevance_pass": eval_result.relevance.pass_,
                "compliance_pass": eval_result.compliance.pass_,
                "feedback": eval_result.feedback_for_generator
            }
            for dept, eval_result in evaluation_results.items()
        }
    }

    print(f"\n{'='*60}")
    print(f"✅ Pipeline Completado")
    print(f"   Estado: {result['status']}")
    print(f"   Secciones aprobadas: {sections_approved}/{total_sections}")
    print(f"   Iteraciones usadas: {final_state['current_iteration']}/{max_iterations}")
    print(f"{'='*60}\n")

    return result


# ============================================================
# MAIN (Testing)
# ============================================================

if __name__ == "__main__":
    # Test del pipeline
    result = execute_rfp_generation_pipeline(
        ticket_id=123,
        max_iterations=3
    )

    print("\n📊 Resultado Final:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
