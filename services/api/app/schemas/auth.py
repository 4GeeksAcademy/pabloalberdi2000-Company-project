"""
Authentication Schemas

Schemas Pydantic para User, Profile, Token y autenticación.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional
from datetime import datetime


# ============================================================
# User Schemas
# ============================================================

class UserBase(BaseModel):
    """Schema base para User con campos comunes"""
    email: EmailStr
    is_active: bool = True
    role: Literal["admin", "manager", "user"] = "user"


class UserCreate(BaseModel):
    """
    Schema para crear nuevo usuario.
    Incluye password + campos opcionales de perfil inicial.
    """
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100, description="Mínimo 8 caracteres")
    role: Literal["admin", "manager", "user"] = "user"

    # Campos opcionales de perfil inicial (crea Profile vinculado)
    name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)


class UserUpdate(BaseModel):
    """Schema para actualizar usuario (todos campos opcionales)"""
    email: Optional[EmailStr] = None
    role: Optional[Literal["admin", "manager", "user"]] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema de respuesta con ID y timestamp"""
    id: int
    created_at: str  # ISO format datetime string


# ============================================================
# Profile Schemas
# ============================================================

class ProfileBase(BaseModel):
    """Schema base para Profile"""
    name: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)


class ProfileUpdate(BaseModel):
    """Schema para actualizar perfil (todos campos opcionales)"""
    name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)


class ProfileResponse(ProfileBase):
    """Schema de respuesta con IDs"""
    id: int
    user_id: int


# ============================================================
# Authentication Schemas
# ============================================================

class Token(BaseModel):
    """Respuesta de login con JWT"""
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Credenciales para login"""
    email: EmailStr
    password: str


class UserWithProfile(UserResponse):
    """Usuario con su perfil vinculado (para /auth/me)"""
    profile: Optional[ProfileResponse] = None


# ============================================================
# Password Management Schemas (Hito 6 - AUTH-03)
# ============================================================

class ForgotPasswordRequest(BaseModel):
    """Solicitud de reset de contraseña"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset de contraseña con token"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100, description="Mínimo 8 caracteres")


class ChangePasswordRequest(BaseModel):
    """Cambio de contraseña (usuario autenticado)"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100, description="Mínimo 8 caracteres")


class MessageResponse(BaseModel):
    """Respuesta genérica con mensaje"""
    message: str
