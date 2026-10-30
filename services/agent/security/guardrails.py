"""
Guardrails Deterministas - Input, Context Sanitization & Output Guards

Implementa validación multicapa sin depender de LLM para estabilidad en CI/CD.

Protecciones implementadas:
1. Input Guard: Detecta prompt injection, jailbreaking, tareas fuera de alcance
2. Context Sanitizer: Neutraliza inyecciones indirectas en RAG/tools
3. Output Guard: Previene fugas de system prompt, PII, datos confidenciales

CRÍTICO:
- Guardrails son DETERMINISTAS (regex, clasificadores locales, reglas)
- NO invocan LLM (estabilidad en tests de CI)
- Logs estructurados para métricas de seguridad
"""

import re
from typing import Tuple, Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import structlog

logger = structlog.get_logger()

# ============================================================
# TIPOS Y ENUMS
# ============================================================

class ThreatType(str, Enum):
    """Tipos de amenazas detectadas"""
    JAILBREAK = "jailbreak"                    # Intento de cambiar instrucciones
    PROMPT_INJECTION = "prompt_injection"      # Inyección de prompt directo
    OUT_OF_SCOPE = "out_of_scope"             # Tarea fuera de dominio
    INDIRECT_INJECTION = "indirect_injection"  # Inyección vía RAG/tools
    PII_LEAK = "pii_leak"                     # Fuga de PII en salida
    SYSTEM_PROMPT_LEAK = "system_prompt_leak" # Fuga de instrucciones internas
    STRUCTURAL_INVALID = "structural_invalid"  # Respuesta malformada
    NONE = "none"                             # Sin amenaza detectada


@dataclass
class InputGuardResult:
    """Resultado de validación de entrada"""
    is_safe: bool
    threat_type: Optional[ThreatType]
    reason: Optional[str]
    sanitized_input: str
    confidence: float  # 0.0 - 1.0


@dataclass
class OutputGuardResult:
    """Resultado de validación de salida"""
    is_safe: bool
    threat_type: Optional[ThreatType]
    reason: Optional[str]
    sanitized_output: str
    confidence: float


# ============================================================
# PATRONES DE DETECCIÓN
# ============================================================

# Patrones de jailbreak (intento de cambiar instrucciones)
JAILBREAK_PATTERNS = [
    # Comandos directos
    r"(?i)(ignora|olvida|descarta|borra|elimina)\s+(todas?\s+)?((tus|las)\s+)?(instrucciones?|reglas?|directivas?|restricciones?|limitaciones?)\s+(anteriores?|previas?|pasadas?)?",
    r"(?i)ahora\s+eres(\s+un)?\s+(asistente|chatbot|ai|modelo)\s+(sin\s+)?(reglas?|restricciones?|límites?)",
    r"(?i)(act|comportate|funciona|opera)\s+como\s+(si\s+)?(fueras|fuera)\s+un\s+",
    r"(?i)nuevo\s+(modo|rol|persona|personaje|sistema):",
    r"(?i)(simula|finge|pretende)\s+que\s+(eres|no\s+eres)",

    # Metacomandos
    r"(?i)system\s*:\s*",
    r"(?i)<\s*system\s*>",
    r"(?i)\/\s*(system|prompt|instructions|rules)",
    r"(?i)@\s*(system|admin|root)",

    # Inyección de roles
    r"(?i)(developer|admin|root)\s+(mode|access|override)",
    r"(?i)(enable|activate|switch\s+to)\s+(admin|debug|god)\s+mode",

    # Bypass de restricciones
    r"(?i)(ignora|bypass|skip|evita|salta)\s+(la|tu)\s+(restricción|limitación|política|regla)",
    r"(?i)sin\s+(ninguna|ningún)\s+(restricción|regla|límite|filtro)",

    # Reescritura de propósito
    r"(?i)(ya\s+no|deja\s+de)\s+(trabajas?|eres)\s+(para|de)\s+brasaland",
    r"(?i)olvida\s+(que\s+)?(trabajas?|eres\s+de)\s+brasaland",
]

# Patrones de prompt injection indirecto (en contenido externo)
INDIRECT_INJECTION_PATTERNS = [
    r"(?i)<!--\s*system\s*-->",
    r"(?i)\[SYSTEM_OVERRIDE\]",
    r"(?i)\{system:\s*[^\}]+\}",
    r"(?i)__INJECT__:",
    r"(?i)<script>",
    r"(?i)javascript:",
]

