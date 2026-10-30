"""
RFP Intake Graph - Multi-Agent LangGraph Pipeline

Pipeline multi-agente para análisis de RFPs:
1. Classifier: Valida si documento es RFP legítima
2. Orchestrator: Descompone en workstreams por departamento
3. Workers: Procesamiento paralelo por departamento (7 workers)
4. Synthesizer: Consolidación y detección de conflictos

CRÍTICO:
- Grafo INDEPENDIENTE (NO contaminar con CX/knowledge-agent)
- Workers NO inventan datos (reportan missing_data)
- Synthesizer detecta conflictos entre departamentos
- Persistencia transaccional en PostgreSQL
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
import openai
from dotenv import load_dotenv

from services.models.rfp import (
    RFPTicket,
    RFPMetadata,
    DepartmentSection,
    RFPSynthesis,
    DepartmentType,
    RFPTicketStatus
)

load_dotenv()

# ============================================================
# STATE SCHEMA
# ============================================================

class RFPState(TypedDict):
    """Estado compartido del grafo de RFP intake"""

    # Input
    ticket_id: int
    markdown_content: str
    markdown_path: str

    # Metadatos globales
    client_name: Optional[str]
    submission_deadline: Optional[str]
    budget_range: Optional[str]
    project_title: Optional[str]

    # Resultados de clasificación
    is_valid_rfp: Optional[bool]
    classifier_confidence: Optional[float]
    rejection_reason: Optional[str]

    # Descomposición
    workstreams: Dict[str, Dict[str, Any]]  # Por departamento

    # Resultados de workers
    department_findings: Dict[str, Dict[str, Any]]  # key_aspects por dept

    # Síntesis final
    executive_summary: Optional[str]
    synthesis_data: Optional[Dict[str, Any]]

    # Control de flujo
    should_discard: bool
    error: Optional[str]


# ============================================================
# PROMPTS
# ============================================================

CLASSIFIER_PROMPT = """Eres un clasificador especializado de documentos RFP (Request for Proposal) para Brasaland, una cadena de 14 restaurantes en Colombia y Florida.

Analiza el siguiente documento y determina si es una RFP válida.

**Criterios de RFP válida:**
1. ✅ Solicitud explícita de propuesta, cotización o servicios
2. ✅ Especificaciones técnicas o requerimientos claros
3. ✅ Plazos de entrega o submission deadline mencionados
4. ✅ Datos del solicitante (empresa, contacto, proyecto)

**Criterios de descarte:**
1. ❌ Documento interno (políticas, manuales, procedimientos)
2. ❌ Factura, recibo o contrato ya firmado
3. ❌ Spam o solicitud genérica masiva
4. ❌ CV, currículum o solicitud de empleo

**Lógica anti-falso-negativo:**
- Si confianza < 0.7: NO descartes automáticamente
- Marca como "requiere_revision_manual" en lugar de descarte
- Prioriza permitir dudosos (costo de falso negativo > falso positivo)

Responde SOLO con JSON válido (sin markdown):
{{
  "is_valid_rfp": true/false,
  "confidence": 0.0-1.0,
  "rejection_reason": "..." (solo si no válida),
  "detected_project_type": "...",
  "requires_manual_review": true/false,
  "extracted_metadata": {{
    "client_name": "...",
    "submission_deadline": "...",
    "budget_range": "...",
    "project_title": "..."
  }}
}}

**Documento:**
{markdown_content}
"""


ORCHESTRATOR_PROMPT = """Eres el orquestador de análisis de RFPs para Brasaland (14 restaurantes en Colombia y Florida).

Tu trabajo es descomponer la RFP en secciones asignadas a cada departamento relevante.

**Departamentos disponibles (según company-BRIEFING.md):**
1. **operaciones** (Felipe Guerrero): Ventas, inventario, pedidos, alertas por local
2. **compras** (Lucía Fernández): Proveedores, precios, negociación, gestión de compras
3. **marketing** (Camila Ospina): Web, app, CRM, fidelización, pedidos online
4. **rrhh** (Ashley Turner): Personal, contratación, portal interno, onboarding
5. **formacion** (Jake Morrison): Recetas, procedimientos, capacitación, actualizaciones
6. **tecnologia** (Nicolás Park): API central, telemetría, dashboards, integraciones
7. **direccion** (Mariana Restrepo): Dashboard ejecutivo, reportes, BI
8. **especiales**: Requerimientos no estándar fuera de catálogo

