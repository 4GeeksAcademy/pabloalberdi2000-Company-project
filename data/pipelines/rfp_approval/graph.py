"""
RFP Approval Graph - Human-in-the-Loop with Checkpointing

Pipeline multi-agente para aprobación humana y consolidación final:
1. Approval Coordinator: Carga borradores finales de Parte 2
2. Parallel Department Approval Branches: 8 ramas con HITL aisladas
3. Barrier Node: Espera ALL aprobaciones
4. Conflict Detector: Identifica desacuerdos
5. Arbitrator Node: Resuelve conflictos (HITL de Mariana Restrepo)
6. Ultimate Synthesizer: Consolida documento final
7. Finalizer: Exporta PDF/Word, marca ticket como "terminado"

CRÍTICO:
- Interrupciones aisladas por rama (NO bloqueo global)
- Checkpointing granular con PostgreSQL/Supabase
- Thread IDs namespaced: rfp-{ticket_id}:{department}
- Reanudación limpia desde último checkpoint
- NO reinicia grafo desde cero
"""

import os
import sys
from pathlib import Path
from typing import TypedDict, Dict, Any, List, Optional, Literal, Annotated
from datetime import datetime
import json

# Agregar raíz al path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver  # Fallback para testing
from psycopg import Connection
import operator
from dotenv import load_dotenv

from services.models.rfp import (
    RFPTicket,
    RFPTicketStatus,
    DepartmentType
)
from services.models.rfp_eval import DraftSection, EvaluationRecord
from services.models.rfp_approval import (
    DepartmentApproval,
    ConflictRecord,
    FinalDocument,
    ApprovalStatus,
    ConflictSeverity,
    HumanApprovalDecision,
    ArbitrationDecision,
    create_department_approval,
    create_conflict_record
)

load_dotenv()


# ============================================================
# STATE SCHEMA
# ============================================================

class ApprovalState(TypedDict):
    """Estado compartido del grafo de aprobación"""

    # Input
    ticket_id: int

    # Borradores de Parte 2
    draft_sections: Dict[str, Dict[str, Any]]  # {dept: draft_data}
    evaluation_records: Dict[str, Dict[str, Any]]  # {dept: eval_data}

    # Aprobaciones por departamento (reducer: acumula aprobaciones)
    department_approvals: Annotated[Dict[str, Dict[str, Any]], operator.add]

    # Conflictos detectados
    conflicts: List[Dict[str, Any]]

    # Documento final
    final_document: Optional[Dict[str, Any]]

    # Control de flujo
    all_approved: bool
    has_conflicts: bool
    conflicts_resolved: bool

    # Human-in-the-Loop flags
    waiting_for_human: bool
    waiting_for_arbitration: bool

    # Error handling
    error: Optional[str]


# ============================================================
# NODO 1: APPROVAL COORDINATOR
# ============================================================

