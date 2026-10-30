"""
Business Performance Pipeline - Brasaland Digital

Pipeline ETL que transforma eventos de telemetría técnica en métricas de negocio
para el dashboard ejecutivo de Brasaland.

Arquitectura:
- Extracción: telemetry_events (PostgreSQL/Supabase)
- Transformación: Pandas (agregaciones vectorizadas)
- Carga: reporting.business_kpis (UPSERT idempotente)

Stakeholders:
- CEO Mariana Restrepo
- Gerentes de área (Operaciones, Marketing, RRHH, Tecnología)

Cadencia:
- Daily ETL: 3:00 AM UTC
- Weekly Briefing: Lunes 6:00 AM UTC
"""

__version__ = "1.0.0"
__author__ = "Brasaland Digital - Data Team"
