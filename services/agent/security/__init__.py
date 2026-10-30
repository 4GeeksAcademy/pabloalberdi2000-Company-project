"""
Security Harness - Guardrails y Blindaje del Agente

Módulo de seguridad multicapa para proteger el agente contra:
- Prompt injection (directo e indirecto)
- Jailbreaking y evasión de directivas
- Tareas fuera de alcance (personal, trivia ajena)
- Fuga de información confidencial
- Envenenamiento de memoria persistente

CRÍTICO:
- Guardrails DETERMINISTAS (no dependen de LLM)
- Validación bidireccional (input + output)
- Aislamiento de contenido externo (RAG, tools)
- Logs estructurados con métricas de seguridad
"""

from .guardrails import (
    SecurityGuardrails,
    InputGuardResult,
    OutputGuardResult,
    ThreatType,
    sanitize_external_content
)
from .metrics import SecurityMetrics, get_security_metrics

__all__ = [
    "SecurityGuardrails",
    "InputGuardResult",
    "OutputGuardResult",
    "ThreatType",
    "sanitize_external_content",
    "SecurityMetrics",
    "get_security_metrics"
]