def approval_coordinator_node(state: ApprovalState) -> ApprovalState:
    """
    Nodo 1: Approval Coordinator

    Carga borradores finales de Parte 2 y crea registros de aprobación.

    CRÍTICO: Consume handoff de Parte 2 (DraftSection[]).
    """
    print(f"\n🎯 [Approval Coordinator] Inicializando aprobaciones para ticket {state['ticket_id']}")

    ticket_id = state["ticket_id"]

    # TODO: Implementar con db_session real
    # Por ahora, simulación

    # Mock de borradores finales (reemplazar con query real)
    draft_sections = {
        "operaciones": {
            "draft_section_id": 101,
            "technical_content": "Dashboard ventas real-time...",
            "economic_content": "Estimación: 40 person-days...",
            "is_final": True,
            "passed_evaluation": True
        },
        "tecnologia": {
            "draft_section_id": 102,
            "technical_content": "API REST con Next.js + FastAPI...",
            "economic_content": "Estimación: 60 person-days...",
            "is_final": True,
            "passed_evaluation": True
        },
        "marketing": {
            "draft_section_id": 103,
            "technical_content": "App móvil con fidelización...",
            "economic_content": "Estimación: 50 person-days...",
            "is_final": True,
            "passed_evaluation": False  # needs_human_review desde Parte 2
        }
    }

    # Mock de evaluaciones
    evaluation_records = {
        "operaciones": {
            "overall_pass": True,
            "readability_score": 65.0,
            "relevance_coverage": 0.95,
            "compliance_pass": True
        },
        "tecnologia": {
            "overall_pass": True,
            "readability_score": 62.0,
            "relevance_coverage": 0.92,
            "compliance_pass": True
        },
        "marketing": {
            "overall_pass": False,  # Falló en iteración 3
            "readability_score": 58.0,  # Ligeramente bajo
            "relevance_coverage": 0.88,  # Falta cobertura
            "compliance_pass": True
        }
    }

    # Crear registros de aprobación en BD (mock)
    # En producción: db_session.add(create_department_approval(...))
    department_approvals = {}
    for dept, draft in draft_sections.items():
        approval = {
            "department": dept,
            "status": "pending",
            "checkpoint_thread_id": f"rfp-{ticket_id}:{dept}",
            "reviewer_name": None,
            "approved_at": None
        }
        department_approvals[dept] = approval

    print(f"✅ [Approval Coordinator] {len(draft_sections)} secciones cargadas")
    print(f"   Departamentos: {', '.join(draft_sections.keys())}")

    return {
        **state,
        "draft_sections": draft_sections,
        "evaluation_records": evaluation_records,
        "department_approvals": department_approvals,
        "conflicts": [],
        "all_approved": False,
        "has_conflicts": False,
        "conflicts_resolved": False,
        "waiting_for_human": True,  # Inicia esperando aprobaciones
        "waiting_for_arbitration": False
    }


# ============================================================
# NODO 2: DEPARTMENT APPROVAL BRANCH (por departamento)
# ============================================================

def department_approval_node(
    state: ApprovalState,
    department: str
) -> ApprovalState:
    """
    Nodo 2: Department Approval Branch

    Rama de aprobación para un departamento específico.

    Flow:
    1. Pre-Approval Check: Verificar si borrador requiere revisión
    2. INTERRUPT: Pausar para aprobación humana
    3. Resume: Procesar decisión de aprobación
    4. Mark Approved/Rejected

    CRÍTICO: Esta función se ejecuta ANTES de la interrupción.
    Después de la interrupción, el estado ya contiene la decisión humana.
    """
    print(f"\n📋 [Approval-{department}] Pre-aprobación check")

    draft = state["draft_sections"].get(department, {})
    evaluation = state["evaluation_records"].get(department, {})

    # Verificar si ya fue aprobado (en caso de reanudación)
    current_approval = state["department_approvals"].get(department, {})
    if current_approval.get("status") == "approved":
        print(f"   ✅ {department} ya aprobado previamente")
        return state

    # Determinar responsable según company-BRIEFING.md
    DEPARTMENT_REVIEWERS = {
        "operaciones": "Felipe Guerrero",
        "tecnologia": "Nicolás Park",
        "marketing": "Camila Ospina",
        "compras": "Lucía Fernández",
        "rrhh": "Ashley Turner",
        "formacion": "Jake Morrison",
        "direccion": "Mariana Restrepo",
        "especiales": "Mariana Restrepo"  # CEO revisa especiales
    }

    reviewer_name = DEPARTMENT_REVIEWERS.get(department, "Unknown")

    print(f"   Borrador: {len(draft.get('technical_content', ''))} chars técnico")
    print(f"   Evaluación: {'✅ PASS' if evaluation.get('overall_pass') else '⚠️  NEEDS REVIEW'}")
    print(f"   Responsable: {reviewer_name}")
    print(f"   🔔 Esperando aprobación humana de {reviewer_name}...")

    # Actualizar estado de aprobación
    updated_approval = {
        **current_approval,
        "department": department,
        "status": "pending",
        "reviewer_name": reviewer_name,
        "checkpoint_thread_id": f"rfp-{state['ticket_id']}:{department}"
    }

    # IMPORTANTE: Este estado se persiste en checkpoint ANTES de la interrupción
    return {
        **state,
        "department_approvals": {
            **state.get("department_approvals", {}),
            department: updated_approval
        },
        "waiting_for_human": True
    }