**Instrucciones:**
- Identifica qué departamentos deben intervenir según los requerimientos
- Extrae la sección de texto relevante para cada departamento
- Si un requerimiento no encaja en departamentos estándar → asigna a "especiales"
- Incluye metadatos globales (plazos, cliente) en cada workstream

Responde SOLO con JSON válido:
{{
  "workstreams": {{
    "operaciones": {{
      "section_title": "...",
      "extracted_text": "...",
      "priority": "alta|media|baja",
      "metadata": {{
        "deadline": "...",
        "estimated_complexity": "alta|media|baja"
      }}
    }},
    "tecnologia": {{ ... }}
  }},
  "involved_departments": ["operaciones", "tecnologia", ...]
}}

**RFP validada:**
Cliente: {client_name}
Deadline: {submission_deadline}
Presupuesto: {budget_range}

{markdown_content}
"""


WORKER_PROMPT = """Eres el especialista del departamento de **{department}** en Brasaland.

**Tu área de responsabilidad:**
{department_description}

Analiza ÚNICAMENTE la sección asignada a tu departamento y extrae:

**Estructura de respuesta (key_aspects):**
{{
  "requirements": ["req1", "req2", ...],  // Requerimientos técnicos claros
  "constraints": ["constraint1", ...],     // Restricciones o limitaciones
  "missing_data": ["dato1", "dato2"],     // Datos críticos que NO aparecen
  "estimated_effort": "alto|medio|bajo",   // Basado SOLO en lo descrito
  "blockers": ["blocker1", ...],          // Impedimentos detectados
  "dependencies": ["dept1", "dept2"],      // Dependencias con otros departamentos
  "notes": "Observaciones adicionales"
}}

**REGLAS CRÍTICAS:**
❌ NO INVENTES datos que no están en el documento
❌ NO ESTIMES presupuestos o volúmenes sin datos explícitos
❌ NO ASUMAS información no mencionada
✅ SI FALTA información crítica → repórtala en missing_data
✅ SI hay ambigüedad → anótala en notes

**Metadatos globales:**
Cliente: {client_name}
Deadline: {submission_deadline}
Presupuesto: {budget_range}

**Sección asignada:**
{section_text}

Responde SOLO con JSON válido (el objeto key_aspects):
"""


SYNTHESIZER_PROMPT = """Eres el sintetizador de análisis de RFPs para el equipo de Ventas de Brasaland.

Has recibido los análisis de {num_departments} departamentos. Tu trabajo es consolidar los hallazgos en un reporte ejecutivo.

**Responsabilidades:**
1. **Executive Summary**: Resumen de 2-3 párrafos para Ventas
2. **Departamentos involucrados**: Lista completa
3. **Dependencias críticas**: Interacciones entre departamentos
4. **Riesgos identificados**: Con severidad (alta/media/baja)
5. **Datos faltantes**: Información bloqueante que falta
6. **Workstreams recomendados**: Estructura de trabajo paralelo

**Detección de conflictos:**
- Si 2 departamentos reportan plazos distintos → alerta en riesgos
- Si > 2 departamentos tienen missing_data crítica → escalar
- Si hay blockers en múltiples departamentos → dependencia crítica

**Hallazgos por departamento:**
{department_findings_json}

**Metadatos globales:**
Cliente: {client_name}
Deadline: {submission_deadline}
Presupuesto: {budget_range}

