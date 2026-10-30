"""
Test Script para Business Performance Pipeline

Este script verifica que el pipeline puede ejecutarse correctamente
con datos de prueba.

Uso:
    python data/pipelines/business-performance/test_pipeline.py
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Agregar raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from data.pipelines.business_performance.pipeline import (
    business_performance_etl_flow,
    init_audit_table,
    init_kpis_table,
    get_database_engine
)

def test_tables_initialization():
    """Test: Inicialización de tablas"""
    print("\n" + "=" * 60)
    print("TEST 1: Inicialización de Tablas")
    print("=" * 60)

    try:
        engine = get_database_engine()

        print("📝 Creando tabla de auditoría...")
        init_audit_table(engine)

        print("📊 Creando tabla de KPIs...")
        init_kpis_table(engine)

        print("✅ Tablas inicializadas correctamente")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_pipeline_execution():
    """Test: Ejecución del pipeline con ventana pequeña"""
    print("\n" + "=" * 60)
    print("TEST 2: Ejecución del Pipeline")
    print("=" * 60)

    # Ventana pequeña: ayer
    now = datetime.now(timezone.utc)
    end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=1)

    print(f"📅 Rango: {start_date.date()} → {end_date.date()}")

    try:
        result = business_performance_etl_flow(
            start_date=start_date,
            end_date=end_date,
            triggered_by="test"
        )

        print("\n✅ Pipeline ejecutado exitosamente")
        print(f"🆔 Run ID: {result['run_id']}")
        print(f"📊 Eventos procesados: {result['records_read']}")
        print(f"📈 KPIs generados: {result['records_processed']}")
        print(f"💾 Registros insertados: {result['records_inserted']}")

        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def main():
    """Ejecuta todos los tests"""
    print("\n" + "=" * 60)
    print("🧪 BRASALAND BUSINESS PERFORMANCE PIPELINE - TEST SUITE")
    print("=" * 60)

    results = []

    # Test 1: Inicialización de tablas
    results.append(("Inicialización de Tablas", test_tables_initialization()))

    # Test 2: Ejecución del pipeline
    results.append(("Ejecución del Pipeline", test_pipeline_execution()))

    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE TESTS")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print("\n" + "=" * 60)
    print(f"Resultados: {total_passed}/{total_tests} tests pasaron")
    print("=" * 60)

    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())
