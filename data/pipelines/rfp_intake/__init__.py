"""
RFP Intake Pipeline - Multi-Agent System

Sistema multi-agente para recepción, análisis y clasificación de RFPs.

ARQUITECTURA:
1. Ingest: Conversión PDF → Markdown + métricas legibilidad
2. Classifier: Validación de RFP legítima
3. Orchestrator: Descomposición en workstreams por departamento
4. Workers: Análisis paralelo por departamento
5. Synthesizer: Consolidación para Ventas

FLUJO:
Upload PDF → Ticket (analizando) → Pipeline asíncrono → analisis_completo | descartado
"""

from .ingest import convert_pdf_to_markdown, calculate_readability_metrics
from .graph import build_rfp_intake_graph, execute_rfp_pipeline

__all__ = [
    "convert_pdf_to_markdown",
    "calculate_readability_metrics",
    "build_rfp_intake_graph",
    "execute_rfp_pipeline"
]
