"""
Approval Handler - Procesa decisiones del usuario sobre propuestas de memoria

Clasifica respuestas del usuario como:
- APPROVED: "sí", "ok", "adelante", "guardar"
- REJECTED: "no", "rechazar", "no guardes"
- DISCARDED: Cambio de tema, ambigüedad
- EDITED: Usuario modifica el contenido

CRÍTICO:
- Aprobación explícita requerida (no por silencio)
- Cambio de tema → descarte automático
- Ambigüedad → descarte (no asumir aprobación)
"""

import sys
from pathlib import Path
from typing import Optional, Literal, Tuple, Dict, Any
from datetime import datetime
import re

import structlog

# Agregar raíz al path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.agent.memory.schemas import (
    MemoryProposalSchema,
    ProposalStatus,
    MemoryCategory
)
from services.agent.memory.memory_manager import (
    MemoryManager,
    create_memory_entry,
    create_proposal_audit_log
)

logger = structlog.get_logger()

# ============================================================
# TIPOS Y CONSTANTES
# ============================================================

DecisionType = Literal["approved", "rejected", "discarded", "edited", "unclear"]

# Keywords de aprobación
APPROVAL_KEYWORDS = [
    "sí", "si", "yes", "ok", "okay", "vale", "adelante", "guarda", "guardar",
    "guárdalo", "guardalo", "save", "correcto", "perfecto", "exacto"
]

# Keywords de rechazo
REJECTION_KEYWORDS = [
    "no", "nope", "rechazar", "rechaza", "no guardes", "no lo guardes",
    "descarta", "olvida", "olvidalo", "olvídalo", "cancel", "cancelar"
]

# Keywords de edición
EDIT_KEYWORDS = [
    "editar", "edit", "cambiar", "modificar", "mejor", "en realidad",
    "en lugar de", "debería ser", "corregir"
]


# ============================================================
# CLASIFICACIÓN DE DECISIONES
# ============================================================

def classify_user_decision(
    user_response: str,
    proposal_context: Dict[str, Any]
) -> Tuple[DecisionType, Optional[str]]:
    """
    Clasifica la respuesta del usuario frente a una propuesta de memoria.

    Args:
        user_response: Respuesta textual del usuario
        proposal_context: Contexto de la propuesta pendiente
            {
                "content": "...",
                "category": "...",
                "reason": "...",
                "id": "..."
            }

    Returns:
        (tipo_de_decisión, contenido_editado_si_aplica)

    Lógica de clasificación:
    1. Aprobación explícita: "sí", "ok", "adelante" → approved
    2. Rechazo explícito: "no", "rechazar" → rejected
    3. Edición: Usuario modifica contenido → edited (+ nuevo contenido)
    4. Cambio de tema: No menciona la propuesta → discarded
    5. Ambigüedad: No se puede determinar → discarded (por defecto)
    """
    response_lower = user_response.lower().strip()

    logger.info("classifying_user_decision",
                response_length=len(user_response),
                proposal_id=proposal_context.get("id"))

    # 1. Verificar aprobación explícita
    if any(kw in response_lower for kw in APPROVAL_KEYWORDS):
        # Si es muy corta y tiene keyword de aprobación → approved simple
        if len(user_response) < 50:
            logger.info("decision_classified", decision="approved", reason="approval_keyword")
            return "approved", None

    # 2. Verificar rechazo explícito
    if any(kw in response_lower for kw in REJECTION_KEYWORDS):
        logger.info("decision_classified", decision="rejected", reason="rejection_keyword")
        return "rejected", None

    # 3. Detectar intento de edición
    has_edit_keyword = any(kw in response_lower for kw in EDIT_KEYWORDS)

    if has_edit_keyword and len(user_response) > 20:
        # Usuario está editando el contenido
        # Extraer el nuevo contenido (heurística: después de keywords de edición)
        edited_content = extract_edited_content(user_response, proposal_context)

        if edited_content:
            logger.info("decision_classified",
                       decision="edited",
                       edited_length=len(edited_content))
            return "edited", edited_content

    # 4. Verificar si menciona el tema de la propuesta
    proposal_content = proposal_context.get("content", "")
    is_on_topic = is_response_on_topic(user_response, proposal_content)

    if not is_on_topic:
        # Usuario cambió de tema → descartar propuesta
        logger.info("decision_classified",
                   decision="discarded",
                   reason="topic_change")
        return "discarded", None

    # 5. Si menciona el tema pero no es clara la decisión
    # Verificar si tiene suficiente overlap con propuesta
    if is_on_topic and len(user_response) > 30:
        # Posible edición implícita
        # Si contiene información relacionada pero diferente
        edited_content = extract_edited_content(user_response, proposal_context)

        if edited_content and edited_content != proposal_content:
            logger.info("decision_classified",
                       decision="edited",
                       reason="implicit_edit")
            return "edited", edited_content

    # 6. Por defecto: No está claro → descartar
    logger.info("decision_classified",
               decision="discarded",
               reason="unclear_intent")
    return "discarded", None