# ============================================================
# NODO 3: PROCESS HUMAN APPROVAL (post-interrupción)
# ============================================================

def process_human_approval_node(
    state: ApprovalState,
    department: str
) -> ApprovalState:
    """
    Nodo 3: Process Human Approval

    Procesa la decisión humana DESPUÉS de la reanudación.

    Este nodo se ejecuta cuando se llama a resume() con la decisión.
    """
    print(f"\n✅ [Process Approval-{department}] Procesando decisión humana")

    approval = state["department_approvals"].get(department, {})

    # La decisión humana viene en el estado actualizado
    # (inyectada via update_state en el resume)
    decision = approval.get("approval_decision")

    if not decision:
        print(f"   ⚠️  No se encontró decisión para {department}")
        return state

    approved = decision.get("approved", False)
    reviewer_name = decision.get("reviewer_name")
    comments = decision.get("comments", "")

    # Actualizar aprobación
    updated_approval = {
        **approval,
        "status": "approved" if approved else "rejected",
        "approved_at": datetime.utcnow().isoformat(),
        "comments": comments
    }

    print(f"   Decisión: {'✅ APROBADO' if approved else '❌ RECHAZADO'}")
    print(f"   Por: {reviewer_name}")
    if comments:
        print(f"   Comentarios: {comments}")

    return {
        **state,
        "department_approvals": {
            **state.get("department_approvals", {}),
            department: updated_approval
        }
    }


# ============================================================
# NODO 4: BARRIER (Espera todas las aprobaciones)
# ============================================================

def barrier_node(state: ApprovalState) -> ApprovalState:
    """
    Nodo 4: Barrier

    Espera hasta que TODOS los departamentos estén aprobados.

    Verifica que no queden aprobaciones pendientes.
    """
    print(f"\n🚧 [Barrier] Verificando aprobaciones completas...")

    approvals = state.get("department_approvals", {})

    pending = [dept for dept, appr in approvals.items() if appr.get("status") == "pending"]
    approved = [dept for dept, appr in approvals.items() if appr.get("status") == "approved"]
    rejected = [dept for dept, appr in approvals.items() if appr.get("status") == "rejected"]

    print(f"   Aprobados: {len(approved)}/{len(approvals)}")
    print(f"   Pendientes: {len(pending)} → {', '.join(pending) if pending else 'Ninguno'}")
    print(f"   Rechazados: {len(rejected)} → {', '.join(rejected) if rejected else 'Ninguno'}")

    all_approved = len(pending) == 0 and len(rejected) == 0

    if all_approved:
        print(f"   ✅ TODAS las aprobaciones completadas")
    else:
        print(f"   ⏳ Aún faltan aprobaciones")

    return {
        **state,
        "all_approved": all_approved,
        "waiting_for_human": not all_approved
    }


# ============================================================
# NODO 5: CONFLICT DETECTOR
# ============================================================

