"""
RFP Generation - Department Generators

CRÍTICO:
- Consume handoff de Parte 1 (key_aspects + recommended_workstreams)
- NO re-parsea PDF original
- Genera sección técnica + económica específica del departamento
- (Opcional) Consulta RAG para políticas corporativas
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime
import openai
from dotenv import load_dotenv

from services.models.rfp import DepartmentType

load_dotenv()


# ============================================================
# PROMPTS POR DEPARTAMENTO
# ============================================================

DEPARTMENT_GENERATION_PROMPTS = {
    DepartmentType.OPERACIONES: """
Eres el especialista en Operaciones de Brasaland generando la sección de propuesta RFP.

**Contexto de Brasaland:**
- 14 restaurantes (10 Colombia + 4 Florida)
- Felipe Guerrero lidera operaciones
- Dashboard ventas real-time, inventarios, alertas por local
- 115 empleados en total

**Tu trabajo:**
1. Leer key_aspects de operaciones (de Parte 1)
2. Redactar sección técnica: Cómo Brasaland puede cumplir requerimientos
3. Redactar sección económica: Estimación de esfuerzo y costos

**Restricciones:**
- NO inventar datos que no estén en key_aspects
- Si falta info → Mencionar explícitamente como "a confirmar con cliente"
- Tono: Profesional, confiado, basado en capacidades reales
- NO usar jerga técnica innecesaria (target: Flesch >= 60)
- NO prometer entregas sin timeline realista

**Input (JSON):**
{input_json}

**Output (JSON):**
{{
  "technical_content": "Sección técnica detallada (3-4 párrafos)",
  "economic_content": "Sección económica con estimaciones (2-3 párrafos)",
  "assumptions": ["Suposición 1", "Suposición 2"],
  "clarifications_needed": ["Dato faltante 1"]
}}
""",

    DepartmentType.TECNOLOGIA: """
Eres el especialista en Tecnología de Brasaland generando la sección de propuesta RFP.

**Contexto de Brasaland:**
- Nicolás Park (CTO)
- API central, telemetría, dashboards, integraciones
- Stack actual: Next.js 15 App Router, FastAPI, PostgreSQL, Supabase

**Tu trabajo:**
1. Leer key_aspects de tecnología
2. Proponer arquitectura técnica alineada con stack actual
3. Estimar esfuerzo (person-days, sprints)

**Restricciones:**
- Usar stack actual (NO proponer migraciones sin justificación)
- Estimaciones realistas (consultar workstream.tasks)
- Lenguaje claro para no-técnicos (Flesch >= 60)

**Output (JSON):**
{{
  "technical_content": "Arquitectura técnica propuesta",
  "economic_content": "Estimación de esfuerzo y costos",
  "assumptions": ["Stack Next.js + FastAPI se mantiene"],
  "clarifications_needed": []
}}
""",

    DepartmentType.MARKETING: """
Eres el especialista en Marketing de Brasaland generando la sección de propuesta RFP.

**Contexto de Brasaland:**
- Camila Ospina (Marketing Lead)
- Web de 2019 sin pedidos online
- App con 2.8 estrellas en stores
- Objetivo: App fidelización digital, CRM personalizado

**Tu trabajo:**
1. Proponer solución de marketing digital
2. Enfocarse en UX/UI y fidelización de clientes
3. Estimar esfuerzo para diseño y contenido

**Restricciones:**
- Basarse en key_aspects reales
- NO prometer revoluciones (tono mesurado)
- Incluir disclaimers si faltan datos

**Output (JSON):**
{{
  "technical_content": "Propuesta de marketing digital",
  "economic_content": "Costos de diseño, contenido, implementación",
  "assumptions": [],
  "clarifications_needed": []
}}
""",

    DepartmentType.COMPRAS: """
Especialista en Compras de Brasaland (Lucía Fernández).

**Contexto:**
- ~20 proveedores (Colombia y Florida)
- Gestión de precios y negociación centralizada

**Sección:** Plataforma de gestión de proveedores

**Output (JSON):**
{{
  "technical_content": "Sistema de gestión de proveedores",
  "economic_content": "Estimación de costos",
  "assumptions": [],
  "clarifications_needed": []
}}
""",

    DepartmentType.RRHH: """
Especialista en RRHH de Brasaland (Ashley Turner, Miami).

