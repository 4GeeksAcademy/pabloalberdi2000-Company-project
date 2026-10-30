"""
Memory Maintenance - Consolidación, Expiración y Optimización

Funciones para mantenimiento automático del sistema de memoria:
- Consolidación de memorias duplicadas
- Expiración por TTL según categoría
- Resumen de memorias antiguas
- Limpieza de audit log antiguo
- Estadísticas y métricas

CRÍTICO:
- Ejecutar consolidación diariamente
- Respetar TTL por categoría
- No eliminar memorias recientes
- Mantener audit log completo
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter
import json

import structlog

# Agregar raíz al path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.agent.memory.memory_manager import MemoryManager, get_memory_manager
from services.agent.memory.schemas import MemoryCategory, ProposalStatus

logger = structlog.get_logger()

# ============================================================
# CONFIGURACIÓN DE TTL Y CONSOLIDACIÓN
# ============================================================

# TTL (Time To Live) por categoría de memoria (en días)
TTL_BY_CATEGORY = {
    MemoryCategory.RESOLUTION: 90,        # Soluciones vigentes 90 días
    MemoryCategory.USER_CORRECTION: 180,  # Correcciones 6 meses
    MemoryCategory.WORKFLOW: 365,         # Workflows 1 año
    MemoryCategory.PREFERENCE: None,      # Preferencias permanentes
    MemoryCategory.FACT: 180              # Hechos 6 meses (revisar)
}

# Threshold de similitud para considerar duplicado
SIMILARITY_THRESHOLD_DUPLICATE = 0.95   # Muy similares
SIMILARITY_THRESHOLD_RELATED = 0.85     # Relacionadas (para resumen)

# Límite de memorias por categoría (para evitar crecimiento infinito)
MAX_MEMORIES_PER_CATEGORY = 100

# Días para mantener audit log completo (después resumir/archivar)
AUDIT_LOG_RETENTION_DAYS = 365


# ============================================================
# CONSOLIDACIÓN DE MEMORIAS DUPLICADAS
# ============================================================

def consolidate_duplicate_memories(
    memory_manager: MemoryManager,
    similarity_threshold: float = SIMILARITY_THRESHOLD_DUPLICATE,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Consolida memorias duplicadas manteniendo la más reciente.

    Args:
        memory_manager: Gestor de memoria
        similarity_threshold: Umbral de similitud (default 0.95)
        dry_run: Si True, solo reporta sin eliminar

    Returns:
        Dict con estadísticas de consolidación:
        {
            "duplicates_found": 10,
            "memories_consolidated": 8,
            "memories_kept": 2,
            "by_category": {...}
        }
    """
    logger.info("consolidate_duplicate_memories_started",
                threshold=similarity_threshold,
                dry_run=dry_run)

    # Obtener todas las memorias
    all_memories_result = memory_manager.client.scroll(
        collection_name="agent_memory",
        limit=1000,  # Ajustar según volumen esperado
        with_payload=True,
        with_vectors=False
    )

    all_memories = all_memories_result[0] if all_memories_result else []

    if not all_memories:
        logger.info("no_memories_to_consolidate")
        return {
            "duplicates_found": 0,
            "memories_consolidated": 0,
            "memories_kept": 0,
            "by_category": {}
        }

    logger.info("memories_loaded", count=len(all_memories))

    # Agrupar por categoría para mejor análisis
    by_category = {}
    for memory_point in all_memories:
        category = memory_point.payload.get("category")
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(memory_point)

    # Consolidar por categoría
    total_duplicates = 0
    total_consolidated = 0
    consolidation_details = {}

    for category, memories in by_category.items():
        logger.info("consolidating_category", category=category, count=len(memories))

        checked_ids = set()
        duplicates_in_category = 0
        consolidated_in_category = 0

        for memory in memories:
            memory_id = memory.payload["id"]

            if memory_id in checked_ids:
                continue

            # Buscar similares
            similar = memory_manager.search_similar(
                content=memory.payload["content"],
                threshold=similarity_threshold
            )

            # Filtrar duplicados (excluyendo el mismo)
            duplicates = [m for m in similar if m["id"] != memory_id]

            if duplicates:
                # Mantener el más reciente (por created_at)
                all_copies = [memory.payload] + [
                    {"id": d["id"], "created_at": d["created_at"]}
                    for d in duplicates
                ]

                # Ordenar por fecha (más reciente primero)
                sorted_copies = sorted(
                    all_copies,
                    key=lambda x: x.get("created_at", ""),
                    reverse=True
                )

                to_keep = sorted_copies[0]["id"]
                to_delete = [c["id"] for c in sorted_copies[1:]]

                logger.info("duplicates_detected",
                           category=category,
                           to_keep=to_keep[:8],
                           to_delete_count=len(to_delete))

                duplicates_in_category += len(to_delete)

                # Eliminar duplicados (si no es dry_run)
                if not dry_run:
                    for dup_id in to_delete:
                        memory_manager.delete_memory(dup_id)
                        consolidated_in_category += 1
                        checked_ids.add(dup_id)

                checked_ids.add(to_keep)

        total_duplicates += duplicates_in_category
        total_consolidated += consolidated_in_category

        consolidation_details[category] = {
            "duplicates_found": duplicates_in_category,
            "consolidated": consolidated_in_category
        }

    result = {
        "duplicates_found": total_duplicates,
        "memories_consolidated": total_consolidated if not dry_run else 0,
        "memories_kept": len(all_memories) - total_consolidated,
        "by_category": consolidation_details,
        "dry_run": dry_run
    }

    logger.info("consolidation_completed", **result)

    return result


