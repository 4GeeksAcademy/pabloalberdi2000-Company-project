"""
Agent Logger - Logging Estructurado para Sistemas Agénticos

Trazabilidad completa de decisiones, acciones y tool calls de agentes IA.

CRÍTICO:
- Log TODAS las llamadas a LLM (prompt, response, tokens, latencia)
- Log TODAS las decisiones de agentes (qué, por qué, confianza)
- Log TODAS las invocaciones de tools (params, result, success)
- Formato JSON estructurado (compatible con SIEM)

Compliance:
- Ley 1581 Colombia (trazabilidad obligatoria)
- NIST AI RMF (observabilidad y auditoría)

Uso:
    from services.logging.agent_logger import (
        log_llm_call,
        log_agent_decision,
        log_tool_invocation
    )

    log_llm_call(
        workflow="rfp_generation",
        node="evaluate_quality",
        prompt=prompt,
        response=response,
        model="gpt-4o-mini",
        tokens_used=response.usage.total_tokens,
        latency_ms=latency,
        user_id=user_id
    )
"""

import structlog
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

# ============================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================

logger = structlog.get_logger()

# Configurar structlog para output JSON
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# ============================================================
# LOGGING DE LLAMADAS A LLM
# ============================================================

def log_llm_call(
    workflow: str,
    node: str,
    prompt: str,
    response: str,
    model: str,
    tokens_used: int,
    latency_ms: float,
    user_id: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log completo de llamada a LLM.

    IMPORTANTE: Solo loguea preview de prompt/response (200 chars)
    para no saturar logs con contenido completo.

    Args:
        workflow: Nombre del workflow (ej. "rfp_generation")
        node: Nodo del grafo que invocó LLM (ej. "evaluate_quality")
        prompt: Prompt completo enviado al LLM
        response: Respuesta completa del LLM
        model: Modelo usado (ej. "gpt-4o-mini")
        tokens_used: Tokens totales consumidos
        latency_ms: Latencia en milisegundos
        user_id: ID del usuario que inició la acción
        metadata: Metadata adicional (opcional)
    """
    logger.info(
        "llm_call",
        workflow=workflow,
        node=node,
        model=model,
        # Solo preview para no saturar logs
        prompt_length=len(prompt),
        prompt_preview=prompt[:200] if prompt else "",
        response_length=len(response),
        response_preview=response[:200] if response else "",
        # Métricas
        tokens_used=tokens_used,
        latency_ms=round(latency_ms, 2),
        # Identificación
        user_id=user_id,
        timestamp=datetime.utcnow().isoformat(),
        # Metadata adicional
        **(metadata or {})
    )

# ============================================================
# LOGGING DE DECISIONES DE AGENTES
# ============================================================

def log_agent_decision(
    workflow: str,
    decision_node: str,
    decision: str,
    reasoning: str,
    confidence: float,
    state: Dict[str, Any],
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log de decisión de agente (aprobar/rechazar, continuar/detener, etc.).

    Args:
        workflow: Nombre del workflow
        decision_node: Nodo que tomó la decisión
        decision: Decisión tomada (ej. "approve", "reject")
        reasoning: Razonamiento del agente (por qué tomó esa decisión)
        confidence: Nivel de confianza (0-1)
        state: Estado del workflow (dict de LangGraph)
        user_id: ID del usuario (opcional)
        metadata: Metadata adicional (opcional)
    """
    logger.info(
        "agent_decision",
        workflow=workflow,
        node=decision_node,
        decision=decision,
        reasoning_preview=reasoning[:300] if reasoning else "",
        confidence=round(confidence, 3),
        # Estado del workflow (solo keys, no valores completos)
        state_keys=list(state.keys()),
        state_size=len(json.dumps(state)),
        # Identificación
        user_id=user_id,
        timestamp=datetime.utcnow().isoformat(),
        # Metadata adicional
        **(metadata or {})
    )

# ============================================================
# LOGGING DE TOOL INVOCATIONS
# ============================================================

def log_tool_invocation(
    tool_name: str,
    parameters: Dict[str, Any],
    result: Any,
    success: bool,
    error: Optional[str] = None,
    user_id: Optional[str] = None,
    latency_ms: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log de invocación de tool (MCP o LangChain).

    Args:
        tool_name: Nombre del tool (ej. "create_incident")
        parameters: Parámetros pasados al tool
        result: Resultado retornado (o None si falló)
        success: True si el tool se ejecutó exitosamente
        error: Mensaje de error (si falló)
        user_id: ID del usuario
        latency_ms: Latencia en milisegundos
        metadata: Metadata adicional (opcional)
    """
    log_level = "info" if success else "error"

    log_func = getattr(logger, log_level)
    log_func(
        "tool_invocation",
        tool_name=tool_name,
        parameters=parameters,
        # Resultado (truncado si es muy largo)
        result_preview=str(result)[:200] if success and result else None,
        result_type=type(result).__name__ if result else None,
        # Estado
        success=success,
        error=error,
        # Métricas
        latency_ms=round(latency_ms, 2) if latency_ms else None,
        # Identificación
        user_id=user_id,
        timestamp=datetime.utcnow().isoformat(),
        # Metadata adicional
        **(metadata or {})
    )

# ============================================================
# LOGGING DE WORKFLOW LIFECYCLE
# ============================================================

def log_workflow_start(
    workflow: str,
    input_data: Dict[str, Any],
    user_id: str,
    session_id: Optional[str] = None
):
    """
    Log de inicio de workflow.

    Args:
        workflow: Nombre del workflow
        input_data: Datos de entrada
        user_id: ID del usuario
        session_id: ID de sesión (opcional)
    """
    logger.info(
        "workflow_start",
        workflow=workflow,
        input_keys=list(input_data.keys()),
        input_size=len(json.dumps(input_data)),
        user_id=user_id,
        session_id=session_id,
        timestamp=datetime.utcnow().isoformat()
    )

def log_workflow_end(
    workflow: str,
    output_data: Dict[str, Any],
    success: bool,
    duration_ms: float,
    user_id: str,
    session_id: Optional[str] = None,
    error: Optional[str] = None
):
    """
    Log de finalización de workflow.

    Args:
        workflow: Nombre del workflow
        output_data: Datos de salida
        success: True si completó exitosamente
        duration_ms: Duración total en milisegundos
        user_id: ID del usuario
        session_id: ID de sesión (opcional)
        error: Mensaje de error (si falló)
    """
    log_level = "info" if success else "error"
    log_func = getattr(logger, log_level)

    log_func(
        "workflow_end",
        workflow=workflow,
        output_keys=list(output_data.keys()) if success else None,
        output_size=len(json.dumps(output_data)) if success else None,
        success=success,
        error=error,
        duration_ms=round(duration_ms, 2),
        user_id=user_id,
        session_id=session_id,
        timestamp=datetime.utcnow().isoformat()
    )

# ============================================================
# LOGGING DE HUMAN-IN-THE-LOOP
# ============================================================

def log_hitl_pause(
    workflow: str,
    interrupt_node: str,
    state: Dict[str, Any],
    user_id: str,
    session_id: str
):
    """
    Log cuando workflow pausa para HITL.

    Args:
        workflow: Nombre del workflow
        interrupt_node: Nodo donde pausó
        state: Estado actual del workflow
        user_id: ID del usuario
        session_id: ID de sesión
    """
    logger.info(
        "hitl_pause",
        workflow=workflow,
        interrupt_node=interrupt_node,
        state_keys=list(state.keys()),
        user_id=user_id,
        session_id=session_id,
        timestamp=datetime.utcnow().isoformat()
    )

def log_hitl_resume(
    workflow: str,
    interrupt_node: str,
    human_decision: str,
    human_notes: Optional[str],
    user_id: str,
    session_id: str
):
    """
    Log cuando humano reanuda workflow después de HITL.

    Args:
        workflow: Nombre del workflow
        interrupt_node: Nodo donde estaba pausado
        human_decision: Decisión del humano (approve/reject/modify)
        human_notes: Notas del humano (opcional)
        user_id: ID del usuario
        session_id: ID de sesión
    """
    logger.info(
        "hitl_resume",
        workflow=workflow,
        interrupt_node=interrupt_node,
        human_decision=human_decision,
        human_notes=human_notes[:200] if human_notes else None,
        user_id=user_id,
        session_id=session_id,
        timestamp=datetime.utcnow().isoformat()
    )

# ============================================================
# LOGGING DE SEGURIDAD
# ============================================================

def log_security_event(
    event_type: str,
    severity: str,
    description: str,
    affected_user: Optional[str] = None,
    source_ip: Optional[str] = None,
    evidence: Optional[Dict[str, Any]] = None
):
    """
    Log de evento de seguridad.

    Args:
        event_type: Tipo de evento (ej. "prompt_injection_detected")
        severity: Severidad (low, medium, high, critical)
        description: Descripción del evento
        affected_user: Usuario afectado (opcional)
        source_ip: IP de origen (opcional)
        evidence: Evidencia del evento (opcional)
    """
    log_level_map = {
        "low": "info",
        "medium": "warning",
        "high": "error",
        "critical": "critical"
    }

    log_level = log_level_map.get(severity, "warning")
    log_func = getattr(logger, log_level)

    log_func(
        "security_event",
        event_type=event_type,
        severity=severity,
        description=description,
        affected_user=affected_user,
        source_ip=source_ip,
        evidence=evidence,
        timestamp=datetime.utcnow().isoformat()
    )

# ============================================================
# LOGGING DE COSTOS
# ============================================================

def log_llm_cost(
    workflow: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    user_id: str
):
    """
    Log de costo de llamada a LLM.

    Args:
        workflow: Nombre del workflow
        model: Modelo usado
        input_tokens: Tokens de input
        output_tokens: Tokens de output
        cost_usd: Costo en USD
        user_id: ID del usuario
    """
    logger.info(
        "llm_cost",
        workflow=workflow,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_usd=round(cost_usd, 4),
        user_id=user_id,
        timestamp=datetime.utcnow().isoformat()
    )