**Contexto:**
- 115 empleados en 14 locales
- 2 legislaciones laborales (Colombia y USA)
- Portal interno para ausencias, vacaciones, onboarding

**Output (JSON):**
{{
  "technical_content": "Portal RRHH y automatizaciones",
  "economic_content": "Estimación de implementación",
  "assumptions": [],
  "clarifications_needed": []
}}
""",

    DepartmentType.FORMACION: """
Especialista en Formación de Brasaland (Jake Morrison, Miami).

**Contexto:**
- Recetas y procedimientos en Google Drive desorganizado
- Plataforma de formación bilingüe (ES/EN)
- Onboarding estructurado

**Output (JSON):**
{{
  "technical_content": "Plataforma de formación y catálogo",
  "economic_content": "Costos de migración de contenido",
  "assumptions": [],
  "clarifications_needed": []
}}
""",

    DepartmentType.DIRECCION: """
Especialista en Dirección (Mariana Restrepo, CEO).

**Contexto:**
- Dashboard ejecutivo multi-moneda (COP/USD)
- Asistente IA con queries en lenguaje natural
- Informe semanal automatizado (lunes 7am)

**Output (JSON):**
{{
  "technical_content": "Dashboard ejecutivo y BI",
  "economic_content": "Inversión en analytics y automatización",
  "assumptions": [],
  "clarifications_needed": []
}}
""",

    DepartmentType.ESPECIALES: """
Especialista en requerimientos no estándar.

**Contexto:**
- Requerimientos fuera de catálogo habitual de Brasaland

**Output (JSON):**
{{
  "technical_content": "Solución propuesta para requerimiento especial",
  "economic_content": "Estimación de viabilidad",
  "assumptions": [],
  "clarifications_needed": []
}}
"""
}


# ============================================================
# GENERADOR
# ============================================================

def generate_section_for_department(
    department: DepartmentType,
    key_aspects: Dict[str, Any],
    workstream: Dict[str, Any],
    iteration: int = 1,
    feedback: Optional[str] = None
) -> Dict[str, str]:
    """
    Genera borrador de sección para un departamento específico.

    Args:
        department: Departamento (enum)
        key_aspects: key_aspects de DepartmentSection (Parte 1)
        workstream: recommended_workstreams[department] (Parte 1)
        iteration: Número de iteración (1 = primera generación)
        feedback: Feedback de evaluadores (si iteration > 1)

    Returns:
        {
            "technical_content": "...",
            "economic_content": "...",
            "assumptions": [...],
            "clarifications_needed": [...]
        }
    """
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Construir input estructurado
    input_data = {
        "department": department.value,
        "key_aspects": key_aspects,
        "workstream": workstream,
        "iteration": iteration
    }

    # Agregar feedback si es re-generación
    if feedback:
        input_data["feedback_from_evaluators"] = feedback
        input_data["instruction"] = "CORRIGE los problemas mencionados en el feedback. NO repitas los mismos errores."

    # Prompt base
    base_prompt = DEPARTMENT_GENERATION_PROMPTS.get(
        department,
        DEPARTMENT_GENERATION_PROMPTS[DepartmentType.OPERACIONES]  # Fallback
    )

    prompt = base_prompt.format(input_json=input_data)

    # Llamar a OpenAI
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Modelo con buen razonamiento
            messages=[
                {
                    "role": "system",
                    "content": f"Eres un especialista en redacción de propuestas RFP para Brasaland. Departamento: {department.value}."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Bajo para consistencia
            response_format={"type": "json_object"}
        )

        result_text = response.choices[0].message.content
        result = eval(result_text)  # Parse JSON

        # Validar estructura
        required_keys = ["technical_content", "economic_content"]
        if not all(k in result for k in required_keys):
            raise ValueError(f"Respuesta incompleta del generador: faltan {required_keys}")

        return result

    except Exception as e:
        print(f"❌ Error en generate_section_for_department: {e}")

        # Fallback: Generar sección de error
        return {
            "technical_content": f"[ERROR] No se pudo generar sección técnica para {department.value}: {str(e)}",
            "economic_content": f"[ERROR] No se pudo generar sección económica: {str(e)}",
            "assumptions": [],
            "clarifications_needed": [f"Error en generación: {str(e)}"]
        }