# Patrones de tareas fuera de alcance
OUT_OF_SCOPE_PATTERNS = [
    # Tareas académicas
    r"(?i)(escribe|redacta|hazme)\s+(un|una)\s+(ensayo|tesis|trabajo|proyecto|informe)\s+(sobre|de|acerca)",
    r"(?i)(resuelve|ayudame\s+con|hazme)\s+(este|estos|mi)\s+(problema|ejercicio|tarea|deber)s?\s+(de|del?)\s+(matemáticas?|física|química|programación|código)",

    # Creación de contenido ajeno
    r"(?i)(escribe|crea|genera)(me)?\s+(un|una)\s+(poema|canción|cuento|historia|novela|rap|verso)",
    r"(?i)(traduce|traduceme)\s+.+\s+(al?|a)\s+(inglés|español|francés|alemán|italiano|portugués)",

    # Código ajeno al stack
    r"(?i)(escribe|crea|hazme)\s+(un|una)\s+(función|clase|programa|script|código)\s+(en|de)\s+(php|ruby|java|c\+\+|rust|go|swift|kotlin)",

    # Tareas personales
    r"(?i)(planifica|organiza|ayudame\s+con)\s+(mi\s+)?(boda|cumpleaños|viaje|vacaciones|fiesta)",
    r"(?i)(dame|necesito|quiero)\s+(consejos?|recomendaciones?|tips?)\s+(de|para|sobre)\s+(amor|relaciones|psicología|salud|fitness|dieta)",

    # Juegos y entretenimiento
    r"(?i)(juega|juguemos|vamos\s+a\s+jugar)\s+(a|al?)\s+",
    r"(?i)(cuenta|contame|narrá)(me)?\s+(un|una)\s+(chiste|historia|anécdota)",
]

# Keywords de dominio Brasaland (permitidas)
BRASALAND_DOMAIN_KEYWORDS = [
    # Negocio
    "brasaland", "restaurante", "local", "comida", "plato", "menú", "cocina", "brasa",
    "cliente", "pedido", "reserva", "delivery", "factura", "ventas",

    # Locaciones
    "medellín", "medellin", "bogotá", "bogota", "cali", "cartagena", "barranquilla",
    "miami", "orlando", "tampa", "florida", "colombia",

    # Operaciones
    "ticket", "incidencia", "incidente", "estado", "progreso", "id",
    "inventario", "stock", "producto", "proveedor", "compras",

    # RRHH
    "candidato", "empleado", "personal", "contratación", "vacante", "puesto",
    "cocinero", "mesero", "cajero", "supervisor", "gerente",

    # Sistemas
    "ats", "análisis", "reporte", "dashboard", "métrica", "kpi",
]

# Patrones de PII en salida
PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
    r"\b\d{10}\b",  # DNI/NIF
    r"\b\d{16}\b",  # Credit card
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email (si no es del dominio)
]

# Patrones de fuga de system prompt
SYSTEM_PROMPT_LEAK_PATTERNS = [
    r"(?i)(system\s+prompt|instrucciones\s+del\s+sistema):",
    r"(?i)mis\s+instrucciones\s+(son|dicen|indican)",
    r"(?i)(fui\s+)?(configurado|programado|entrenado)\s+para",
    r"(?i)como\s+(asistente|agente|ia)\s+de\s+brasaland,\s+(debo|tengo\s+que|mi\s+función)",
]


# ============================================================
# SECURITY GUARDRAILS CLASS
# ============================================================

