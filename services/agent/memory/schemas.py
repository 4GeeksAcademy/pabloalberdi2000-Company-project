"""
Schemas de Memoria - Structured Output para LangGraph

Define los tipos Pydantic para propuestas de memoria y respuestas estructuradas.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum
from datetime import datetime


class MemoryCategory(str, Enum):
    """
    Categorías de memoria según company-BRIEFING.md

    PERMITIDAS:
    - RESOLUTION: Soluciones a problemas específicos
    - USER_CORRECTION: Correcciones explícitas del usuario
    - WORKFLOW: Flujos de trabajo aprendidos
    - PREFERENCE: Preferencias del usuario

    PROHIBIDAS (no incluidas):
    - PII (datos personales)
    - CREDENTIALS (contraseñas, tokens)
    - CONFIDENTIAL (datos sensibles)
    """
    RESOLUTION = "resolution"          # Solución a incidente
    USER_CORRECTION = "user_correction"  # Corrección explícita
    WORKFLOW = "workflow"              # Flujo aprendido
    PREFERENCE = "preference"          # Preferencia del usuario
    FACT = "fact"                      # Hecho verificable


class ProposalStatus(str, Enum):
    """Estados de una propuesta de memoria"""
    PENDING = "pending"                # Esperando decisión del usuario
    APPROVED = "approved"              # Usuario aprobó explícitamente
    REJECTED = "rejected"              # Usuario rechazó explícitamente
    DISCARDED = "discarded"            # Descartada por silencio/ambigüedad


class MemoryProposalSchema(BaseModel):
    """
    Schema de propuesta de memoria (generado por LLM).

    Este schema se usa en Structured Output del modelo.
    """
    is_memorable: bool = Field(
        description="¿Hay un hecho nuevo o corrección relevante que amerite recordarse?"
    )
    content: Optional[str] = Field(
        None,
        description="Contenido concreto a memorizar (qué exactamente recordar)"
    )
    category: Optional[MemoryCategory] = Field(
        None,
        description="Categoría según company-BRIEFING.md"
    )
    reason: Optional[str] = Field(
        None,
        description="Justificación de por qué es relevante para el usuario"
    )

    # Validación de políticas negativas
    def validate_negative_policies(self) -> tuple[bool, Optional[str]]:
        """
        Valida que la propuesta no viole políticas negativas.

        Returns:
            (es_válida, razón_de_rechazo)
        """
        if not self.content:
            return True, None

        content_lower = self.content.lower()

        # Keywords prohibidas (PII, credentials, confidential)
        forbidden_keywords = [
            "contraseña", "password", "token", "api_key", "secret",
            "dni", "nif", "passport", "social security",
            "credit card", "tarjeta", "cuenta bancaria",
            "confidencial", "confidential", "privado", "private"
        ]

        for keyword in forbidden_keywords:
            if keyword in content_lower:
                return False, f"Contiene información prohibida: '{keyword}'"

        return True, None


class AgentStructuredResponse(BaseModel):
    """
    Respuesta estructurada del agente (con propuesta de memoria opcional).

    El LLM genera este schema en Structured Output:
    - response_text: Lo que ve el usuario
    - memory_proposal: Propuesta (solo si is_memorable=True)
    """
    response_text: str = Field(
        description="Respuesta visible para el usuario final"
    )
    memory_proposal: Optional[MemoryProposalSchema] = Field(
        None,
        description="Propuesta de memoria (solo si hay algo memorable)"
    )


class MemoryEntry(BaseModel):
    """
    Entrada de memoria persistida (después de aprobación).

    Se almacena en Qdrant collection `agent_memory`.
    """
    id: str = Field(description="UUID de la memoria")
    content: str = Field(description="Contenido de la memoria")
    category: MemoryCategory = Field(description="Categoría")
    context: Optional[str] = Field(None, description="Contexto adicional")
    created_at: datetime = Field(description="Timestamp de creación")
    approved_by: str = Field(description="Usuario que aprobó (user_id)")
    proposal_id: str = Field(description="ID de la propuesta original")
    metadata: dict = Field(default_factory=dict, description="Metadata adicional")


class ProposalAuditLog(BaseModel):
    """
    Registro de auditoría de propuestas (trazabilidad completa).

    Se persiste TODAS las propuestas (aprobadas, rechazadas, descartadas).
    """
    id: str = Field(description="UUID de la propuesta")
    proposal: MemoryProposalSchema = Field(description="Propuesta original")
    status: ProposalStatus = Field(description="Estado de la decisión")
    proposed_at: datetime = Field(description="Timestamp de propuesta")
    decided_at: Optional[datetime] = Field(None, description="Timestamp de decisión")
    user_response: Optional[str] = Field(None, description="Respuesta textual del usuario")
    decision_reason: Optional[str] = Field(None, description="Razón de la decisión")
    conversation_id: str = Field(description="ID de la conversación")
    agent_version: str = Field(description="Versión del agente")