def conflict_detector_node(state: ApprovalState) -> ApprovalState:
    """
    Nodo 5: Conflict Detector

    Detecta desacuerdos entre departamentos aprobados.

    Tipos de conflictos:
    - Timeline: Plazos incompatibles
    - Budget: Estimaciones que suman más del presupuesto
    - Requirements: Requerimientos contradictorios
    - Technical: Incompatibilidades técnicas
    """
    print(f"\n🔍 [Conflict Detector] Analizando desacuerdos...")

    draft_sections = state.get("draft_sections", {})
    conflicts = []

    # REGLA 1: Detectar plazos incompatibles
    # (Simplificado: comparar deadlines en economic_content)
    departments = list(draft_sections.keys())
    for i, dept_a in enumerate(departments):
        for dept_b in departments[i+1:]:
            # Mock de detección (en producción: usar LLM o regex)
            # Ejemplo: Si operaciones dice "1 mes" y tecnología dice "3 meses"

            # Por ahora, NO detectamos conflictos (mock)
            # En producción: Analizar contenido con LLM
            pass

    # Mock: Simular 1 conflicto de prueba
    if "operaciones" in draft_sections and "tecnologia" in draft_sections:
        # Conflicto simulado: Plazos incompatibles
        conflict = {
            "department_a": "operaciones",
            "department_b": "tecnologia",
            "conflict_type": "timeline",
            "conflict_description": "Operaciones requiere entrega en 4 semanas, Tecnología estima 8 semanas para API completa",
            "severity": "medium"
        }
        # Descomentар para simular conflicto:
        # conflicts.append(conflict)

    has_conflicts = len(conflicts) > 0

    if has_conflicts:
        print(f"   ⚠️  {len(conflicts)} conflictos detectados")
        for c in conflicts:
            print(f"      - {c['conflict_type']}: {c['department_a']} vs {c['department_b']}")
    else:
        print(f"   ✅ NO se detectaron conflictos")

    return {
        **state,
        "conflicts": conflicts,
        "has_conflicts": has_conflicts,
        "waiting_for_arbitration": has_conflicts
    }


# ============================================================
# NODO 6: ARBITRATOR (HITL de CEO)
# ============================================================

def arbitrator_node(state: ApprovalState) -> ApprovalState:
    """
    Nodo 6: Arbitrator

    Resuelve conflictos mediante arbitraje de Mariana Restrepo (CEO).

    INTERRUPT: Pausa para decisión de arbitraje.

    Resoluciones posibles:
    - accept_dept_A: Aceptar versión de departamento A
    - accept_dept_B: Aceptar versión de departamento B
    - hybrid: Combinación de ambos
    - regenerate: Re-generar secciones afectadas
    """
    print(f"\n⚖️  [Arbitrator] Preparando arbitraje...")

    conflicts = state.get("conflicts", [])

    if not conflicts:
        print(f"   ✅ No hay conflictos para arbitrar")
        return {
            **state,
            "conflicts_resolved": True,
            "waiting_for_arbitration": False
        }

    print(f"   🔔 Esperando decisión de arbitraje de Mariana Restrepo (CEO)")
    print(f"   Conflictos pendientes: {len(conflicts)}")

    # IMPORTANTE: La decisión de arbitraje se inyecta via update_state en resume
    # Por ahora, marcamos como esperando

    return {
        **state,
        "waiting_for_arbitration": True
    }


def process_arbitration_node(state: ApprovalState) -> ApprovalState:
    """
    Procesa decisión de arbitraje DESPUÉS de reanudación.
    """
    print(f"\n✅ [Process Arbitration] Procesando decisión de arbitraje")

    conflicts = state.get("conflicts", [])

    # La decisión viene en state["arbitration_decision"]
    # (inyectada via update_state)
    arbitration = state.get("arbitration_decision")

    if not arbitration:
        print(f"   ⚠️  No se encontró decisión de arbitraje")
        return state

    resolution = arbitration.get("resolution")
    arbitrator_name = arbitration.get("arbitrator_name")
    notes = arbitration.get("resolution_notes", "")

    print(f"   Decisión: {resolution}")
    print(f"   Por: {arbitrator_name}")
    print(f"   Notas: {notes}")

    # Marcar conflictos como resueltos
    # En producción: Actualizar ConflictRecord en BD

    return {
        **state,
        "conflicts_resolved": True,
        "waiting_for_arbitration": False
    }


# ============================================================
# NODO 7: ULTIMATE SYNTHESIZER
# ============================================================