# ============================================================
# EXPIRACIÓN POR TTL
# ============================================================

def expire_old_memories(
    memory_manager: MemoryManager,
    ttl_config: Dict[MemoryCategory, Optional[int]] = TTL_BY_CATEGORY,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Elimina memorias expiradas según TTL por categoría.

    Args:
        memory_manager: Gestor de memoria
        ttl_config: Dict de TTL en días por categoría
        dry_run: Si True, solo reporta sin eliminar

    Returns:
        Dict con estadísticas de expiración
    """
    logger.info("expire_old_memories_started", dry_run=dry_run)

    now = datetime.utcnow()

    # Obtener todas las memorias
    all_memories_result = memory_manager.client.scroll(
        collection_name="agent_memory",
        limit=1000,
        with_payload=True,
        with_vectors=False
    )

    all_memories = all_memories_result[0] if all_memories_result else []

    expired_by_category = {}
    total_expired = 0

    for memory_point in all_memories:
        category_str = memory_point.payload.get("category")
        created_at_str = memory_point.payload.get("created_at")
        memory_id = memory_point.payload.get("id")

        try:
            category = MemoryCategory(category_str)
        except ValueError:
            logger.warning("invalid_category", category=category_str, memory_id=memory_id)
            continue

        # Verificar si tiene TTL configurado
        ttl_days = ttl_config.get(category)

        if ttl_days is None:
            # Sin TTL → permanente
            continue

        # Parsear fecha de creación
        try:
            created_at = datetime.fromisoformat(created_at_str)
        except (ValueError, TypeError):
            logger.warning("invalid_created_at", created_at=created_at_str, memory_id=memory_id)
            continue

        # Calcular edad
        age_days = (now - created_at).days

        # Verificar si expiró
        if age_days > ttl_days:
            logger.info("memory_expired",
                       memory_id=memory_id[:8],
                       category=category,
                       age_days=age_days,
                       ttl_days=ttl_days)

            if category_str not in expired_by_category:
                expired_by_category[category_str] = []

            expired_by_category[category_str].append({
                "id": memory_id,
                "content": memory_point.payload.get("content", "")[:50],
                "age_days": age_days
            })

            # Eliminar (si no es dry_run)
            if not dry_run:
                memory_manager.delete_memory(memory_id)

            total_expired += 1

    result = {
        "total_expired": total_expired if not dry_run else 0,
        "expired_candidates": total_expired,
        "by_category": {
            cat: len(mems) for cat, mems in expired_by_category.items()
        },
        "details": expired_by_category,
        "dry_run": dry_run
    }

    logger.info("expiration_completed", **result)

    return result


# ============================================================
# RESUMEN DE MEMORIAS RELACIONADAS
# ============================================================

def summarize_related_memories(
    memory_manager: MemoryManager,
    category: MemoryCategory,
    similarity_threshold: float = SIMILARITY_THRESHOLD_RELATED,
    min_memories: int = 3,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Resume múltiples memorias relacionadas en una sola.

    Útil para:
    - Comprimir información redundante
    - Mantener esencia sin perder detalles
    - Reducir número de memorias sin perder conocimiento

    Args:
        memory_manager: Gestor de memoria
        category: Categoría a resumir
        similarity_threshold: Umbral para considerar relacionadas
        min_memories: Mínimo de memorias para generar resumen
        dry_run: Si True, solo reporta sin resumir

    Returns:
        Dict con resúmenes generados
    """
    logger.info("summarize_related_memories_started",
                category=category,
                threshold=similarity_threshold,
                dry_run=dry_run)

    # Obtener memorias de la categoría
    all_memories_result = memory_manager.client.scroll(
        collection_name="agent_memory",
        scroll_filter={
            "must": [
                {
                    "key": "category",
                    "match": {"value": category}
                }
            ]
        },
        limit=MAX_MEMORIES_PER_CATEGORY,
        with_payload=True,
        with_vectors=False
    )

    memories = all_memories_result[0] if all_memories_result else []

    if len(memories) < min_memories:
        logger.info("insufficient_memories_for_summary",
                   count=len(memories),
                   min_required=min_memories)
        return {
            "summaries_created": 0,
            "memories_summarized": 0,
            "reason": "insufficient_memories"
        }

    # Agrupar memorias relacionadas
    memory_clusters = []
    processed_ids = set()

    for memory in memories:
        memory_id = memory.payload["id"]

        if memory_id in processed_ids:
            continue

        # Buscar memorias relacionadas
        related = memory_manager.search_similar(
            content=memory.payload["content"],
            threshold=similarity_threshold
        )

        if len(related) >= min_memories:
            cluster = [memory.payload] + related
            cluster_ids = {m["id"] if isinstance(m, dict) else m.payload["id"] for m in cluster}

            # Verificar que no se solape con clusters existentes
            if not cluster_ids & processed_ids:
                memory_clusters.append(cluster)
                processed_ids.update(cluster_ids)

    logger.info("memory_clusters_identified", count=len(memory_clusters))

    # Generar resúmenes (usando LLM)
    summaries_created = 0
    total_memories_summarized = 0

    for cluster in memory_clusters:
        if dry_run:
            summaries_created += 1
            total_memories_summarized += len(cluster)
        else:
            # TODO: Implementar generación de resumen con LLM
            # summary = generate_summary_with_llm(cluster)
            # memory_manager.save_memory(summary)
            # for mem in cluster: memory_manager.delete_memory(mem["id"])
            pass

    result = {
        "summaries_created": summaries_created if not dry_run else len(memory_clusters),
        "memories_summarized": total_memories_summarized if not dry_run else sum(len(c) for c in memory_clusters),
        "clusters_identified": len(memory_clusters),
        "dry_run": dry_run
    }

    logger.info("summarization_completed", **result)

    return result


# ============================================================
# ESTADÍSTICAS Y MÉTRICAS
# ============================================================

def get_memory_statistics(
    memory_manager: MemoryManager
) -> Dict[str, Any]:
    """
    Genera estadísticas completas del sistema de memoria.

    Returns:
        Dict con métricas detalladas:
        - Total de memorias
        - Por categoría
        - Edad promedio
        - Tasa de crecimiento
        - Propuestas (audit log stats)
    """
    logger.info("generating_memory_statistics")

    # Memorias
    all_memories_result = memory_manager.client.scroll(
        collection_name="agent_memory",
        limit=1000,
        with_payload=True,
        with_vectors=False
    )

    memories = all_memories_result[0] if all_memories_result else []

    # Propuestas (audit log)
    audit_log_result = memory_manager.client.scroll(
        collection_name="memory_proposals_audit",
        limit=1000,
        with_payload=True,
        with_vectors=False
    )

    proposals = audit_log_result[0] if audit_log_result else []

    # Análisis de memorias
    by_category = Counter()
    ages = []
    now = datetime.utcnow()

    for memory in memories:
        category = memory.payload.get("category")
        by_category[category] += 1

        created_at_str = memory.payload.get("created_at")
        try:
            created_at = datetime.fromisoformat(created_at_str)
            age_days = (now - created_at).days
            ages.append(age_days)
        except (ValueError, TypeError):
            pass

    avg_age_days = sum(ages) / len(ages) if ages else 0

    # Análisis de propuestas
    proposal_statuses = Counter()
    for proposal in proposals:
        status = proposal.payload.get("status")
        proposal_statuses[status] += 1

    total_proposals = len(proposals)
    approved = proposal_statuses.get("approved", 0)
    rejected = proposal_statuses.get("rejected", 0)
    discarded = proposal_statuses.get("discarded", 0)
    pending = proposal_statuses.get("pending", 0)

    approval_rate = (approved / total_proposals * 100) if total_proposals > 0 else 0
    rejection_rate = (rejected / total_proposals * 100) if total_proposals > 0 else 0

    stats = {
        "memories": {
            "total": len(memories),
            "by_category": dict(by_category),
            "avg_age_days": round(avg_age_days, 1),
            "oldest_days": max(ages) if ages else 0,
            "newest_days": min(ages) if ages else 0
        },
        "proposals": {
            "total": total_proposals,
            "approved": approved,
            "rejected": rejected,
            "discarded": discarded,
            "pending": pending,
            "approval_rate_pct": round(approval_rate, 1),
            "rejection_rate_pct": round(rejection_rate, 1)
        },
        "health": {
            "needs_consolidation": len(memories) > MAX_MEMORIES_PER_CATEGORY * len(MemoryCategory),
            "has_pending_proposals": pending > 0,
            "avg_age_healthy": avg_age_days < 180  # Menos de 6 meses promedio
        }
    }

    logger.info("statistics_generated", **stats)

    return stats


# ============================================================
# MANTENIMIENTO COMPLETO (Daily Job)
# ============================================================

def run_daily_maintenance(
    memory_manager: Optional[MemoryManager] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Ejecuta mantenimiento completo diario del sistema de memoria.

    Tareas:
    1. Consolidación de duplicados
    2. Expiración de memorias antiguas
    3. Estadísticas

    Args:
        memory_manager: Gestor de memoria (si None, usa singleton)
        dry_run: Si True, solo reporta sin modificar

    Returns:
        Dict con resultados de todas las tareas
    """
    if memory_manager is None:
        memory_manager = get_memory_manager()

    logger.info("daily_maintenance_started", dry_run=dry_run)

    # 1. Estadísticas pre-mantenimiento
    stats_before = get_memory_statistics(memory_manager)

    # 2. Consolidación
    consolidation_result = consolidate_duplicate_memories(
        memory_manager=memory_manager,
        dry_run=dry_run
    )

    # 3. Expiración
    expiration_result = expire_old_memories(
        memory_manager=memory_manager,
        dry_run=dry_run
    )

    # 4. Estadísticas post-mantenimiento
    stats_after = get_memory_statistics(memory_manager)

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "dry_run": dry_run,
        "stats_before": stats_before,
        "consolidation": consolidation_result,
        "expiration": expiration_result,
        "stats_after": stats_after,
        "summary": {
            "memories_before": stats_before["memories"]["total"],
            "memories_after": stats_after["memories"]["total"],
            "memories_removed": (
                consolidation_result["memories_consolidated"] +
                expiration_result["total_expired"]
            ),
            "health_improved": (
                stats_after["health"]["avg_age_healthy"] >=
                stats_before["health"]["avg_age_healthy"]
            )
        }
    }

    logger.info("daily_maintenance_completed", **result["summary"])

    return result


# ============================================================
# HELPERS PÚBLICOS
# ============================================================

def get_memory_health_report(
    memory_manager: Optional[MemoryManager] = None
) -> str:
    """
    Genera reporte de salud del sistema de memoria (formato texto).

    Returns:
        String con reporte legible
    """
    if memory_manager is None:
        memory_manager = get_memory_manager()

    stats = get_memory_statistics(memory_manager)

    report_lines = [
        "=" * 70,
        "📊 REPORTE DE SALUD - Sistema de Memoria",
        "=" * 70,
        "",
        "MEMORIAS:",
        f"  Total: {stats['memories']['total']}",
        f"  Por categoría:",
    ]

    for category, count in stats['memories']['by_category'].items():
        report_lines.append(f"    - {category}: {count}")

    report_lines.extend([
        f"  Edad promedio: {stats['memories']['avg_age_days']} días",
        "",
        "PROPUESTAS:",
        f"  Total: {stats['proposals']['total']}",
        f"  Aprobadas: {stats['proposals']['approved']} ({stats['proposals']['approval_rate_pct']}%)",
        f"  Rechazadas: {stats['proposals']['rejected']} ({stats['proposals']['rejection_rate_pct']}%)",
        f"  Descartadas: {stats['proposals']['discarded']}",
        f"  Pendientes: {stats['proposals']['pending']}",
        "",
        "SALUD DEL SISTEMA:",
    ])

    for key, value in stats['health'].items():
        status = "✅" if value else "⚠️"
        report_lines.append(f"  {status} {key}: {value}")

    report_lines.append("=" * 70)

    return "\n".join(report_lines)
