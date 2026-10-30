"""
Security Integration - Nodos de Seguridad para LangGraph

Contiene los nodos de seguridad adicionales para integrar en graph.py.
Este archivo complementa la integración del harness de seguridad.

INTEGRACIÓN:
1. Importar en graph.py
2. Agregar nodos security_output_guard_node
3. Modificar synthesis_node para usar secure_system_prompt
4. Modificar rag_retrieve_node para sanitizar contexto
"""

from typing import Dict, Any
from services.agent.security import (
    SecurityGuardrails,
    OutputGuardResult,
    sanitize_external_content,
    get_security_metrics
)
from services.agent.security.secure_prompts import get_secure_system_prompt
import structlog

logger = structlog.get_logger()


def security_output_guard_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nodo de seguridad: Valida salida antes de retornarla al usuario.

    Bloquea:
    - Fuga de system prompt
    - PII en salida
    - Respuestas malformadas

    Returns:
        State con answer sanitizado o mensaje de error genérico
    """
    print(f"\n[SECURITY_OUTPUT_GUARD] Validando salida...")

    if not state.get("answer"):
        print("[SECURITY_OUTPUT_GUARD] ⚠️  Sin respuesta para validar")
        return state

    guardrails = SecurityGuardrails()
    guard_result: OutputGuardResult = guardrails.validate_output(state["answer"])

    # Registrar en métricas
    security_metrics = get_security_metrics()
    security_metrics.record_output_check(
        is_safe=guard_result.is_safe,
        threat_type=guard_result.threat_type.value if guard_result.threat_type else None
    )

    if not guard_result.is_safe:
        # AMENAZA EN SALIDA - Sanitizar o reemplazar
        print(f"[SECURITY_OUTPUT_GUARD] ⚠️  Amenaza en salida: {guard_result.threat_type.value}")
        print(f"  Razón: {guard_result.reason}")

        return {
            **state,
            "answer": guard_result.sanitized_output,
            "metadata": {
                **state.get("metadata", {}),
                "output_guard": "threat_detected_and_sanitized",
                "threat_type": guard_result.threat_type.value,
                "threat_reason": guard_result.reason
            }
        }

    # OUTPUT SEGURO
    print(f"[SECURITY_OUTPUT_GUARD] ✅ Output seguro")

    return {
        **state,
        "metadata": {
            **state.get("metadata", {}),
            "output_guard": "passed"
        }
    }


def sanitize_rag_context(context_chunks: list) -> list:
    """
    Sanitiza chunks de RAG para prevenir inyecciones indirectas.

    Args:
        context_chunks: Lista de chunks recuperados de RAG

    Returns:
        Chunks con contenido sanitizado
    """
    sanitized_chunks = []

    for chunk in context_chunks:
        sanitized_chunk = chunk.copy()

        # Sanitizar texto del chunk
        if "text" in chunk:
            sanitized_chunk["text"] = sanitize_external_content(
                content=chunk["text"],
                source="rag"
            )

        sanitized_chunks.append(sanitized_chunk)

    return sanitized_chunks


def sanitize_tool_output(tool_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitiza salida de tool para prevenir inyecciones indirectas.

    Args:
        tool_data: Datos retornados por tool MCP

    Returns:
        tool_data con contenido sanitizado
    """
    sanitized_data = tool_data.copy()

    # Sanitizar campo 'data' si existe
    if "data" in tool_data and isinstance(tool_data["data"], dict):
        sanitized_content = {}
        for key, value in tool_data["data"].items():
            if isinstance(value, str):
                sanitized_content[key] = sanitize_external_content(
                    content=value,
                    source=f"tool:{tool_data.get('tool_name', 'unknown')}"
                )
            else:
                sanitized_content[key] = value

        sanitized_data["data"] = sanitized_content

    return sanitized_data