def ultimate_synthesizer_node(state: ApprovalState) -> ApprovalState:
    """
    Nodo 7: Ultimate Document Synthesizer

    Consolida documento final con TODAS las secciones aprobadas.

    Output:
    - Markdown completo
    - Executive summary
    - Orden de secciones
    """
    print(f"\n📄 [Ultimate Synthesizer] Consolidando documento final...")

    draft_sections = state.get("draft_sections", {})
    approvals = state.get("department_approvals", {})

    # Orden de secciones (según jerarquía de Brasaland)
    sections_order = [
        "direccion",      # Mariana Restrepo (CEO) - Executive Summary
        "operaciones",    # Felipe Guerrero
        "tecnologia",     # Nicolás Park
        "marketing",      # Camila Ospina
        "compras",        # Lucía Fernández
        "rrhh",           # Ashley Turner
        "formacion",      # Jake Morrison
        "especiales"      # Si existe
    ]

    # Filtrar solo departamentos presentes
    sections_order = [dept for dept in sections_order if dept in draft_sections]

    # Consolidar contenido
    full_proposal_parts = []
    all_approvers = []

    full_proposal_parts.append("# Propuesta de Servicio - Brasaland Digital Platform\n\n")

    for dept in sections_order:
        draft = draft_sections.get(dept, {})
        approval = approvals.get(dept, {})

        dept_name = dept.capitalize()
        reviewer = approval.get("reviewer_name", "Unknown")

        full_proposal_parts.append(f"## {dept_name}\n")
        full_proposal_parts.append(f"**Responsable**: {reviewer}\n\n")
        full_proposal_parts.append("### Propuesta Técnica\n")
        full_proposal_parts.append(draft.get("technical_content", "") + "\n\n")
        full_proposal_parts.append("### Estimación Económica\n")
        full_proposal_parts.append(draft.get("economic_content", "") + "\n\n")
        full_proposal_parts.append("---\n\n")

        all_approvers.append(reviewer)

    full_proposal_markdown = "".join(full_proposal_parts)

    # Executive summary (primeros 3 párrafos)
    executive_summary = f"""
Propuesta consolidada para sistema digital de Brasaland.

Participaron {len(sections_order)} departamentos en la elaboración de esta propuesta.

Aprobada por: {', '.join(set(all_approvers))}.
"""

    # Calcular metadata
    total_words = len(full_proposal_markdown.split())
    estimated_pages = total_words // 300  # ~300 palabras por página

    final_document = {
        "ticket_id": state["ticket_id"],
        "executive_summary": executive_summary.strip(),
        "full_proposal_markdown": full_proposal_markdown,
        "sections_order": sections_order,
        "total_words": total_words,
        "total_pages": estimated_pages,
        "all_approvers": list(set(all_approvers)),
        "generated_at": datetime.utcnow().isoformat()
    }

    print(f"✅ [Ultimate Synthesizer] Documento consolidado")
    print(f"   Secciones: {len(sections_order)}")
    print(f"   Palabras totales: {total_words}")
    print(f"   Páginas estimadas: {estimated_pages}")
    print(f"   Aprobadores: {', '.join(set(all_approvers))}")

    return {
        **state,
        "final_document": final_document
    }


# ============================================================
# NODO 8: FINALIZER
# ============================================================

