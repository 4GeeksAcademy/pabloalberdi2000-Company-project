"""
Seed Candidates - Populate ATS with realistic candidate data

Generates test candidates for Brasaland's ATS system across Colombia and Florida locations.

Usage:
  python services/api/scripts/seed_candidates.py [count]

  count: Number of candidates to create (default: 50)
"""
import sys
import os
from pathlib import Path
from datetime import date, timedelta
import random

# Add project path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, engine, Base
from app.models import Candidate, Note

# Create all tables if they don't exist
Base.metadata.create_all(bind=engine)

# Brasaland realistic data
NOMBRES_CO = [
    "Juan Carlos Gómez", "María Fernanda López", "Andrés Felipe Martínez",
    "Carolina Restrepo", "Santiago Vargas", "Valentina Ospina",
    "Diego Alejandro Ruiz", "Camila Andrea Torres", "Luis Miguel Castro",
    "Isabella Rodríguez", "Daniel Esteban Pérez", "Sofía Alejandra Sánchez",
    "Sebastián Giraldo", "Natalia Ramírez", "Carlos Eduardo Hernández",
    "Juliana Parra", "Miguel Ángel Betancur", "Ana María Cardona",
    "Felipe Moreno", "Laura Cristina Mejía"
]

NOMBRES_US = [
    "Michael Johnson", "Sarah Williams", "David Martinez",
    "Jennifer Garcia", "Robert Taylor", "Jessica Anderson",
    "James Rodriguez", "Emily Davis", "Christopher Lopez",
    "Amanda Wilson", "Daniel Thompson", "Melissa Brown",
    "Matthew Moore", "Ashley Martinez", "Joshua White",
    "Stephanie Lee", "Andrew Harris", "Nicole Clark",
    "Ryan Lewis", "Lauren Robinson"
]

POSITIONS = [
    "Cocinero", "Mesero", "Cajero", "Supervisor",
    "Gerente de Local", "Jefe de Cocina", "Bartender",
    "Auxiliar de Cocina", "Coordinador de Servicio"
]

LOCATIONS_CO = [
    "Medellín - Centro", "Medellín - El Poblado", "Medellín - Envigado",
    "Bogotá - Zona Rosa", "Bogotá - Usaquén", "Bogotá - Suba",
    "Cali - Norte", "Cali - Sur",
    "Cartagena - Centro", "Barranquilla - Norte"
]

LOCATIONS_US = [
    "Miami Beach", "Miami Downtown",
    "Orlando International Drive", "Tampa Centro"
]

STATUSES = ['activo', 'archivado', 'contratado', 'rechazado']
STAGES = ['aplicacion', 'revision', 'entrevista', 'oferta', 'finalizado']

def generate_email(name: str, country: str) -> str:
    """Generate realistic email from name"""
    parts = name.lower().split()
    if len(parts) >= 2:
        username = f"{parts[0]}.{parts[-1]}"
    else:
        username = parts[0]

    # Remove accents
    username = username.replace('á', 'a').replace('é', 'e').replace('í', 'i')
    username = username.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')

    domain = "gmail.com" if random.random() > 0.3 else "hotmail.com"
    return f"{username}{random.randint(1, 999)}@{domain}"

def generate_phone(country: str) -> str:
    """Generate realistic phone number"""
    if country == 'CO':
        return f"+57 {random.choice([300, 301, 310, 311, 312, 320, 321, 350])} {random.randint(100, 999)} {random.randint(1000, 9999)}"
    else:  # US
        return f"+1 ({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"

