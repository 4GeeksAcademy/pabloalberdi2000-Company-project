"""
Connection Manager - SSE Pub/Sub

Gestiona conexiones SSE activas y difunde eventos a todos los clientes suscritos.

CRÍTICO:
- Un asyncio.Queue por cliente (conexión individual)
- Pub/Sub centralizado (un publish → N clientes)
- Escalable a Redis Pub/Sub para multi-worker

DOMINIO: Brasaland Digital (Cadena de Restaurantes)
- Incidencias postventa (14 locales: 10 CO + 4 US)
- Candidaturas ATS (RRHH)
- Alertas operacionales
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


# ============================================================
# EVENT TYPES - BRASALAND DOMAIN
# ============================================================

@dataclass
class IncidentCreatedEvent:
    """
    Evento de nueva incidencia postventa en Brasaland.

    Dominio: Sistema de Análisis de Incidencias
    Usuario: Operaciones + Dirección
    Locales: 14 restaurantes (10 CO + 4 US)
    """
    event_type: str  # "incident_created"
    incident_id: int
    local_name: str  # "Medellín Centro", "Miami Beach", "Bogotá Norte", etc.
    country: str  # "CO" | "US"
    category: str  # "calidad_comida", "servicio", "tiempo_espera", "higiene", "ambiente"
    severity: str  # "baja", "media", "alta", "critica"
    description: str
    customer_name: Optional[str]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario (sin event_type)"""
        data = asdict(self)
        data.pop("event_type")  # event_type va en el campo "event:" de SSE
        return data


@dataclass
class CandidateAppliedEvent:
    """
    Evento de nueva candidatura en ATS.

    Dominio: Applicant Tracking System (RRHH)
    Usuario: Ashley Turner (Personas y Cultura)
    Países: Colombia + USA (2 legislaciones laborales)
    """
    event_type: str  # "candidate_applied"
    candidate_id: int
    full_name: str
    email: str
    phone: str
    position: str  # "Cocinero", "Mesero", "Cajero", "Supervisor", "Gerente"
    local: str  # "Medellín Centro", "Miami Beach", etc.
    country: str  # "CO" | "US"
    status: str  # "nuevo", "en_revision", "entrevista", "contratado", "descartado"
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario (sin event_type)"""
        data = asdict(self)
        data.pop("event_type")
        return data


@dataclass
class OperationalAlertEvent:
    """
    Evento de alerta operacional en tiempo real.

    Dominio: Dashboard Operaciones (Felipe Guerrero)
    Ejemplos: Local sin ventas, pedido urgente, inventario crítico
    """
    event_type: str  # "operational_alert"
    alert_id: int
    alert_type: str  # "no_sales", "low_inventory", "urgent_order", "system_down"
    local_name: str
    country: str  # "CO" | "US"
    priority: str  # "info", "warning", "critical"
    message: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario (sin event_type)"""
        data = asdict(self)
        data.pop("event_type")
        return data


# Alias para compatibilidad con código existente (deprecado)
RFPTicketEvent = IncidentCreatedEvent  # DEPRECATED: Use IncidentCreatedEvent


# ============================================================
# CONNECTION MANAGER
# ============================================================

class ConnectionManager:
    """
    Gestor de conexiones SSE con Pub/Sub.

    Arquitectura:
    - Cada cliente tiene un asyncio.Queue dedicado
    - publish() envía evento a TODAS las colas activas
    - Escalable a Redis Pub/Sub para multi-worker
    """

    def __init__(self):
        # Mapeo de connection_id → asyncio.Queue
        self.connections: Dict[str, asyncio.Queue] = {}

        # Lock para thread-safety
        self._lock = asyncio.Lock()

    async def connect(self, connection_id: str) -> asyncio.Queue:
        """
        Registra nueva conexión SSE.

        Args:
            connection_id: ID único de conexión (user_id + timestamp)

        Returns:
            asyncio.Queue para enviar eventos a este cliente
        """
        async with self._lock:
            # Crear cola para este cliente
            queue = asyncio.Queue(maxsize=100)  # Buffer de 100 eventos
            self.connections[connection_id] = queue

            logger.info(f"[SSE] Nueva conexión: {connection_id} (Total: {len(self.connections)})")

            return queue

    async def disconnect(self, connection_id: str):
        """
        Desregistra conexión SSE.

        Args:
            connection_id: ID de conexión a eliminar
        """
        async with self._lock:
            if connection_id in self.connections:
                # Cerrar cola
                queue = self.connections.pop(connection_id)

                # Vaciar cola pendiente
                while not queue.empty():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break

                logger.info(f"[SSE] Desconexión: {connection_id} (Total: {len(self.connections)})")

    async def publish(self, event: RFPTicketEvent):
        """
        Publica evento a TODAS las conexiones activas.

        Args:
            event: Evento a difundir
        """
        async with self._lock:
            if not self.connections:
                logger.debug(f"[SSE] No hay conexiones activas para evento {event.event_type}")
                return

            # Difundir a todas las colas
            dead_connections = []

            for connection_id, queue in self.connections.items():
                try:
                    # put_nowait para evitar bloqueo si cola llena
                    queue.put_nowait(event)
                    logger.debug(f"[SSE] Evento enviado a {connection_id}")
                except asyncio.QueueFull:
                    logger.warning(f"[SSE] Cola llena para {connection_id}, marcando para desconexión")
                    dead_connections.append(connection_id)
                except Exception as e:
                    logger.error(f"[SSE] Error enviando a {connection_id}: {e}")
                    dead_connections.append(connection_id)

            # Limpiar conexiones muertas
            for connection_id in dead_connections:
                if connection_id in self.connections:
                    self.connections.pop(connection_id)

            logger.info(f"[SSE] Evento {event.event_type} publicado a {len(self.connections)} clientes")

    def get_active_connections_count(self) -> int:
        """Retorna número de conexiones activas"""
        return len(self.connections)


# ============================================================
# SINGLETON INSTANCE
# ============================================================

# Instancia global del connection manager
# En producción multi-worker: Reemplazar con Redis Pub/Sub
connection_manager = ConnectionManager()