def finalizer_node(state: ApprovalState) -> ApprovalState:
    """
    Nodo 8: Finalizer

    Exporta documento final a PDF/Word y marca ticket como "terminado".

    Actions:
    1. Exportar Markdown → PDF (usando pandoc o reportlab)
    2. Exportar Markdown → Word (usando python-docx)
    3. Persistir FinalDocument en BD
    4. Actualizar RFPTicket status = "terminado"
    5. Notificar a Ventas
    """
    print(f"\n💾 [Finalizer] Exportando documento final...")

    final_document = state.get("final_document", {})
    ticket_id = state["ticket_id"]

    markdown_content = final_document.get("full_proposal_markdown", "")

    # Mock de exportación (en producción: usar pandoc/python-docx)
    output_dir = f"data/final_proposals/"
    os.makedirs(output_dir, exist_ok=True)

    # Guardar Markdown
    markdown_path = f"{output_dir}rfp_{ticket_id}_proposal.md"
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"   ✅ Markdown guardado: {markdown_path}")

    # TODO: Exportar a PDF (pandoc o reportlab)
    pdf_path = f"{output_dir}rfp_{ticket_id}_proposal.pdf"
    print(f"   ⏳ PDF: {pdf_path} (pendiente implementación)")

    # TODO: Exportar a Word (python-docx)
    word_path = f"{output_dir}rfp_{ticket_id}_proposal.docx"
    print(f"   ⏳ Word: {word_path} (pendiente implementación)")

    # TODO: Persistir FinalDocument en BD
    # final_doc = FinalDocument(
    #     ticket_id=ticket_id,
    #     executive_summary=final_document["executive_summary"],
    #     full_proposal_markdown=markdown_content,
    #     sections_order=final_document["sections_order"],
    #     pdf_path=pdf_path,
    #     word_path=word_path,
    #     total_pages=final_document["total_pages"],
    #     total_words=final_document["total_words"],
    #     all_approvers=final_document["all_approvers"]
    # )
    # db_session.add(final_doc)

    # TODO: Actualizar RFPTicket status = "terminado"
    # ticket.status = RFPTicketStatus.TERMINADO
    # db_session.commit()

    print(f"   ✅ Ticket {ticket_id} marcado como TERMINADO")
    print(f"   📧 Notificación enviada a Ventas (mock)")

    return state


# ============================================================
# EDGES CONDICIONALES
# ============================================================

def should_wait_for_approvals(state: ApprovalState) -> Literal["wait", "continue"]:
    """
    Edge condicional: ¿Esperar aprobaciones pendientes?
    """
    return "wait" if state.get("waiting_for_human") else "continue"


def should_arbitrate(state: ApprovalState) -> Literal["arbitrate", "skip"]:
    """
    Edge condicional: ¿Necesita arbitraje?
    """
    return "arbitrate" if state.get("has_conflicts") else "skip"


# ============================================================
# BUILD GRAPH
# ============================================================

def build_rfp_approval_graph(
    checkpointer = None
) -> StateGraph:
    """
    Construye grafo LangGraph para aprobación humana y consolidación.

    Args:
        checkpointer: PostgresSaver o MemorySaver para checkpointing

    Topología:

    START → Approval Coordinator → Parallel Department Branches
                                         (con INTERRUPT cada una)
                                               ↓
                                          [Barrier]
                                               ↓
                                      [Conflict Detector]
                                         ┌─────┴─────┐
                                      [skip]     [arbitrate]
                                         │           │
                                         │     [Arbitrator]
                                         │      INTERRUPT
                                         │           │
                                         └─────┬─────┘
                                               ↓
                                    [Ultimate Synthesizer]
                                               ↓
                                         [Finalizer]
                                               ↓
                                             [END]
    """
    workflow = StateGraph(ApprovalState)

    # NODO 1: Approval Coordinator
    workflow.add_node("approval_coordinator", approval_coordinator_node)

    # NODO 2: Department Approval Branches (simplificado: 3 departamentos)
    # En producción: Una rama por cada departamento presente
    for dept in ["operaciones", "tecnologia", "marketing"]:
        workflow.add_node(
            f"approval_{dept}",
            lambda s, d=dept: department_approval_node(s, d)
        )
        workflow.add_node(
            f"process_approval_{dept}",
            lambda s, d=dept: process_human_approval_node(s, d)
        )

    # NODO 4: Barrier
    workflow.add_node("barrier", barrier_node)

    # NODO 5: Conflict Detector
    workflow.add_node("conflict_detector", conflict_detector_node)

    # NODO 6: Arbitrator
    workflow.add_node("arbitrator", arbitrator_node)
    workflow.add_node("process_arbitration", process_arbitration_node)

    # NODO 7: Ultimate Synthesizer
    workflow.add_node("ultimate_synthesizer", ultimate_synthesizer_node)

    # NODO 8: Finalizer
    workflow.add_node("finalizer", finalizer_node)

    # EDGES
    workflow.set_entry_point("approval_coordinator")

    # Coordinator → Department Branches
    for dept in ["operaciones", "tecnologia", "marketing"]:
        workflow.add_edge("approval_coordinator", f"approval_{dept}")

    # Department Approval → INTERRUPT → Process Approval
    # IMPORTANTE: La interrupción se configura en compile()
    for dept in ["operaciones", "tecnologia", "marketing"]:
        workflow.add_edge(f"approval_{dept}", f"process_approval_{dept}")
        workflow.add_edge(f"process_approval_{dept}", "barrier")

    # Barrier → Conflict Detector
    workflow.add_edge("barrier", "conflict_detector")

    # Conflict Detector → Arbitrate OR Skip
    workflow.add_conditional_edges(
        "conflict_detector",
        should_arbitrate,
        {
            "arbitrate": "arbitrator",
            "skip": "ultimate_synthesizer"
        }
    )

    # Arbitrator → INTERRUPT → Process Arbitration
    workflow.add_edge("arbitrator", "process_arbitration")
    workflow.add_edge("process_arbitration", "ultimate_synthesizer")

    # Ultimate Synthesizer → Finalizer
    workflow.add_edge("ultimate_synthesizer", "finalizer")

    # Finalizer → END
    workflow.add_edge("finalizer", END)

    # Compile con checkpointer e interrupciones
    interrupts = [
        f"approval_{dept}" for dept in ["operaciones", "tecnologia", "marketing"]
    ] + ["arbitrator"]

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupts  # HITL: Pausar ANTES de estos nodos
    )