def seed_candidates(count: int = 50):
    """
    Create realistic candidate records for Brasaland ATS.

    Args:
        count: Number of candidates to create (default 50)
    """
    db = SessionLocal()

    try:
        # Check existing count
        existing = db.query(Candidate).count()
        if existing > 0:
            print(f"\n⚠️  Database already has {existing} candidates. Adding {count} more...")

        print(f"\n🌱 Creating {count} candidates for Brasaland ATS...\n")
        created = 0

        for i in range(count):
            # Distribute 70% Colombia, 30% USA
            country = 'CO' if random.random() < 0.7 else 'US'

            # Select name pool
            name = random.choice(NOMBRES_CO if country == 'CO' else NOMBRES_US)
            email = generate_email(name, country)

            # Check email uniqueness
            if db.query(Candidate).filter(Candidate.email == email).first():
                email = f"{email.split('@')[0]}{random.randint(1000, 9999)}@{email.split('@')[1]}"

            # Application date in last 90 days
            days_ago = random.randint(1, 90)
            app_date = date.today() - timedelta(days=days_ago)

            # Status/Stage based on application age
            if days_ago > 60:
                status = random.choice(['contratado', 'contratado', 'rechazado', 'archivado'])
                stage = 'finalizado'
            elif days_ago > 30:
                status = random.choice(['activo', 'activo', 'archivado'])
                stage = random.choice(['entrevista', 'oferta', 'finalizado'])
            else:
                status = 'activo'
                stage = random.choice(['aplicacion', 'revision', 'entrevista'])

            # Experience weighted toward entry-level for high-turnover positions
            position = random.choice(POSITIONS)
            if position in ['Mesero', 'Cajero', 'Auxiliar de Cocina']:
                years_exp = random.choices([0, 1, 2, 3, 4, 5], weights=[30, 25, 20, 15, 7, 3])[0]
            elif position in ['Supervisor', 'Jefe de Cocina']:
                years_exp = random.choices([2, 3, 4, 5, 6, 7, 8], weights=[5, 10, 20, 25, 20, 15, 5])[0]
            else:
                years_exp = random.randint(0, 10)

            candidate = Candidate(
                full_name=name,
                email=email,
                phone=generate_phone(country),
                position=position,
                country=country,
                location_preference=random.choice(LOCATIONS_CO if country == 'CO' else LOCATIONS_US),
                linkedin_url=f"https://linkedin.com/in/{name.lower().replace(' ', '-')}" if random.random() > 0.3 else None,
                cv_url=f"https://storage.brasaland.com/cv/{email.split('@')[0]}.pdf" if random.random() > 0.2 else None,
                years_experience=years_exp,
                status=status,
                stage=stage,
                application_date=app_date
            )

            db.add(candidate)
            db.commit()
            db.refresh(candidate)

            # Add 1-3 notes for candidates past 'aplicacion'
            if stage != 'aplicacion' and random.random() > 0.4:
                num_notes = random.randint(1, 3)
                authors = ["Ashley Turner", "Mariana Restrepo", "Felipe Guerrero", "Nicolás Park"]

                for n in range(num_notes):
                    note_date = app_date + timedelta(days=random.randint(1, days_ago))
                    note_texts = [
                        "Excelente presentación en entrevista inicial",
                        "Requiere seguimiento sobre disponibilidad de horario",
                        "Perfil alineado con necesidades del local",
                        "Solicitar referencias laborales",
                        "Pendiente validación de experiencia",
                        "Candidato muy motivado, recomendar para siguiente etapa"
                    ]

                    note = Note(
                        candidate_id=candidate.id,
                        content=random.choice(note_texts),
                        author=random.choice(authors),
                        created_at=note_date
                    )
                    db.add(note)

                db.commit()

            created += 1
            print(f"✅ [{created}/{count}] {name} - {position} ({country})")

        print("\n" + "="*60)
        print("📊 SEED COMPLETED")
        print("="*60)
        print(f"✅ Created: {created} candidates")
        print(f"📋 Total in DB: {db.query(Candidate).count()}")
        print("\nBreakdown:")
        print(f"  🇨🇴 Colombia: {db.query(Candidate).filter(Candidate.country == 'CO').count()}")
        print(f"  🇺🇸 USA: {db.query(Candidate).filter(Candidate.country == 'US').count()}")
        print(f"  ✅ Activos: {db.query(Candidate).filter(Candidate.status == 'activo').count()}")
        print(f"  ✅ Contratados: {db.query(Candidate).filter(Candidate.status == 'contratado').count()}")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Error during seed: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    count = 50
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid count. Using default: 50")

    seed_candidates(count)

if __name__ == "__main__":
    main()