Responde SOLO con JSON válido:
{{
  "executive_summary": "...",
  "involved_departments": ["dept1", "dept2"],
  "critical_dependencies": ["Operaciones necesita datos de Compras antes de..."],
  "identified_risks": [
    {{"risk": "...", "severity": "alta", "mitigation": "..."}}
  ],
  "missing_critical_data": ["presupuesto específico", "plazo de implementación"],
  "recommended_workstreams": {{
    "operaciones": {{
      "lead": "Felipe Guerrero",
      "tasks": ["task1", "task2"],
      "deadline": "...",
      "dependencies": []
    }}
  }},
  "synthesis_confidence": 0.0-1.0
}}
"""


# Descripciones de departamentos
DEPARTMENT_DESCRIPTIONS = {
    DepartmentType.OPERACIONES: "Ventas, inventario, pedidos, alertas, gestión de 14 locales",
    DepartmentType.COMPRAS: "Proveedores, precios, negociación, gestión de ~20 proveedores",
    DepartmentType.MARKETING: "Web, app, CRM, fidelización, pedidos online, personalización",
    DepartmentType.RRHH: "Personal, contratación, portal interno, onboarding, KPIs de RRHH",
    DepartmentType.FORMACION: "Recetas, procedimientos, capacitación, actualizaciones ES/EN",
    DepartmentType.TECNOLOGIA: "API central, telemetría, dashboards, integraciones técnicas",
    DepartmentType.DIRECCION: "Dashboard ejecutivo, reportes semanales, BI, análisis",
    DepartmentType.ESPECIALES: "Requerimientos no estándar fuera de catálogo"
}


# ============================================================
# NODOS DEL GRAFO
# ============================================================

def classifier_node(state: RFPState) -> RFPState:
    """
    Nodo 1: Classifier Agent

    Valida si el documento es una RFP legítima.
    Si no válida → marca should_discard=True
    Si confianza baja → permite pero marca para revisión manual
    """
    print(f"\n[CLASSIFIER] Analizando documento...")

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = CLASSIFIER_PROMPT.format(
        markdown_content=state["markdown_content"][:8000]  # Limitar tokens
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        print(f"[CLASSIFIER] Resultado: is_valid={result['is_valid_rfp']}, "
              f"confidence={result['confidence']:.2f}")

        # Extraer metadatos
        metadata = result.get("extracted_metadata", {})

        # Actualizar estado
        return {
            **state,
            "is_valid_rfp": result["is_valid_rfp"],
            "classifier_confidence": result["confidence"],
            "rejection_reason": result.get("rejection_reason"),
            "should_discard": not result["is_valid_rfp"] and result["confidence"] >= 0.7,
            "client_name": metadata.get("client_name"),
            "submission_deadline": metadata.get("submission_deadline"),
            "budget_range": metadata.get("budget_range"),
            "project_title": metadata.get("project_title")
        }

    except Exception as e:
        print(f"[CLASSIFIER] ❌ Error: {e}")
        return {
            **state,
            "error": f"Classifier error: {str(e)}",
            "should_discard": True
        }


def orchestrator_node(state: RFPState) -> RFPState:
    """
    Nodo 2: Orchestrator Agent

    Descompone RFP en workstreams por departamento.
    """
    print(f"\n[ORCHESTRATOR] Descomponiendo RFP en departamentos...")

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = ORCHESTRATOR_PROMPT.format(
        client_name=state.get("client_name", "No especificado"),
        submission_deadline=state.get("submission_deadline", "No especificado"),
        budget_range=state.get("budget_range", "No especificado"),
        markdown_content=state["markdown_content"][:10000]
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        workstreams = result.get("workstreams", {})
        print(f"[ORCHESTRATOR] Departamentos identificados: {list(workstreams.keys())}")

        return {
            **state,
            "workstreams": workstreams,
            "department_findings": {}  # Inicializar findings vacíos
        }

    except Exception as e:
        print(f"[ORCHESTRATOR] ❌ Error: {e}")
        return {
            **state,
            "error": f"Orchestrator error: {str(e)}",
            "workstreams": {}
        }


def department_worker_node(state: RFPState, department: DepartmentType) -> RFPState:
    """
    Nodo 3: Department Worker

    Procesa sección asignada a un departamento específico.

    Args:
        state: Estado compartido
        department: Departamento a procesar

    Returns:
        Estado con findings del departamento agregados
    """
    dept_key = department.value

    # Verificar si hay workstream para este departamento
    if dept_key not in state.get("workstreams", {}):
        print(f"[WORKER:{dept_key}] Sin workstream asignado, skipping...")
        return state

    print(f"[WORKER:{dept_key}] Procesando sección...")

    workstream = state["workstreams"][dept_key]
    section_text = workstream.get("extracted_text", "")

    if not section_text:
        print(f"[WORKER:{dept_key}] ⚠️  Sin texto asignado")
        return state

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = WORKER_PROMPT.format(
        department=dept_key,
        department_description=DEPARTMENT_DESCRIPTIONS[department],
        client_name=state.get("client_name", "No especificado"),
        submission_deadline=state.get("submission_deadline", "No especificado"),
        budget_range=state.get("budget_range", "No especificado"),
        section_text=section_text[:6000]
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        key_aspects = json.loads(response.choices[0].message.content)

        print(f"[WORKER:{dept_key}] ✅ Análisis completado")
        print(f"  Requirements: {len(key_aspects.get('requirements', []))}")
        print(f"  Missing data: {len(key_aspects.get('missing_data', []))}")

        # Agregar findings al estado
        department_findings = state.get("department_findings", {})
        department_findings[dept_key] = key_aspects

        return {
            **state,
            "department_findings": department_findings
        }

    except Exception as e:
        print(f"[WORKER:{dept_key}] ❌ Error: {e}")
        return state


def synthesizer_node(state: RFPState) -> RFPState:
    """
    Nodo 4: Synthesizer Agent

    Consolida findings de todos los workers y genera reporte ejecutivo.
    """
    print(f"\n[SYNTHESIZER] Consolidando análisis de {len(state.get('department_findings', {}))} departamentos...")

    department_findings = state.get("department_findings", {})

    if not department_findings:
        print(f"[SYNTHESIZER] ⚠️  Sin findings para consolidar")
        return {
            **state,
            "error": "No department findings to synthesize"
        }

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = SYNTHESIZER_PROMPT.format(
        num_departments=len(department_findings),
        department_findings_json=json.dumps(department_findings, indent=2),
        client_name=state.get("client_name", "No especificado"),
        submission_deadline=state.get("submission_deadline", "No especificado"),
        budget_range=state.get("budget_range", "No especificado")
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        synthesis = json.loads(response.choices[0].message.content)

        print(f"[SYNTHESIZER] ✅ Síntesis completada")
        print(f"  Departamentos involucrados: {len(synthesis.get('involved_departments', []))}")
        print(f"  Riesgos identificados: {len(synthesis.get('identified_risks', []))}")
        print(f"  Datos faltantes: {len(synthesis.get('missing_critical_data', []))}")

        return {
            **state,
            "executive_summary": synthesis.get("executive_summary"),
            "synthesis_data": synthesis
        }

    except Exception as e:
        print(f"[SYNTHESIZER] ❌ Error: {e}")
        return {
            **state,
            "error": f"Synthesizer error: {str(e)}"
        }


# ============================================================
# BUILD GRAPH
# ============================================================

def build_rfp_intake_graph() -> StateGraph:
    """
    Construye el grafo de LangGraph para RFP intake.

    Flujo:
    classifier → [descartado → END | continuar → orchestrator]
              → workers (paralelo) → synthesizer → END

    Returns:
        Grafo compilado
    """
    workflow = StateGraph(RFPState)

    # Agregar nodos
    workflow.add_node("classifier", classifier_node)
    workflow.add_node("orchestrator", orchestrator_node)

    # Workers por departamento
    for dept in DepartmentType:
        workflow.add_node(
            f"worker_{dept.value}",
            lambda s, d=dept: department_worker_node(s, d)
        )

    workflow.add_node("synthesizer", synthesizer_node)

    # Entry point
    workflow.set_entry_point("classifier")

    # Edges condicionales desde classifier
    def should_continue_after_classifier(state: RFPState) -> Literal["discard", "continue"]:
        return "discard" if state.get("should_discard") else "continue"

    workflow.add_conditional_edges(
        "classifier",
        should_continue_after_classifier,
        {
            "discard": END,
            "continue": "orchestrator"
        }
    )

    # Orchestrator → Workers (todos en paralelo)
    for dept in DepartmentType:
        workflow.add_edge("orchestrator", f"worker_{dept.value}")

    # Workers → Synthesizer (convergencia)
    for dept in DepartmentType:
        workflow.add_edge(f"worker_{dept.value}", "synthesizer")

    # Synthesizer → END
    workflow.add_edge("synthesizer", END)

    print("✅ Grafo RFP Intake construido con éxito")
    print(f"   Nodos: classifier + orchestrator + {len(DepartmentType)} workers + synthesizer")

    return workflow.compile()


# ============================================================
# EJECUCIÓN DEL PIPELINE
# ============================================================

def execute_rfp_pipeline(
    ticket_id: int,
    markdown_path: str,
    markdown_content: str,
    db_session
) -> Dict[str, Any]:
    """
    Ejecuta el pipeline completo de RFP intake.

    Args:
        ticket_id: ID del ticket en BD
        markdown_path: Ruta del Markdown convertido
        markdown_content: Contenido del Markdown
        db_session: Sesión de DB para persistir resultados

    Returns:
        Dict con resultado final del pipeline
    """
    print(f"\n{'='*70}")
    print(f"🚀 Ejecutando RFP Pipeline para ticket {ticket_id}")
    print(f"{'='*70}\n")

    # Construir grafo
    graph = build_rfp_intake_graph()

    # Estado inicial
    initial_state: RFPState = {
        "ticket_id": ticket_id,
        "markdown_content": markdown_content,
        "markdown_path": markdown_path,
        "client_name": None,
        "submission_deadline": None,
        "budget_range": None,
        "project_title": None,
        "is_valid_rfp": None,
        "classifier_confidence": None,
        "rejection_reason": None,
        "workstreams": {},
        "department_findings": {},
        "executive_summary": None,
        "synthesis_data": None,
        "should_discard": False,
        "error": None
    }

    try:
        # Ejecutar grafo
        final_state = graph.invoke(initial_state)

        print(f"\n{'='*70}")
        print(f"✅ Pipeline completado para ticket {ticket_id}")
        print(f"{'='*70}\n")

        # Persistir resultados en BD
        _persist_results(ticket_id, final_state, db_session)

        return {
            "success": True,
            "ticket_id": ticket_id,
            "status": "descartado" if final_state.get("should_discard") else "analisis_completo",
            "final_state": final_state
        }

    except Exception as e:
        print(f"\n❌ Error en pipeline: {e}")

        # Actualizar ticket con error
        ticket = db_session.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()
        if ticket:
            ticket.status = RFPTicketStatus.ERROR
            ticket.error_message = str(e)
            ticket.updated_at = datetime.utcnow()
            db_session.commit()

        return {
            "success": False,
            "ticket_id": ticket_id,
            "error": str(e)
        }


def _persist_results(ticket_id: int, final_state: RFPState, db_session):
    """Persiste resultados del pipeline en BD"""

    ticket = db_session.query(RFPTicket).filter(RFPTicket.id == ticket_id).first()
    if not ticket:
        print(f"⚠️  Ticket {ticket_id} no encontrado en BD")
        return

    # Actualizar ticket
    if final_state.get("should_discard"):
        ticket.status = RFPTicketStatus.DESCARTADO
        ticket.rejection_reason = final_state.get("rejection_reason")
    else:
        ticket.status = RFPTicketStatus.ANALISIS_COMPLETO

    ticket.is_valid_rfp = final_state.get("is_valid_rfp")
    ticket.classifier_confidence = final_state.get("classifier_confidence")
    ticket.updated_at = datetime.utcnow()

    # Crear/actualizar metadata
    if ticket.metadata:
        metadata = ticket.metadata
    else:
        metadata = RFPMetadata(ticket_id=ticket_id)
        db_session.add(metadata)

    metadata.client_name = final_state.get("client_name")
    metadata.submission_deadline = final_state.get("submission_deadline")
    metadata.budget_range = final_state.get("budget_range")

    # Crear secciones por departamento
    for dept_key, key_aspects in final_state.get("department_findings", {}).items():
        section = DepartmentSection(
            ticket_id=ticket_id,
            department=DepartmentType(dept_key),
            section_title=final_state.get("workstreams", {}).get(dept_key, {}).get("section_title"),
            extracted_text=final_state.get("workstreams", {}).get(dept_key, {}).get("extracted_text"),
            key_aspects=key_aspects,
            processed_at=datetime.utcnow()
        )
        db_session.add(section)

    # Crear síntesis
    if final_state.get("synthesis_data") and not final_state.get("should_discard"):
        synthesis_data = final_state["synthesis_data"]
        synthesis = RFPSynthesis(
            ticket_id=ticket_id,
            executive_summary=synthesis_data.get("executive_summary", ""),
            involved_departments=synthesis_data.get("involved_departments", []),
            critical_dependencies=synthesis_data.get("critical_dependencies", []),
            identified_risks=synthesis_data.get("identified_risks", []),
            missing_critical_data=synthesis_data.get("missing_critical_data", []),
            recommended_workstreams=synthesis_data.get("recommended_workstreams", {}),
            synthesis_confidence=synthesis_data.get("synthesis_confidence", 0.0),
            synthesized_at=datetime.utcnow()
        )
        db_session.add(synthesis)

    db_session.commit()
    print(f"✅ Resultados persistidos en BD para ticket {ticket_id}")