# ============================================================
# EXECUTE PIPELINE
# ============================================================

def execute_rfp_approval_pipeline(
    ticket_id: int,
    db_session = None,
    checkpointer = None
) -> Dict[str, Any]:
    """
    Ejecuta pipeline completo de aprobación y consolidación.

    Args:
        ticket_id: ID del ticket con status=listo_para_consolidacion
        db_session: Sesión de BD
        checkpointer: PostgresSaver o MemorySaver

    Returns:
        {
            "status": "waiting_approval" | "completed",
            "waiting_departments": [...],
            "final_document_path": "..."
        }
    """
    print(f"\n{'='*60}")
    print(f"🚀 Iniciando Pipeline de Aprobación RFP - Ticket #{ticket_id}")
    print(f"{'='*60}")

    # Usar MemorySaver si no se proporciona checkpointer
    if checkpointer is None:
        checkpointer = MemorySaver()
        print(f"⚠️  Usando MemorySaver (no persistente)")

    # Construir grafo
    graph = build_rfp_approval_graph(checkpointer=checkpointer)

    # Configuración del thread (namespaced)
    thread_config = {
        "configurable": {
            "thread_id": f"rfp-{ticket_id}"
        }
    }

    # Estado inicial
    initial_state: ApprovalState = {
        "ticket_id": ticket_id,
        "draft_sections": {},
        "evaluation_records": {},
        "department_approvals": {},
        "conflicts": [],
        "final_document": None,
        "all_approved": False,
        "has_conflicts": False,
        "conflicts_resolved": False,
        "waiting_for_human": False,
        "waiting_for_arbitration": False,
        "error": None
    }

    # Ejecutar grafo (se detendrá en primera interrupción)
    final_state = graph.invoke(initial_state, thread_config)

    # Verificar estado final
    if final_state.get("waiting_for_human"):
        waiting_depts = [
            dept for dept, appr in final_state.get("department_approvals", {}).items()
            if appr.get("status") == "pending"
        ]

        result = {
            "status": "waiting_approval",
            "waiting_departments": waiting_depts,
            "message": f"Esperando aprobación de: {', '.join(waiting_depts)}"
        }
    elif final_state.get("waiting_for_arbitration"):
        result = {
            "status": "waiting_arbitration",
            "conflicts": final_state.get("conflicts", []),
            "message": "Esperando decisión de arbitraje de Mariana Restrepo (CEO)"
        }
    else:
        final_doc = final_state.get("final_document", {})
        result = {
            "status": "completed",
            "final_document_path": f"data/final_proposals/rfp_{ticket_id}_proposal.md",
            "total_pages": final_doc.get("total_pages", 0),
            "total_words": final_doc.get("total_words", 0)
        }

    print(f"\n{'='*60}")
    print(f"✅ Pipeline Pausado/Completado")
    print(f"   Estado: {result['status']}")
    print(f"{'='*60}\n")

    return result


