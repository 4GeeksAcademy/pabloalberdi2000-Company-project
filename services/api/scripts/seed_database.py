"""
Database Seeder

Script para poblar la base de datos con datos realistas para testing de performance.
Genera volumen representativo para identificar cuellos de botella.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import random
import uuid

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tinydb_database import incidents_table, users_table, profiles_table
from app.auth.password import hash_password

# Seed data realista
CATEGORIAS = [
    "calidad_comida",
    "servicio_cliente",
    "operaciones",
    "infraestructura",
    "pedidos_online",
    "facturacion"
]

ESTADOS = ["open", "in_progress", "resolved", "discarded"]

ORIGENES = ["customer", "branch", "internal"]

LOCALES = [
    "medellin_centro", "medellin_poblado", "medellin_envigado",
    "bogota_zona_rosa", "bogota_usaquen", "bogota_suba",
    "cali_norte", "cali_sur",
    "cartagena_centro", "barranquilla_norte",
    "miami_beach", "miami_downtown",
    "orlando_international", "tampa_centro"
]

TITLES = [
    "Problema con calidad de carne",
    "Demora en atención",
    "Falla en caja registradora",
    "Fuga de agua en baño",
    "Error en pedido online",
    "Factura incorrecta",
    "Quejas de cliente sobre servicio",
    "Ingredientes cerca de vencimiento",
    "Personal insuficiente en hora pico",
    "Sistema POS lento",
    "Cliente insatisfecho con platillo",
    "Problema con proveedor",
    "Nevera no enfría correctamente",
    "Retraso en entrega a domicilio"
]

DEPARTMENTS = [
    "Operaciones",
    "Personas y Cultura",
    "Finanzas",
    "Marketing",
    "IT",
    "Cocina",
    "Meseros",
    "Administración"
]

POSITIONS = [
    "Gerente General",
    "Supervisor",
    "Cocinero",
    "Mesero",
    "Cajero",
    "Jefe de Cocina",
    "Analista",
    "Coordinador"
]


def seed_users(count: int = 50):
    """
    Crear usuarios de prueba.

    Args:
        count: Número de usuarios a crear
    """
    print(f"\n📝 Creando {count} usuarios...")

    existing_count = len(users_table.all())
    if existing_count >= count:
        print(f"   ℹ️  Ya existen {existing_count} usuarios. Saltando seed.")
        return

    roles = ["admin", "manager", "user"]
    created = 0

    for i in range(count):
        email = f"user{i+1}@brasaland.com"

        # Verificar si ya existe
        existing = users_table.search(lambda x: x.get("email") == email)
        if existing:
            continue

        # Crear usuario
        user_doc = {
            "email": email,
            "hashed_password": hash_password(f"password{i+1}"),
            "is_active": random.choice([True, True, True, False]),  # 75% activos
            "role": random.choice(roles),
            "created_at": (datetime.utcnow() - timedelta(days=random.randint(1, 365))).isoformat()
        }

        user_id = users_table.insert(user_doc)

        # Crear perfil asociado
        profile_doc = {
            "user_id": user_id,
            "name": f"Usuario {i+1}",
            "phone": f"+57 300 {random.randint(100, 999)} {random.randint(1000, 9999)}",
            "address": f"Calle {random.randint(1, 100)} #{random.randint(1, 50)}-{random.randint(10, 99)}"
        }
        profiles_table.insert(profile_doc)

        created += 1

    print(f"   ✅ {created} usuarios creados")


def seed_incidents(count: int = 500):
    """
    Crear incidencias de prueba con datos realistas.

    Args:
        count: Número de incidencias a crear
    """
    print(f"\n📋 Creando {count} incidencias...")

    existing_count = len(incidents_table.all())
    if existing_count >= count:
        print(f"   ℹ️  Ya existen {existing_count} incidencias. Saltando seed.")
        return

    created = 0

    for i in range(count):
        # Fecha aleatoria en los últimos 6 meses
        days_ago = random.randint(1, 180)
        created_at = datetime.utcnow() - timedelta(days=days_ago)

        # Estado basado en antigüedad (más antiguas = más probabilidad de resueltas)
        if days_ago > 90:
            status = random.choice(["resolved", "resolved", "resolved", "discarded"])
        elif days_ago > 30:
            status = random.choice(["resolved", "in_progress", "open"])
        else:
            status = random.choice(["open", "open", "in_progress"])

        # Satisfacción solo para resueltos
        satisfaction = None
        if status == "resolved":
            satisfaction = random.randint(1, 5)

        incident_doc = {
            "id": str(uuid.uuid4()),
            "title": random.choice(TITLES),
            "description": f"Descripción detallada de la incidencia #{i+1}. " * random.randint(2, 5),
            "category": random.choice(CATEGORIAS),
            "status": status,
            "origin": random.choice(ORIGENES),
            "branch": random.choice(LOCALES),
            "created_at": created_at.isoformat(),
            "updated_at": (created_at + timedelta(days=random.randint(0, 7))).isoformat(),
            "satisfaction": satisfaction,
            "legacy_id": f"INC{str(i+1).zfill(4)}"
        }

        incidents_table.insert(incident_doc)
        created += 1

    print(f"   ✅ {created} incidencias creadas")


def print_stats():
    """Imprimir estadísticas de la base de datos"""
    print("\n" + "="*60)
    print("📊 ESTADÍSTICAS DE LA BASE DE DATOS")
    print("="*60)

    # Usuarios
    all_users = users_table.all()
    active_users = [u for u in all_users if u.get("is_active")]
    print(f"\n👥 Usuarios:")
    print(f"   Total: {len(all_users)}")
    print(f"   Activos: {len(active_users)}")
    print(f"   Inactivos: {len(all_users) - len(active_users)}")

    # Perfiles
    all_profiles = profiles_table.all()
    print(f"\n📇 Perfiles: {len(all_profiles)}")

    # Incidencias
    all_incidents = incidents_table.all()
    print(f"\n📋 Incidencias: {len(all_incidents)}")

    if all_incidents:
        by_status = {}
        by_category = {}
        by_origin = {}

        for inc in all_incidents:
            status = inc.get("status", "unknown")
            category = inc.get("category", "unknown")
            origin = inc.get("origin", "unknown")

            by_status[status] = by_status.get(status, 0) + 1
            by_category[category] = by_category.get(category, 0) + 1
            by_origin[origin] = by_origin.get(origin, 0) + 1

        print(f"\n   Por Estado:")
        for status, count in sorted(by_status.items()):
            print(f"      {status:15} {count:4} ({count/len(all_incidents)*100:.1f}%)")

        print(f"\n   Por Categoría:")
        for cat, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:3]:
            print(f"      {cat:20} {count:4}")

        print(f"\n   Por Origen:")
        for origin, count in sorted(by_origin.items()):
            print(f"      {origin:15} {count:4} ({count/len(all_incidents)*100:.1f}%)")

    print("\n" + "="*60)


def main():
    """Ejecutar seeding completo"""
    print("🌱 SEED DATABASE - Brasaland Digital")
    print("="*60)

    try:
        # Seed usuarios
        seed_users(count=50)

        # Seed incidencias (volumen alto para testing de performance)
        seed_incidents(count=500)

        # Estadísticas
        print_stats()

        print("\n✅ Seed completado exitosamente")
        print("\n💡 Tip: Ahora puedes ejecutar el servidor y observar los tiempos de respuesta:")
        print("   uvicorn app.main:app --reload")
        print("   curl http://localhost:8000/incidents")

        return 0

    except Exception as e:
        print(f"\n❌ Error durante seed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
