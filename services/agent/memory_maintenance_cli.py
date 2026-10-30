#!/usr/bin/env python3
"""
CLI de Mantenimiento de Memoria

Herramienta de línea de comandos para mantenimiento del sistema de memoria.

Comandos:
- stats: Mostrar estadísticas actuales
- consolidate: Consolidar memorias duplicadas
- expire: Eliminar memorias expiradas
- daily: Ejecutar mantenimiento diario completo
- health: Reporte de salud del sistema

Ejemplos:
    python memory_maintenance_cli.py stats
    python memory_maintenance_cli.py consolidate --dry-run
    python memory_maintenance_cli.py daily
"""

import sys
import argparse
import json
from pathlib import Path

# Agregar raíz al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.agent.memory import get_memory_manager
from services.agent.memory.maintenance import (
    get_memory_statistics,
    consolidate_duplicate_memories,
    expire_old_memories,
    run_daily_maintenance,
    get_memory_health_report
)


def cmd_stats(args):
    """Comando: stats - Mostrar estadísticas"""
    print("\n📊 Generando estadísticas...\n")

    memory_manager = get_memory_manager()
    stats = get_memory_statistics(memory_manager)

    if args.json:
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    else:
        print("=" * 70)
        print("📊 ESTADÍSTICAS DE MEMORIA")
        print("=" * 70)
        print(f"\n📝 MEMORIAS:")
        print(f"  Total: {stats['memories']['total']}")
        print(f"  Por categoría:")
        for category, count in stats['memories']['by_category'].items():
            print(f"    - {category}: {count}")
        print(f"  Edad promedio: {stats['memories']['avg_age_days']} días")
        print(f"  Más antigua: {stats['memories']['oldest_days']} días")
        print(f"  Más reciente: {stats['memories']['newest_days']} días")

        print(f"\n📋 PROPUESTAS:")
        print(f"  Total: {stats['proposals']['total']}")
        print(f"  Aprobadas: {stats['proposals']['approved']} ({stats['proposals']['approval_rate_pct']}%)")
        print(f"  Rechazadas: {stats['proposals']['rejected']} ({stats['proposals']['rejection_rate_pct']}%)")
        print(f"  Descartadas: {stats['proposals']['discarded']}")
        print(f"  Pendientes: {stats['proposals']['pending']}")

        print(f"\n💚 SALUD:")
        for key, value in stats['health'].items():
            status = "✅" if value else "⚠️"
            print(f"  {status} {key}: {value}")

        print("=" * 70 + "\n")