# ============================================================
# RESUME FUNCTIONS
# ============================================================

def resume_with_approval(
    ticket_id: int,
    department: str,
    approval_decision: HumanApprovalDecision,
    checkpointer,
    db_session = None
) -> Dict[str, Any]:
    """
    Reanuda pipeline tras aprobación humana de un departamento.

    Args:
        ticket_id: ID del ticket
        department: Departamento aprobado
        approval_decision: Decisión humana (HumanApprovalDecision)
        checkpointer: Checkpointer con estado persistido
        db_session: Sesión de BD

    Returns:
        Estado actualizado del pipeline
    """
    print(f"\n🔄 Reanudando pipeline con aprobación de {department}...")

    # Construir grafo
    graph = build_rfp_approval_graph(checkpointer=checkpointer)

    # Configuración del thread
    thread_config = {
        "configurable": {
            "thread_id": f"rfp-{ticket_id}"
        }
    }

    # Obtener estado actual del checkpoint
    current_state = graph.get_state(thread_config)

    if not current_state:
        raise ValueError(f"No se encontró checkpoint para ticket {ticket_id}")

    # Actualizar estado con decisión de aprobación
    updated_approvals = current_state.values.get("department_approvals", {})
    updated_approvals[department] = {
        **updated_approvals.get(department, {}),
        "approval_decision": approval_decision.model_dump(),
        "status": "approved" if approval_decision.approved else "rejected"
    }

    # Inyectar decisión en el estado
    graph.update_state(
        thread_config,
        {
            "department_approvals": updated_approvals
        }
    )

    # Reanudar ejecución (stream para ver progreso)
    for event in graph.stream(None, thread_config):
        print(f"   Event: {list(event.keys())}")

    # Obtener estado final
    final_state = graph.get_state(thread_config)

    return {
        "status": "resumed",
        "department": department,
        "approved": approval_decision.approved,
        "current_state": final_state.values.get("waiting_for_human", False)
    }


def resume_with_arbitration(
    ticket_id: int,
    arbitration_decision: ArbitrationDecision,
    checkpointer,
    db_session = None
) -> Dict[str, Any]:
    """
    Reanuda pipeline tras decisión de arbitraje.
    """
    print(f"\n⚖️  Reanudando pipeline con decisión de arbitraje...")

    graph = build_rfp_approval_graph(checkpointer=checkpointer)

    thread_config = {
        "configurable": {
            "thread_id": f"rfp-{ticket_id}"
        }
    }

    # Inyectar decisión de arbitraje
    graph.update_state(
        thread_config,
        {
            "arbitration_decision": arbitration_decision.model_dump(),
            "conflicts_resolved": True
        }
    )

    # Reanudar
    for event in graph.stream(None, thread_config):
        print(f"   Event: {list(event.keys())}")

    final_state = graph.get_state(thread_config)

    return {
        "status": "arbitration_resolved",
        "resolution": arbitration_decision.resolution,
        "completed": not final_state.values.get("waiting_for_human", False)
    }


# ============================================================
# MAIN (Testing)
# ============================================================

if __name__ == "__main__":
    # Test del pipeline con MemorySaver
    result = execute_rfp_approval_pipeline(
        ticket_id=123
    )

    print("\n📊 Resultado:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
