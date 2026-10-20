"""
Authentication Router

Endpoints de autenticación: login y obtener info del usuario actual.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from ..schemas.auth import Token, LoginRequest, UserWithProfile
from ..tinydb_database import get_user_by_email, get_profile_by_user_id
from ..auth.password import verify_password
from ..auth.jwt import create_access_token
from ..auth.dependencies import get_current_active_user

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest):
    """
    Autenticar usuario y retornar token JWT.

    - **email**: Email del usuario
    - **password**: Contraseña en texto plano

    Returns:
        - **access_token**: Token JWT firmado
        - **token_type**: "bearer"

    Raises:
        - **401**: Email o contraseña incorrectos
        - **400**: Usuario desactivado
    """
    # Buscar usuario por email
    user = get_user_by_email(credentials.email)

    # Verificar que usuario existe y contraseña es correcta
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificar que usuario está activo
    if not user.get("is_active", False):
        raise HTTPException(
            status_code=400,
            detail="Inactive user"
        )

    # Crear token JWT con user_id en el payload
    access_token = create_access_token(data={"sub": user.doc_id})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserWithProfile)
async def get_current_user_info(current_user: dict = Depends(get_current_active_user)):
    """
    Obtener información del usuario autenticado + su perfil vinculado.

    Requiere: Token JWT válido en header Authorization

    Returns:
        - Datos del usuario (email, role, is_active, created_at)
        - Profile vinculado si existe

    Raises:
        - **401**: Token inválido o expirado
        - **400**: Usuario desactivado
    """
    # Buscar perfil del usuario
    profile = get_profile_by_user_id(current_user.doc_id)

    # Formatear respuesta
    response = {
        "id": current_user.doc_id,
        "email": current_user["email"],
        "role": current_user["role"],
        "is_active": current_user["is_active"],
        "created_at": current_user["created_at"],
        "profile": None
    }

    # Agregar perfil si existe
    if profile:
        response["profile"] = {
            "id": profile.doc_id,
            "user_id": profile["user_id"],
            "name": profile["name"],
            "phone": profile.get("phone", ""),
            "address": profile.get("address", "")
        }

    return response
