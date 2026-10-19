from pydantic import BaseModel, EmailStr, HttpUrl, Field
from datetime import date
from typing import Literal, Optional


class CandidateBase(BaseModel):
    """Base schema for Candidate with common fields"""
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., min_length=7, max_length=20)
    position: str = Field(..., min_length=2, max_length=100)
    country: Literal['CO', 'US']
    location_preference: Optional[str] = Field(None, max_length=100)
    linkedin_url: Optional[HttpUrl] = None
    cv_url: Optional[HttpUrl] = None
    years_experience: int = Field(..., ge=0, le=50)


class CandidateCreate(CandidateBase):
    """Schema for creating a new candidate"""
    application_date: Optional[date] = None  # Will default to today if not provided


class CandidateUpdate(BaseModel):
    """Schema for updating candidate (all fields optional)"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=7, max_length=20)
    position: Optional[str] = Field(None, min_length=2, max_length=100)
    country: Optional[Literal['CO', 'US']] = None
    location_preference: Optional[str] = Field(None, max_length=100)
    linkedin_url: Optional[HttpUrl] = None
    cv_url: Optional[HttpUrl] = None
    years_experience: Optional[int] = Field(None, ge=0, le=50)


class CandidateStatusUpdate(BaseModel):
    """Schema for updating only the status"""
    status: Literal['activo', 'archivado', 'contratado', 'rechazado']


class CandidateStageUpdate(BaseModel):
    """Schema for updating only the stage"""
    stage: Literal['aplicacion', 'revision', 'entrevista', 'oferta', 'finalizado']


class CandidateResponse(CandidateBase):
    """Schema for candidate responses (includes DB fields)"""
    id: int
    status: Literal['activo', 'archivado', 'contratado', 'rechazado']
    stage: Literal['aplicacion', 'revision', 'entrevista', 'oferta', 'finalizado']
    application_date: date

    model_config = {"from_attributes": True}