class SecurityGuardrails:
    """
    Guardrails de seguridad deterministas para el agente.

    Implementa validación multicapa sin depender de LLM.
    """

    def __init__(self):
        """Inicializa guardrails con métricas vacías"""
        self.metrics = {
            "total_inputs_checked": 0,
            "total_outputs_checked": 0,
            "threats_blocked": {threat.value: 0 for threat in ThreatType if threat != ThreatType.NONE},
            "safe_interactions": 0
        }

        logger.info("security_guardrails_initialized")

    # ========================================
    # INPUT GUARD
    # ========================================

    def validate_input(self, user_input: str) -> InputGuardResult:
        """
        Valida entrada del usuario contra amenazas conocidas.

        Args:
            user_input: Texto de entrada del usuario

        Returns:
            InputGuardResult con validación y input sanitizado
        """
        self.metrics["total_inputs_checked"] += 1

        logger.info("input_guard_checking", input_length=len(user_input))

        # 1. Detectar jailbreak
        jailbreak_result = self._detect_jailbreak(user_input)
        if not jailbreak_result[0]:
            self.metrics["threats_blocked"]["jailbreak"] += 1
            return InputGuardResult(
                is_safe=False,
                threat_type=ThreatType.JAILBREAK,
                reason=jailbreak_result[1],
                sanitized_input="",
                confidence=jailbreak_result[2]
            )

        # 2. Detectar prompt injection directo
        injection_result = self._detect_prompt_injection(user_input)
        if not injection_result[0]:
            self.metrics["threats_blocked"]["prompt_injection"] += 1
            return InputGuardResult(
                is_safe=False,
                threat_type=ThreatType.PROMPT_INJECTION,
                reason=injection_result[1],
                sanitized_input="",
                confidence=injection_result[2]
            )

        # 3. Detectar tareas fuera de alcance
        scope_result = self._check_scope(user_input)
        if not scope_result[0]:
            self.metrics["threats_blocked"]["out_of_scope"] += 1
            return InputGuardResult(
                is_safe=False,
                threat_type=ThreatType.OUT_OF_SCOPE,
                reason=scope_result[1],
                sanitized_input=user_input,  # Mantener input para respuesta de reconducción
                confidence=scope_result[2]
            )

        # 4. Input seguro
        self.metrics["safe_interactions"] += 1
        logger.info("input_guard_passed")

        return InputGuardResult(
            is_safe=True,
            threat_type=ThreatType.NONE,
            reason=None,
            sanitized_input=user_input,
            confidence=1.0
        )

    def _detect_jailbreak(self, text: str) -> Tuple[bool, Optional[str], float]:
        """
        Detecta intentos de jailbreak.

        Returns:
            (is_safe, reason, confidence)
        """
        for pattern in JAILBREAK_PATTERNS:
            match = re.search(pattern, text)
            if match:
                logger.warning("jailbreak_detected", pattern=pattern[:50], matched_text=match.group(0))
                return (
                    False,
                    f"Intento de jailbreak detectado: '{match.group(0)}'",
                    0.95
                )

        return (True, None, 1.0)

    def _detect_prompt_injection(self, text: str) -> Tuple[bool, Optional[str], float]:
        """
        Detecta inyección de prompt directo.

        Returns:
            (is_safe, reason, confidence)
        """
        # Detectar delimitadores sospechosos
        suspicious_delimiters = ["<system>", "</system>", "[SYSTEM]", "{system:", "__INJECT__"]

        for delimiter in suspicious_delimiters:
            if delimiter.lower() in text.lower():
                logger.warning("prompt_injection_detected", delimiter=delimiter)
                return (
                    False,
                    f"Delimitador sospechoso detectado: '{delimiter}'",
                    0.90
                )

        # Detectar múltiples saltos de línea consecutivos (posible inyección)
        if "\n\n\n\n" in text or "\r\n\r\n\r\n" in text:
            logger.warning("suspicious_whitespace_detected")
            return (
                False,
                "Formato sospechoso con múltiples saltos de línea",
                0.75
            )

        return (True, None, 1.0)

    def _check_scope(self, text: str) -> Tuple[bool, Optional[str], float]:
        """
        Verifica si la entrada está dentro del alcance de Brasaland.

        Returns:
            (is_in_scope, reason, confidence)
        """
        text_lower = text.lower()

        # 1. Detectar tareas explícitamente fuera de alcance
        for pattern in OUT_OF_SCOPE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                logger.warning("out_of_scope_task_detected", pattern=pattern[:50], matched_text=match.group(0))
                return (
                    False,
                    f"Tarea fuera de alcance detectada: '{match.group(0)}'",
                    0.90
                )

        # 2. Permitir trivialidades/cortesía (cortas y simples)
        if len(text.strip()) < 30 and not any(kw in text_lower for kw in ["escribe", "hazme", "crea", "genera"]):
            # Pregunta corta (ej. "hola", "cómo estás", "qué hora es")
            logger.info("casual_interaction_allowed", text=text[:50])
            return (True, None, 1.0)

        # 3. Verificar si menciona dominio Brasaland
        has_domain_keyword = any(kw in text_lower for kw in BRASALAND_DOMAIN_KEYWORDS)

        if has_domain_keyword:
            logger.info("brasaland_domain_confirmed")
            return (True, None, 1.0)

        # 4. Si no menciona Brasaland ni es trivia, pero tampoco es tarea compleja → permitir con aviso
        if len(text.strip()) < 100:
            logger.info("generic_question_allowed", text=text[:50])
            return (True, None, 0.7)  # Confianza media (puede reconducirse en respuesta)

        # 5. Texto largo sin keywords de dominio → sospechoso
        logger.warning("no_domain_keywords_long_text", text_length=len(text))
        return (
            False,
            "La consulta parece no estar relacionada con Brasaland. Puedo ayudarte con información sobre restaurantes, locales, incidencias, inventarios o personal.",
            0.80
        )

    # ========================================
    # CONTEXT SANITIZER
    # ========================================

    def sanitize_external_content(self, content: str, source: str) -> str:
        """
        Sanitiza contenido externo (RAG, tools) para prevenir inyecciones indirectas.

        Args:
            content: Contenido recuperado de fuente externa
            source: Fuente del contenido ("rag", "tool:nombre")

        Returns:
            Contenido sanitizado envuelto en etiquetas de datos no confiables
        """
        logger.info("sanitizing_external_content", source=source, content_length=len(content))

        # Detectar patrones de inyección indirecta
        for pattern in INDIRECT_INJECTION_PATTERNS:
            if re.search(pattern, content):
                logger.warning("indirect_injection_detected_in_external_content", source=source, pattern=pattern[:50])
                # Escapar contenido sospechoso
                content = content.replace("<", "&lt;").replace(">", "&gt;")

        # Envolver en etiquetas de datos no confiables
        sanitized = f"<untrusted_data source=\"{source}\">\n{content}\n</untrusted_data>"

        return sanitized

    # ========================================
    # OUTPUT GUARD
    # ========================================

    def validate_output(self, model_output: str, allow_redirect: bool = False) -> OutputGuardResult:
        """
        Valida salida del modelo antes de retornarla al usuario.

        Args:
            model_output: Respuesta generada por el modelo
            allow_redirect: Si True, permite respuestas de reconducción para trivias

        Returns:
            OutputGuardResult con validación y output sanitizado
        """
        self.metrics["total_outputs_checked"] += 1

        logger.info("output_guard_checking", output_length=len(model_output))

        # 1. Detectar fuga de system prompt
        leak_result = self._detect_system_prompt_leak(model_output)
        if not leak_result[0]:
            self.metrics["threats_blocked"]["system_prompt_leak"] += 1
            return OutputGuardResult(
                is_safe=False,
                threat_type=ThreatType.SYSTEM_PROMPT_LEAK,
                reason=leak_result[1],
                sanitized_output="Lo siento, no puedo procesar esa solicitud en este momento.",
                confidence=leak_result[2]
            )

        # 2. Detectar PII en salida
        pii_result = self._detect_pii_leak(model_output)
        if not pii_result[0]:
            self.metrics["threats_blocked"]["pii_leak"] += 1
            return OutputGuardResult(
                is_safe=False,
                threat_type=ThreatType.PII_LEAK,
                reason=pii_result[1],
                sanitized_output=pii_result[3],  # Output con PII redactado
                confidence=pii_result[2]
            )

        # 3. Validar estructura básica (no vacío, no solo espacios)
        if not model_output.strip():
            self.metrics["threats_blocked"]["structural_invalid"] += 1
            logger.warning("empty_output_detected")
            return OutputGuardResult(
                is_safe=False,
                threat_type=ThreatType.STRUCTURAL_INVALID,
                reason="Respuesta vacía generada",
                sanitized_output="Lo siento, no pude generar una respuesta adecuada.",
                confidence=1.0
            )

        # 4. Output seguro
        logger.info("output_guard_passed")

        return OutputGuardResult(
            is_safe=True,
            threat_type=ThreatType.NONE,
            reason=None,
            sanitized_output=model_output,
            confidence=1.0
        )

    def _detect_system_prompt_leak(self, text: str) -> Tuple[bool, Optional[str], float]:
        """
        Detecta fuga de instrucciones internas.

        Returns:
            (is_safe, reason, confidence)
        """
        for pattern in SYSTEM_PROMPT_LEAK_PATTERNS:
            match = re.search(pattern, text)
            if match:
                logger.error("system_prompt_leak_detected", matched_text=match.group(0))
                return (
                    False,
                    f"Fuga de instrucciones internas detectada: '{match.group(0)}'",
                    0.95
                )

        return (True, None, 1.0)

    def _detect_pii_leak(self, text: str) -> Tuple[bool, Optional[str], float, str]:
        """
        Detecta PII en salida y redacta si es necesario.

        Returns:
            (is_safe, reason, confidence, sanitized_text)
        """
        sanitized_text = text
        pii_found = []

        for pattern in PII_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                pii_found.extend(matches)
                # Redactar PII
                sanitized_text = re.sub(pattern, "[REDACTED]", sanitized_text)

        if pii_found:
            logger.warning("pii_leak_detected_and_redacted", count=len(pii_found))
            return (
                False,
                f"PII detectada y redactada ({len(pii_found)} ocurrencias)",
                0.90,
                sanitized_text
            )

        return (True, None, 1.0, text)

    # ========================================
    # MÉTRICAS
    # ========================================

    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas de seguridad acumuladas"""
        return self.metrics.copy()

    def reset_metrics(self):
        """Reinicia métricas"""
        self.metrics = {
            "total_inputs_checked": 0,
            "total_outputs_checked": 0,
            "threats_blocked": {threat.value: 0 for threat in ThreatType if threat != ThreatType.NONE},
            "safe_interactions": 0
        }
        logger.info("security_metrics_reset")


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def sanitize_external_content(content: str, source: str) -> str:
    """
    Función auxiliar para sanitizar contenido externo.

    Wrapper de SecurityGuardrails.sanitize_external_content para uso simple.
    """
    guardrails = SecurityGuardrails()
    return guardrails.sanitize_external_content(content, source)
