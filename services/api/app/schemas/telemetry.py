"""
Telemetry Schemas - Event Envelope Standard

Basado en la especificación aprobada en TELEMETRY_PLAN.md y event-schemas.json.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any, Literal
from datetime import datetime
import uuid


class TelemetryEvent(BaseModel):
    """
    Event Envelope estándar para todos los eventos de telemetría.

    Estructura de 8 campos obligatorios según especificación:
    - eventId: UUID v4 único por evento
    - timestamp: ISO 8601 UTC
    - sessionId: ID de sesión del usuario (nullable para backend events)
    - userId: UUID del usuario autenticado (nullable para flujos anónimos)
    - event_type: Taxonomía entidad_acción (snake_case)
    - schemaVersion: Semver (1.0.0)
    - requestId: UUID para correlación distribuida
    - properties: Payload específico del evento (allowlist estricto en producción)
    """
    eventId: str = Field(..., description="UUID v4 único del evento")
    timestamp: str = Field(..., description="Marca temporal ISO 8601 UTC")
    sessionId: Optional[str] = Field(None, description="ID de sesión (nullable)")
    userId: Optional[str] = Field(None, description="UUID del usuario autenticado (nullable)")
    event_type: str = Field(..., description="Tipo de evento (entidad_acción en snake_case)")
    schemaVersion: str = Field(..., description="Versión semántica del schema")
    requestId: str = Field(..., description="UUID v4 para correlación")
    properties: dict[str, Any] = Field(..., description="Payload específico del evento")

    @field_validator('eventId', 'requestId')
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Valida formato UUID v4"""
        try:
            uuid.UUID(v, version=4)
        except ValueError:
            raise ValueError(f'Invalid UUID v4 format: {v}')
        return v

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Valida formato ISO 8601"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f'Invalid ISO 8601 timestamp: {v}')
        return v

    @field_validator('event_type')
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Valida naming convention entidad_acción (snake_case)"""
        if not v or not v.islower() or not all(c.isalnum() or c == '_' for c in v):
            raise ValueError(f'event_type must be snake_case (entidad_acción): {v}')
        return v

    @field_validator('schemaVersion')
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Valida formato semver (MAJOR.MINOR.PATCH)"""
        parts = v.split('.')
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError(f'schemaVersion must be semver (e.g., 1.0.0): {v}')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "eventId": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
                    "timestamp": "2026-10-30T14:23:45.123Z",
                    "sessionId": "sess_abc123xyz",
                    "userId": "550e8400-e29b-41d4-a716-446655440000",
                    "event_type": "login_attempt_failed",
                    "schemaVersion": "1.0.0",
                    "requestId": "req_xyz789abc",
                    "properties": {
                        "email_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
                        "failure_reason": "invalid_credentials",
                        "ip_address_masked": "192.168.1.0"
                    }
                }
            ]
        }
    }


class TelemetryBatchRequest(BaseModel):
    """
    Contenedor para envío de eventos en lote desde frontend.

    El frontend acumula eventos en memoria y los envía en batches
    para reducir overhead de red y mejorar performance.
    """
    events: list[TelemetryEvent] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Lote de eventos (máximo 100 por request)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "events": [
                        {
                            "eventId": "evt_001",
                            "timestamp": "2026-10-30T14:23:45.123Z",
                            "sessionId": "sess_abc123",
                            "userId": "user_123",
                            "event_type": "page_view",
                            "schemaVersion": "1.0.0",
                            "requestId": "req_xyz789",
                            "properties": {
                                "page_name": "inventory_ingredients",
                                "referrer": "https://backoffice.brasaland.com/dashboard"
                            }
                        }
                    ]
                }
            ]
        }
    }


class TelemetryBatchResponse(BaseModel):
    """
    Respuesta del endpoint de ingestion stub.

    En MVP retorna solo la cantidad de eventos recibidos.
    En producción incluirá detalles de validación y procesamiento.
    """
    received: int = Field(..., description="Cantidad de eventos procesados en el lote")
    status: Literal["success"] = Field(default="success", description="Estado del procesamiento")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "received": 5,
                    "status": "success"
                }
            ]
        }
    }
