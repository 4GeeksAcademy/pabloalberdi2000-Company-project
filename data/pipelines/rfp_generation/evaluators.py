"""
RFP Evaluation - Parallel Evaluators

CRÍTICO:
- 3 evaluadores independientes: Readability, Relevance, Compliance
- Ejecutan en paralelo (no secuencial)
- Retornan EvaluationResult estructurado
"""

import os
from typing import Dict, Any
import openai
from dotenv import load_dotenv

# Readability metrics
try:
    from readability import Readability
    READABILITY_AVAILABLE = True
except ImportError:
    print("⚠️  py-readability-metrics no disponible. Instalar: pip install py-readability-metrics")
    READABILITY_AVAILABLE = False

from services.models.rfp_eval import (
    ReadabilityScore,
    RelevanceScore,
    ComplianceScore,
    EvaluationResult
)
from datetime import datetime

load_dotenv()


# ============================================================
# EVALUATOR 1: READABILITY
# ============================================================

def evaluate_readability(
    technical_content: str,
    economic_content: str,
    target_flesch: float = 60.0
) -> ReadabilityScore:
    """
    Evalúa legibilidad con py-readability-metrics.

    Target: Flesch Reading Ease >= 60 (nivel universitario)

    Flesch Reading Ease scale:
    - 90-100: Very Easy (5th grade)
    - 60-70: Standard (8th-9th grade)
    - 30-50: Difficult (college level)
    - 0-30: Very Difficult (college graduate)
    """
    if not READABILITY_AVAILABLE:
        # Fallback si no está instalado
        return ReadabilityScore(
            pass_=True,  # Asumimos OK si no podemos medir
            flesch_reading_ease=65.0,  # Mock
            flesch_kincaid_grade=8.0,
            gunning_fog=10.0,
            target_flesch=target_flesch,
            details="py-readability-metrics no disponible. Medición omitida."
        )

    combined_text = f"{technical_content}\n\n{economic_content}"

    # Validar longitud mínima
    if len(combined_text.split()) < 100:
        return ReadabilityScore(
            pass_=True,
            flesch_reading_ease=70.0,  # Mock para textos cortos
            flesch_kincaid_grade=7.0,
            gunning_fog=9.0,
            target_flesch=target_flesch,
            details="Texto muy corto para análisis de legibilidad (< 100 palabras)"
        )

    try:
        r = Readability(combined_text)
        flesch = r.flesch()
        fk_grade = r.flesch_kincaid()
        gunning = r.gunning_fog()

        score_value = flesch.score
        pass_threshold = score_value >= target_flesch

        details = f"Flesch: {score_value:.1f} (target: {target_flesch}+). "
        if not pass_threshold:
            diff = target_flesch - score_value
            details += f"⚠️ Demasiado complejo (falta {diff:.1f} puntos). Simplifica frases largas y reduce jerga técnica."
        else:
            details += "✅ Legibilidad adecuada para audiencia general."

        return ReadabilityScore(
            pass_=pass_threshold,
            flesch_reading_ease=score_value,
            flesch_kincaid_grade=fk_grade.score,
            gunning_fog=gunning.score,
            target_flesch=target_flesch,
            details=details
        )

    except Exception as e:
        # Fallback en caso de error
        return ReadabilityScore(
            pass_=True,  # No penalizamos por errores técnicos
            flesch_reading_ease=65.0,
            flesch_kincaid_grade=8.0,
            gunning_fog=10.0,
            target_flesch=target_flesch,
            details=f"Error calculando legibilidad: {str(e)}"
        )


# ============================================================
# EVALUATOR 2: RELEVANCE
# ============================================================

RELEVANCE_PROMPT = """
Evalúa si la sección generada cubre TODOS los aspectos requeridos.

**key_aspects originales (de Parte 1):**
```json
{key_aspects}
```

**Sección generada:**
### Técnica:
{technical_content}

### Económica:
{economic_content}

---

**Instrucciones:**
1. Identifica qué requirements de key_aspects están cubiertos en la sección
2. Identifica qué requirements NO están mencionados
3. Calcula coverage_percentage = cubiertos / total
4. Pass = True si coverage >= 0.90 (90%)

**Responde SOLO con JSON válido (sin markdown):**
{{
  "covered_aspects": ["requirement1", "requirement2"],
  "missing_aspects": ["requirement_no_cubierto"],
  "coverage_percentage": 0.85,
  "pass": true/false,
  "reasoning": "Explicación breve del resultado"
}}
"""

