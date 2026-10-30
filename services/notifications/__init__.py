"""
Notifications Module

Sistema de notificaciones en tiempo real con Server-Sent Events (SSE).

DOMINIO: Brasaland Digital
- Incidencias postventa
- Candidaturas ATS
- Alertas operacionales

Exporta:
- connection_manager: Singleton del gestor de conexiones
- IncidentCreatedEvent: Evento de nueva incidencia
- CandidateAppliedEvent: Evento de nueva candidatura
- OperationalAlertEvent: Evento de alerta operacional
"""

from .manager import (
    connection_manager,
    ConnectionManager,
    IncidentCreatedEvent,
    CandidateAppliedEvent,
    OperationalAlertEvent,
    RFPTicketEvent  # DEPRECATED: Alias para compatibilidad
)

__all__ = [
    "connection_manager",
    "ConnectionManager",
    "IncidentCreatedEvent",
    "CandidateAppliedEvent",
    "OperationalAlertEvent",
    "RFPTicketEvent",  # DEPRECATED
]