def is_response_on_topic(user_response: str, proposal_content: str) -> bool:
    """
    Determina si la respuesta del usuario está relacionada con la propuesta.

    Args:
        user_response: Respuesta del usuario
        proposal_content: Contenido de la propuesta

    Returns:
        True si está relacionada, False si cambió de tema
    """
    response_lower = user_response.lower()

    # Extraer palabras clave de la propuesta (filtrar stopwords)
    stopwords = {"el", "la", "los", "las", "de", "del", "a", "en", "es", "un", "una"}
    proposal_words = [
        w.lower() for w in re.findall(r'\b\w+\b', proposal_content)
        if len(w) > 3 and w.lower() not in stopwords
    ]

    # Si al menos 2 palabras clave aparecen en la respuesta → on topic
    matches = sum(1 for word in proposal_words if word in response_lower)

    return matches >= 2


def extract_edited_content(user_response: str, proposal_context: Dict[str, Any]) -> Optional[str]:
    """
    Extrae el contenido editado de la respuesta del usuario.

    Args:
        user_response: Respuesta del usuario
        proposal_context: Contexto de la propuesta

    Returns:
        Contenido editado o None si no se puede extraer
    """
    response_clean = user_response.strip()

    # Patrones de edición comunes
    edit_patterns = [
        r"en realidad\s+(.+)",
        r"mejor\s+(.+)",
        r"debería ser\s+(.+)",
        r"cambiar a\s+(.+)",
        r"editar:\s+(.+)",
        r"corregir a\s+(.+)"
    ]

    for pattern in edit_patterns:
        match = re.search(pattern, response_clean, re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            if len(extracted) > 10:  # Contenido mínimo
                return extracted

    # Si no hay patrón específico pero es largo y está on-topic
    # Usar toda la respuesta como nuevo contenido
    if len(response_clean) > 30 and len(response_clean) < 200:
        # Remover keywords de edición
        for keyword in EDIT_KEYWORDS:
            response_clean = response_clean.replace(keyword, "").strip()

        if len(response_clean) > 10:
            return response_clean

    return None


# ============================================================
# PROCESAMIENTO DE APROBACIÓN
# ============================================================

def process_approval(
    proposal_id: str,
    user_response: str,
    user_id: str,
    memory_manager: MemoryManager,
    conversation_id: str
) -> Dict[str, Any]:
    """
    Procesa la aprobación/rechazo/descarte de una propuesta de memoria.

    Args:
        proposal_id: ID de la propuesta pendiente
        user_response: Respuesta textual del usuario
        user_id: ID del usuario que decide
        memory_manager: Gestor de memoria
        conversation_id: ID de la conversación

    Returns:
        Dict con resultado de la operación:
        {
            "status": "approved" | "rejected" | "discarded",
            "memory_id": "..." (solo si approved),
            "message": "Mensaje para mostrar al usuario",
            "proposal_id": "..."
        }
    """
    logger.info("processing_approval",
                proposal_id=proposal_id,
                user_id=user_id,
                conversation_id=conversation_id)

    # Obtener propuesta del audit log
    # (Simplificado: en producción, buscar en Qdrant por proposal_id)
    # Por ahora, asumimos que tenemos el contexto

    # Para esta implementación, necesitamos recuperar la propuesta
    # del audit log de Qdrant
    proposal_data = get_proposal_from_audit_log(proposal_id, memory_manager)

    if not proposal_data:
        logger.error("proposal_not_found", proposal_id=proposal_id)
        return {
            "status": "error",
            "message": f"⚠️  Propuesta {proposal_id[:8]}... no encontrada",
            "proposal_id": proposal_id
        }

    proposal_context = {
        "id": proposal_id,
        "content": proposal_data.get("proposal_content"),
        "category": proposal_data.get("proposal_category"),
        "reason": proposal_data.get("proposal_reason")
    }

    # Clasificar decisión del usuario
    decision, edited_content = classify_user_decision(user_response, proposal_context)

    # Procesar según decisión
    if decision == "approved" or decision == "edited":
        # Usuario aprobó o editó (aprobación implícita)
        content = edited_content if edited_content else proposal_context["content"]
        category = proposal_context["category"]

        # Crear memoria y persistir
        memory_entry = create_memory_entry(
            content=content,
            category=MemoryCategory(category),
            approved_by=user_id,
            proposal_id=proposal_id,
            context=f"Approved in conversation {conversation_id}"
        )

        memory_id = memory_manager.save_memory(memory_entry)

        # Actualizar audit log a APPROVED
        audit_log = create_proposal_audit_log(
            proposal=MemoryProposalSchema(
                is_memorable=True,
                content=content,
                category=MemoryCategory(category),
                reason=proposal_context["reason"]
            ),
            status=ProposalStatus.APPROVED,
            conversation_id=conversation_id,
            user_response=user_response,
            decision_reason="user_approved" if decision == "approved" else "user_edited_and_approved"
        )

        # Sobrescribir ID con el original
        audit_log.id = proposal_id
        memory_manager.log_proposal(audit_log)

        logger.info("proposal_approved",
                   proposal_id=proposal_id,
                   memory_id=memory_id,
                   was_edited=decision == "edited")

        message = "✅ Memoria guardada exitosamente"
        if decision == "edited":
            message += f"\n📝 Contenido actualizado: {content[:60]}..."

        return {
            "status": "approved",
            "memory_id": memory_id,
            "message": message,
            "proposal_id": proposal_id,
            "was_edited": decision == "edited"
        }

    elif decision == "rejected":
        # Usuario rechazó explícitamente
        audit_log = create_proposal_audit_log(
            proposal=MemoryProposalSchema(
                is_memorable=True,
                content=proposal_context["content"],
                category=MemoryCategory(proposal_context["category"]),
                reason=proposal_context["reason"]
            ),
            status=ProposalStatus.REJECTED,
            conversation_id=conversation_id,
            user_response=user_response,
            decision_reason="user_rejected"
        )

        audit_log.id = proposal_id
        memory_manager.log_proposal(audit_log)

        logger.info("proposal_rejected",
                   proposal_id=proposal_id,
                   user_id=user_id)

        return {
            "status": "rejected",
            "message": "❌ Propuesta rechazada. No se guardó nada.",
            "proposal_id": proposal_id
        }

    elif decision == "discarded":
        # Descartada por cambio de tema o ambigüedad
        audit_log = create_proposal_audit_log(
            proposal=MemoryProposalSchema(
                is_memorable=True,
                content=proposal_context["content"],
                category=MemoryCategory(proposal_context["category"]),
                reason=proposal_context["reason"]
            ),
            status=ProposalStatus.DISCARDED,
            conversation_id=conversation_id,
            user_response=user_response,
            decision_reason="topic_change_or_unclear"
        )

        audit_log.id = proposal_id
        memory_manager.log_proposal(audit_log)

        logger.info("proposal_discarded",
                   proposal_id=proposal_id,
                   reason="topic_change_or_unclear")

        return {
            "status": "discarded",
            "message": "⚠️  Propuesta descartada (cambio de tema o respuesta poco clara).",
            "proposal_id": proposal_id
        }

    else:
        # No se pudo determinar (unclear) - pedir clarificación
        logger.warning("decision_unclear",
                      proposal_id=proposal_id,
                      user_response=user_response[:50])

        return {
            "status": "pending",
            "message": "🤔 No entendí tu respuesta. ¿Quieres que guarde esta información?\n   Responde claramente: sí / no / editar",
            "proposal_id": proposal_id
        }


def get_proposal_from_audit_log(
    proposal_id: str,
    memory_manager: MemoryManager
) -> Optional[Dict[str, Any]]:
    """
    Recupera una propuesta del audit log de Qdrant.

    Args:
        proposal_id: ID de la propuesta
        memory_manager: Gestor de memoria

    Returns:
        Datos de la propuesta o None si no se encuentra
    """
    try:
        # Buscar en Qdrant por ID
        result = memory_manager.client.retrieve(
            collection_name="memory_proposals_audit",
            ids=[proposal_id]
        )

        if result and len(result) > 0:
            return result[0].payload

        return None

    except Exception as e:
        logger.error("error_retrieving_proposal",
                    proposal_id=proposal_id,
                    error=str(e))
        return None


def discard_pending_proposals(
    conversation_id: str,
    memory_manager: MemoryManager,
    reason: str = "conversation_ended"
) -> int:
    """
    Descarta todas las propuestas pendientes de una conversación.

    Útil cuando:
    - Usuario cambia de tema sin decidir
    - Conversación termina
    - Nueva conversación comienza

    Args:
        conversation_id: ID de la conversación
        memory_manager: Gestor de memoria
        reason: Razón del descarte

    Returns:
        Número de propuestas descartadas
    """
    pending_proposals = memory_manager.get_pending_proposals(conversation_id)

    discarded_count = 0

    for proposal_data in pending_proposals:
        proposal_id = proposal_data.get("id")

        # Actualizar a DISCARDED
        audit_log = create_proposal_audit_log(
            proposal=MemoryProposalSchema(
                is_memorable=True,
                content=proposal_data.get("proposal_content"),
                category=MemoryCategory(proposal_data.get("proposal_category")),
                reason=proposal_data.get("proposal_reason")
            ),
            status=ProposalStatus.DISCARDED,
            conversation_id=conversation_id,
            user_response=None,
            decision_reason=reason
        )

        audit_log.id = proposal_id
        memory_manager.log_proposal(audit_log)

        discarded_count += 1

    if discarded_count > 0:
        logger.info("pending_proposals_discarded",
                   conversation_id=conversation_id,
                   count=discarded_count,
                   reason=reason)

    return discarded_count


# ============================================================
# HELPERS PÚBLICOS
# ============================================================

def is_approval_response(text: str) -> bool:
    """
    Determina si el texto es una respuesta a una propuesta de memoria.

    Útil para detectar si el usuario está respondiendo a una propuesta
    en lugar de hacer una nueva pregunta.

    Args:
        text: Texto del usuario

    Returns:
        True si parece ser una respuesta de aprobación/rechazo
    """
    text_lower = text.lower().strip()

    # Respuestas muy cortas con keywords de decisión
    if len(text) < 100:
        all_keywords = APPROVAL_KEYWORDS + REJECTION_KEYWORDS + EDIT_KEYWORDS
        if any(kw in text_lower for kw in all_keywords):
            return True

    # Patrones de edición
    edit_patterns = ["en realidad", "mejor", "debería ser", "cambiar a", "editar"]
    if any(pattern in text_lower for pattern in edit_patterns):
        return True

    return False
