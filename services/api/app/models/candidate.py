from sqlalchemy import Column, Integer, String, Date, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import date
from ..database import Base


class Candidate(Base):
    """
    Candidate model for Brasaland ATS system.
    Stores information about job applicants across Colombia and Florida locations.
    """
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    position = Column(String(100), nullable=False, index=True)
    country = Column(SQLEnum('CO', 'US', name='country_enum'), nullable=False, index=True)
    location_preference = Column(String(100), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    cv_url = Column(String(255), nullable=True)
    years_experience = Column(Integer, nullable=False, default=0)
    status = Column(
        SQLEnum('activo', 'archivado', 'contratado', 'rechazado', name='status_enum'),
        nullable=False,
        default='activo',
        index=True
    )
    stage = Column(
        SQLEnum('aplicacion', 'revision', 'entrevista', 'oferta', 'finalizado', name='stage_enum'),
        nullable=False,
        default='aplicacion',
        index=True
    )
    application_date = Column(Date, nullable=False, default=date.today)

    # Relationship to notes
    notes = relationship("Note", back_populates="candidate", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Candidate(id={self.id}, name='{self.full_name}', position='{self.position}', status='{self.status}')>"
