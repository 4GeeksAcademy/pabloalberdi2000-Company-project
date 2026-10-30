"""
Security Metrics - Observabilidad de Guardrails

Centraliza métricas de seguridad del agente para monitoreo y alertas.
"""

from typing import Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import structlog

logger = structlog.get_logger()

# Singleton global para métricas
_security_metrics: 'SecurityMetrics' = None


@dataclass
class SecurityMetricsSnapshot:
    """Snapshot de métricas de seguridad en un momento dado"""
    timestamp: str
    total_inputs_checked: int
    total_outputs_checked: int
    threats_blocked_by_type: Dict[str, int]
    safe_interactions: int
    threat_rate: float  # % de amenazas detectadas

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización"""
        return asdict(self)


class SecurityMetrics:
    """
    Gestor centralizado de métricas de seguridad.

    Acumula estadísticas de guardrails para reportes y alertas.
    """

    def __init__(self):
        """Inicializa métricas vacías"""
        self.start_time = datetime.utcnow()
        self.data = {
            "total_inputs_checked": 0,
            "total_outputs_checked": 0,
            "threats_blocked_by_type": {},
            "safe_interactions": 0,
            "session_start": self.start_time.isoformat()
        }

        logger.info("security_metrics_initialized", start_time=self.data["session_start"])

    def record_input_check(self, is_safe: bool, threat_type: str = None):
        """
        Registra validación de entrada.

        Args:
            is_safe: Si el input pasó la validación
            threat_type: Tipo de amenaza detectada (si aplica)
        """
        self.data["total_inputs_checked"] += 1

        if is_safe:
            self.data["safe_interactions"] += 1
        else:
            if threat_type not in self.data["threats_blocked_by_type"]:
                self.data["threats_blocked_by_type"][threat_type] = 0
            self.data["threats_blocked_by_type"][threat_type] += 1

        logger.info("input_check_recorded", is_safe=is_safe, threat_type=threat_type)

    def record_output_check(self, is_safe: bool, threat_type: str = None):
        """
        Registra validación de salida.

        Args:
            is_safe: Si el output pasó la validación
            threat_type: Tipo de amenaza detectada (si aplica)
        """
        self.data["total_outputs_checked"] += 1

        if not is_safe:
            if threat_type not in self.data["threats_blocked_by_type"]:
                self.data["threats_blocked_by_type"][threat_type] = 0
            self.data["threats_blocked_by_type"][threat_type] += 1

        logger.info("output_check_recorded", is_safe=is_safe, threat_type=threat_type)

    def get_snapshot(self) -> SecurityMetricsSnapshot:
        """
        Genera snapshot actual de métricas.

        Returns:
            SecurityMetricsSnapshot con datos actuales
        """
        total_checks = self.data["total_inputs_checked"] + self.data["total_outputs_checked"]
        total_threats = sum(self.data["threats_blocked_by_type"].values())

        threat_rate = (total_threats / total_checks * 100) if total_checks > 0 else 0.0

        return SecurityMetricsSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            total_inputs_checked=self.data["total_inputs_checked"],
            total_outputs_checked=self.data["total_outputs_checked"],
            threats_blocked_by_type=self.data["threats_blocked_by_type"].copy(),
            safe_interactions=self.data["safe_interactions"],
            threat_rate=round(threat_rate, 2)
        )

    def get_summary(self) -> Dict[str, Any]:
        """
        Retorna resumen legible de métricas.

        Returns:
            Dict con métricas y estadísticas calculadas
        """
        snapshot = self.get_snapshot()
        total_checks = snapshot.total_inputs_checked + snapshot.total_outputs_checked
        total_threats = sum(snapshot.threats_blocked_by_type.values())

        return {
            "session_start": self.data["session_start"],
            "session_duration_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "total_checks": total_checks,
            "inputs_checked": snapshot.total_inputs_checked,
            "outputs_checked": snapshot.total_outputs_checked,
            "safe_interactions": snapshot.safe_interactions,
            "threats_detected": total_threats,
            "threat_rate_percent": snapshot.threat_rate,
            "threats_by_type": snapshot.threats_blocked_by_type,
            "top_threat": max(
                snapshot.threats_blocked_by_type.items(),
                key=lambda x: x[1]
            )[0] if snapshot.threats_blocked_by_type else None
        }

    def reset(self):
        """Reinicia métricas"""
        self.start_time = datetime.utcnow()
        self.data = {
            "total_inputs_checked": 0,
            "total_outputs_checked": 0,
            "threats_blocked_by_type": {},
            "safe_interactions": 0,
            "session_start": self.start_time.isoformat()
        }
        logger.info("security_metrics_reset")


def get_security_metrics() -> SecurityMetrics:
    """
    Obtiene instancia singleton de métricas de seguridad.

    Returns:
        SecurityMetrics global
    """
    global _security_metrics

    if _security_metrics is None:
        _security_metrics = SecurityMetrics()

    return _security_metrics