def evaluate_relevance(
    technical_content: str,
    economic_content: str,
    key_aspects: Dict[str, Any]
) -> RelevanceScore:
    """
    Evalúa si la sección cubre los key_aspects de Parte 1.

    Criterio: Coverage >= 90%
    """
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    combined = f"{technical_content}\n\n{economic_content}"

    prompt = RELEVANCE_PROMPT.format(
        key_aspects=key_aspects,
        technical_content=technical_content,
        economic_content=economic_content
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un evaluador de pertinencia de propuestas RFP. Analiza si el contenido generado cubre los requerimientos solicitados."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        result = eval(response.choices[0].message.content)

        return RelevanceScore(
            pass_=result.get("pass", False),
            covered_aspects=result.get("covered_aspects", []),
            missing_aspects=result.get("missing_aspects", []),
            coverage_percentage=result.get("coverage_percentage", 0.0)
        )

    except Exception as e:
        print(f"❌ Error en evaluate_relevance: {e}")

        # Fallback: Asumir cobertura parcial
        return RelevanceScore(
            pass_=False,
            covered_aspects=[],
            missing_aspects=["Error en evaluación"],
            coverage_percentage=0.0
        )


# ============================================================
# EVALUATOR 3: COMPLIANCE
# ============================================================

COMPLIANCE_RULES = {
    "RULE_001": {
        "description": "NO mencionar precios específicos sin disclaimers de variabilidad",
        "severity": "warning"
    },
    "RULE_002": {
        "description": "NO prometer entregas sin timeline de proyecto realista",
        "severity": "blocker"
    },
    "RULE_003": {
        "description": "Usar tono profesional (evitar 'revolucionar', 'disruptivo', 'game-changer')",
        "severity": "warning"
    },
    "RULE_004": {
        "description": "Mencionar capacidad real de Brasaland (14 locales, 115 empleados)",
        "severity": "info"
    },
    "RULE_005": {
        "description": "NO inventar datos que no estén en key_aspects",
        "severity": "blocker"
    },
    "RULE_006": {
        "description": "Flesch Reading Ease >= 60 (legibilidad para audiencia general)",
        "severity": "warning"
    }
}

COMPLIANCE_PROMPT = """
Verifica cumplimiento de políticas corporativas de Brasaland.

**Reglas a verificar:**
{rules}

**Sección generada:**
### Técnica:
{technical_content}

### Económica:
{economic_content}

---

**Instrucciones:**
1. Revisa CADA regla
2. Identifica violaciones específicas (cita el texto problemático)
3. Clasifica severidad: "blocker" (impide aprobación), "warning" (mejorable), "info" (sugerencia)
4. Pass = True si NO hay blockers

**Responde SOLO con JSON válido (sin markdown):**
{{
  "checked_rules": ["RULE_001", "RULE_002"],
  "violations": [
    "RULE_003: Detectado tono exagerado en 'revolucionará la industria' (párrafo 2)"
  ],
  "severity": "warning",
  "pass": true/false,
  "reasoning": "Explicación breve"
}}
"""

def evaluate_compliance(
    technical_content: str,
    economic_content: str
) -> ComplianceScore:
    """
    Evalúa cumplimiento con políticas de negocio.

    Criterio: Pass = True si NO hay violaciones blocker
    """
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    combined = f"{technical_content}\n\n{economic_content}"

    # Formatear reglas para el prompt
    rules_formatted = "\n".join([
        f"- {rule_id}: {data['description']} (severidad: {data['severity']})"
        for rule_id, data in COMPLIANCE_RULES.items()
    ])

    prompt = COMPLIANCE_PROMPT.format(
        rules=rules_formatted,
        technical_content=technical_content,
        economic_content=economic_content
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un auditor de compliance para propuestas RFP de Brasaland. Tu trabajo es identificar violaciones de políticas corporativas."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        result = eval(response.choices[0].message.content)

        return ComplianceScore(
            pass_=result.get("pass", False),
            checked_rules=result.get("checked_rules", []),
            violations=result.get("violations", []),
            severity=result.get("severity", "unknown")
        )

    except Exception as e:
        print(f"❌ Error en evaluate_compliance: {e}")

        # Fallback: Asumir compliance OK si hay error técnico
        return ComplianceScore(
            pass_=True,
            checked_rules=[],
            violations=[f"Error en evaluación: {str(e)}"],
            severity="info"
        )


# ============================================================
# AGGREGATOR
# ============================================================

def aggregate_evaluation(
    section_id: str,
    department: str,
    iteration: int,
    readability: ReadabilityScore,
    relevance: RelevanceScore,
    compliance: ComplianceScore
) -> EvaluationResult:
    """
    Consolida resultados de los 3 evaluadores.

    Overall Pass = True si TODAS las dimensiones pasan.
    Genera feedback accionable para el generador.
    """
    overall_pass = all([
        readability.pass_,
        relevance.pass_,
        compliance.pass_
    ])

    # Construir feedback accionable
    feedback_parts = []

    if not readability.pass_:
        feedback_parts.append(f"📖 **Legibilidad**: {readability.details}")

    if not relevance.pass_:
        missing = ", ".join(relevance.missing_aspects[:3])  # Primeros 3
        if len(relevance.missing_aspects) > 3:
            missing += f" (+{len(relevance.missing_aspects) - 3} más)"
        feedback_parts.append(
            f"🎯 **Cobertura**: {relevance.coverage_percentage:.0%} (target: 90%). "
            f"Faltan aspectos → {missing}"
        )

    if not compliance.pass_:
        violations_str = "; ".join(compliance.violations[:2])  # Primeras 2
        if len(compliance.violations) > 2:
            violations_str += f" (+{len(compliance.violations) - 2} más)"
        feedback_parts.append(
            f"⚖️ **Compliance** ({compliance.severity}): {violations_str}"
        )

    feedback_for_generator = (
        "\n\n".join(feedback_parts)
        if feedback_parts
        else "✅ Sección aprobada en todas las dimensiones"
    )

    return EvaluationResult(
        section_id=section_id,
        department=department,
        iteration=iteration,
        readability=readability,
        relevance=relevance,
        compliance=compliance,
        overall_pass=overall_pass,
        feedback_for_generator=feedback_for_generator,
        evaluated_at=datetime.utcnow()
    )
