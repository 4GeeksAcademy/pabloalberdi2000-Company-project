#!/usr/bin/env python3
"""
Seed Incidents - Import historical CSV data to TinyDB

Este script migra incidencias históricas desde CSV a la base de datos persistente.
Características:
- Validación con lógica existente de incident_analyzer.py
- Idempotencia: no duplica registros (verifica legacy_id)
- Transformación de datos CSV → API schema
- Reporte detallado de errores

Usage:
    python scripts/seed_incidents.py <csv_file_path>

Example:
    python scripts/seed_incidents.py scripts/test-incidents.csv
"""
import sys
import csv
import os
from datetime import datetime
from pathlib import Path
import uuid

# Agregar parent directory al path para importar desde app
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "api"))

from app.tinydb_database import incidents_table, get_incident_by_legacy_id

# Importar validaciones desde paquete compartido transversal
from brasaland_shared import validar_registro


# ============================================================
# ESTADO MAPPING: CSV → API
# ============================================================

ESTADO_MAP = {
    "abierto": "open",
    "en_proceso": "in_progress",
    "cerrado": "resolved",
    "descartado": "discarded"
}


# ============================================================
# TRANSFORMACIÓN CSV → INCIDENT
# ============================================================

def transform_csv_to_incident(csv_row: dict) -> dict:
    """
    Transformar fila de CSV a documento Incident.

    Mappings:
    - descripcion → title (truncado 255) + description
    - estado → status (con mapping a English)
    - local → branch
    - fecha → created_at / updated_at (ISO 8601)
    - id_incidencia → legacy_id (para idempotencia)
    - origin hardcoded como "customer" (asumimos datos históricos de clientes)

    Args:
        csv_row: Diccionario con datos del CSV

    Returns:
        Documento Incident listo para insertar en TinyDB
    """
    estado_csv = csv_row["estado"]
    status_api = ESTADO_MAP.get(estado_csv, "open")

    # Parsear fecha a ISO 8601
    fecha_str = csv_row["fecha"]
    try:
        fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
        timestamp = fecha_dt.isoformat()
    except ValueError:
        # Fallback: usar timestamp actual si fecha inválida
        timestamp = datetime.utcnow().isoformat()

    incident_doc = {
        "id": str(uuid.uuid4()),
        "title": csv_row["descripcion"][:255],  # Truncar a longitud de título
        "description": csv_row["descripcion"],
        "category": csv_row["categoria"],
        "status": status_api,
        "origin": "customer",  # ⚠️ Hardcoded: asumimos datos históricos de clientes
        "branch": csv_row["local"],
        "created_at": timestamp,
        "updated_at": timestamp,
        "legacy_id": csv_row["id_incidencia"],
    }

    # Agregar satisfacción si presente y status es resolved
    if status_api == "resolved" and csv_row.get("satisfaccion"):
        satisfaccion_str = csv_row.get("satisfaccion", "").strip()
        if satisfaccion_str:
            try:
                satisfaccion = int(satisfaccion_str)
                if 1 <= satisfaccion <= 5:
                    incident_doc["satisfaction"] = satisfaccion
            except ValueError:
                pass  # Ignorar satisfacción inválida

    return incident_doc


# ============================================================
# FUNCIÓN PRINCIPAL DE SEEDING
# ============================================================

def seed_from_csv(csv_path: str) -> dict:
    """
    Importar CSV a tabla de incidencias con idempotencia.

    Args:
        csv_path: Ruta al archivo CSV

    Returns:
        Diccionario con estadísticas de la importación
    """
    stats = {
        "total": 0,
        "valid": 0,
        "invalid": 0,
        "imported": 0,
        "skipped": 0,
        "errors": []
    }

    # Verificar que el archivo existe
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader, start=2):  # Línea 2 (header es línea 1)
            stats["total"] += 1

            # Validar con lógica existente de incident_analyzer
            es_valido, razon = validar_registro(row)

            if not es_valido:
                stats["invalid"] += 1
                stats["errors"].append({
                    "line": i,
                    "id": row.get("id_incidencia", "N/A"),
                    "reason": razon
                })
                continue

            stats["valid"] += 1

            # ✅ IDEMPOTENCIA: verificar si legacy_id ya existe
            legacy_id = row.get("id_incidencia")
            if get_incident_by_legacy_id(legacy_id):
                stats["skipped"] += 1
                print(f"⏭️  Skipped duplicate: {legacy_id}")
                continue

            # Transformar y insertar
            try:
                incident_doc = transform_csv_to_incident(row)
                incidents_table.insert(incident_doc)
                stats["imported"] += 1
                print(f"✅ Imported: {legacy_id} → {incident_doc['id']}")
            except Exception as e:
                stats["invalid"] += 1
                stats["errors"].append({
                    "line": i,
                    "id": legacy_id,
                    "reason": f"Insert error: {str(e)}"
                })
                print(f"❌ Error importing {legacy_id}: {str(e)}")

    return stats


# ============================================================
# REPORTE
# ============================================================

def print_report(stats: dict):
    """Imprimir reporte de seeding"""
    print("\n" + "="*60)
    print("📊 SEED REPORT")
    print("="*60)
    print(f"Total rows processed:    {stats['total']}")
    print(f"Valid rows:              {stats['valid']}")
    print(f"Invalid rows:            {stats['invalid']}")
    print(f"✅ Successfully imported: {stats['imported']}")
    print(f"⏭️  Skipped (duplicates):  {stats['skipped']}")
    print("="*60)

    if stats["errors"]:
        print(f"\n⚠️  {len(stats['errors'])} INVALID RECORDS:")
        for err in stats["errors"]:
            print(f"   Line {err['line']}: {err['id']} - {err['reason']}")
        print()


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    """Punto de entrada del script"""
    if len(sys.argv) != 2:
        print("Usage: python scripts/seed_incidents.py <csv_file_path>")
        print("Example: python scripts/seed_incidents.py scripts/test-incidents.csv")
        sys.exit(1)

    csv_path = sys.argv[1]

    print(f"🌱 Starting seed from: {csv_path}")
    print(f"📂 Database: incidents_db.json (TinyDB)")
    print()

    try:
        stats = seed_from_csv(csv_path)
        print_report(stats)

        if stats["imported"] > 0:
            print(f"✅ Seed completed successfully! {stats['imported']} records imported.")
        elif stats["skipped"] > 0:
            print("⚠️  No new records imported (all were duplicates)")
        else:
            print("⚠️  No new records imported")

        # Exit code: 0 si se importó algo, 1 si no
        sys.exit(0 if stats["imported"] > 0 else 1)

    except Exception as e:
        print(f"❌ Seed failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