def cmd_consolidate(args):
    """Comando: consolidate - Consolidar duplicados"""
    dry_run_msg = " (DRY RUN - sin modificar)" if args.dry_run else ""
    print(f"\n🔄 Consolidando memorias duplicadas{dry_run_msg}...\n")

    memory_manager = get_memory_manager()
    result = consolidate_duplicate_memories(
        memory_manager=memory_manager,
        similarity_threshold=args.threshold,
        dry_run=args.dry_run
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("=" * 70)
        print("🔄 CONSOLIDACIÓN COMPLETADA")
        print("=" * 70)
        print(f"\n📊 Resultados:")
        print(f"  Duplicados encontrados: {result['duplicates_found']}")
        print(f"  Memorias consolidadas: {result['memories_consolidated']}")
        print(f"  Memorias mantenidas: {result['memories_kept']}")

        if result['by_category']:
            print(f"\n📁 Por categoría:")
            for category, data in result['by_category'].items():
                print(f"  {category}:")
                print(f"    - Duplicados: {data['duplicates_found']}")
                print(f"    - Consolidados: {data['consolidated']}")

        if args.dry_run:
            print(f"\n⚠️  DRY RUN: No se modificó nada")

        print("=" * 70 + "\n")


def cmd_expire(args):
    """Comando: expire - Eliminar memorias expiradas"""
    dry_run_msg = " (DRY RUN - sin modificar)" if args.dry_run else ""
    print(f"\n⏰ Eliminando memorias expiradas{dry_run_msg}...\n")

    memory_manager = get_memory_manager()
    result = expire_old_memories(
        memory_manager=memory_manager,
        dry_run=args.dry_run
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("=" * 70)
        print("⏰ EXPIRACIÓN COMPLETADA")
        print("=" * 70)
        print(f"\n📊 Resultados:")
        print(f"  Memorias expiradas: {result['expired_candidates']}")

        if result['by_category']:
            print(f"\n📁 Por categoría:")
            for category, count in result['by_category'].items():
                print(f"  {category}: {count} expiradas")

        if args.dry_run:
            print(f"\n⚠️  DRY RUN: No se eliminó nada")
        else:
            print(f"\n✅ Eliminadas: {result['total_expired']} memorias")

        print("=" * 70 + "\n")


def cmd_daily(args):
    """Comando: daily - Mantenimiento diario completo"""
    dry_run_msg = " (DRY RUN - sin modificar)" if args.dry_run else ""
    print(f"\n🔧 Ejecutando mantenimiento diario{dry_run_msg}...\n")

    result = run_daily_maintenance(dry_run=args.dry_run)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("=" * 70)
        print("🔧 MANTENIMIENTO DIARIO COMPLETADO")
        print("=" * 70)

        summary = result['summary']

        print(f"\n📊 Resumen:")
        print(f"  Memorias antes: {summary['memories_before']}")
        print(f"  Memorias después: {summary['memories_after']}")
        print(f"  Memorias eliminadas: {summary['memories_removed']}")
        print(f"  Salud mejorada: {'✅' if summary['health_improved'] else '⚠️'}")

        print(f"\n🔄 Consolidación:")
        cons = result['consolidation']
        print(f"  Duplicados: {cons['duplicates_found']}")
        print(f"  Consolidados: {cons['memories_consolidated']}")

        print(f"\n⏰ Expiración:")
        exp = result['expiration']
        print(f"  Expiradas: {exp['total_expired']}")

        if args.dry_run:
            print(f"\n⚠️  DRY RUN: No se modificó nada")

        print("=" * 70 + "\n")


def cmd_health(args):
    """Comando: health - Reporte de salud"""
    print("\n💚 Generando reporte de salud...\n")

    memory_manager = get_memory_manager()
    report = get_memory_health_report(memory_manager)

    print(report)


def main():
    parser = argparse.ArgumentParser(
        description="CLI de Mantenimiento de Memoria",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s stats                    # Mostrar estadísticas
  %(prog)s consolidate --dry-run    # Simular consolidación
  %(prog)s expire                   # Eliminar memorias expiradas
  %(prog)s daily --dry-run          # Simular mantenimiento diario
  %(prog)s health                   # Reporte de salud
"""
    )

    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')

    # Comando: stats
    parser_stats = subparsers.add_parser('stats', help='Mostrar estadísticas actuales')
    parser_stats.add_argument('--json', action='store_true', help='Salida en formato JSON')
    parser_stats.set_defaults(func=cmd_stats)

    # Comando: consolidate
    parser_consolidate = subparsers.add_parser('consolidate', help='Consolidar memorias duplicadas')
    parser_consolidate.add_argument('--threshold', type=float, default=0.95, help='Umbral de similitud (default: 0.95)')
    parser_consolidate.add_argument('--dry-run', action='store_true', help='Simular sin modificar')
    parser_consolidate.add_argument('--json', action='store_true', help='Salida en formato JSON')
    parser_consolidate.set_defaults(func=cmd_consolidate)

    # Comando: expire
    parser_expire = subparsers.add_parser('expire', help='Eliminar memorias expiradas')
    parser_expire.add_argument('--dry-run', action='store_true', help='Simular sin modificar')
    parser_expire.add_argument('--json', action='store_true', help='Salida en formato JSON')
    parser_expire.set_defaults(func=cmd_expire)

    # Comando: daily
    parser_daily = subparsers.add_parser('daily', help='Mantenimiento diario completo')
    parser_daily.add_argument('--dry-run', action='store_true', help='Simular sin modificar')
    parser_daily.add_argument('--json', action='store_true', help='Salida en formato JSON')
    parser_daily.set_defaults(func=cmd_daily)

    # Comando: health
    parser_health = subparsers.add_parser('health', help='Reporte de salud del sistema')
    parser_health.set_defaults(func=cmd_health)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n\n⚠️  Operación cancelada por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
