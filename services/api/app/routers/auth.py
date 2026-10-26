"""
Authentication Router

Endpoints de autenticación: login y obtener info del usuario actual.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from ..schemas.auth import (
    Token,
    LoginRequest,
    UserWithProfile,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    MessageResponse
)
from ..tinydb_database import (
    get_user_by_email,
    get_profile_by_user_id,
    get_user_by_id,
    users_table
)
from ..auth.password import verify_password, hash_password
from ..auth.jwt import create_access_token
from ..auth.dependencies import get_current_active_user
from ..auth.reset_token import create_reset_token, verify_reset_token, invalidate_reset_token
from ..email.service import send_password_reset_email

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


# ============================================================
# Password Management Endpoints (Hito 6 - AUTH-03)
# ============================================================

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Solicitar reset de contraseña.

    ⚠️ ANTI-ENUMERACIÓN: Siempre retorna 200, nunca revela si email existe.

    Args:
        email: Email del usuario

    Returns:
        Mensaje genérico de confirmación

    Security:
        - No revela si el email está registrado
        - Token de reset enviado solo a emails válidos
        - Token expira en 30 minutos
    """
    user = get_user_by_email(request.email)

    if user:
        # Usuario existe - generar token y enviar email
        try:
            reset_token = create_reset_token(user.doc_id)
            send_password_reset_email(request.email, reset_token)
        except Exception as e:
            # Log error pero no exponer al cliente (anti-enumeración)
            print(f"Failed to send reset email to {request.email}: {str(e)}")
            # ⚠️ Mantener mismo mensaje para no revelar si email existe

    # ⚠️ CRÍTICO: Siempre mismo mensaje (no revelar si email existe)
    return {
        "message": "Si esa dirección está registrada, recibirás un enlace de restablecimiento en breve."
    }


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(request: ResetPasswordRequest):
    """
    Restablecer contraseña con token.

    Valida:
    - Token válido y no expirado
    - Token no usado previamente
    - Password con mínimo 8 caracteres

    Args:
        token: Token JWT de reset
        new_password: Nueva contraseña (min 8 caracteres)

    Returns:
        Mensaje de confirmación

    Raises:
        - **400**: Token inválido, expirado o ya utilizado
        - **404**: Usuario no encontrado
    """
    # Verificar token
    payload = verify_reset_token(request.token)

    if not payload:
        raise HTTPException(
            status_code=400,
            detail="Token inválido, expirado o ya utilizado"
        )

    user_id = payload.get("sub")
    jti = payload.get("jti")

    # Obtener usuario
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Actualizar contraseña con hash seguro
    new_hashed_password = hash_password(request.new_password)
    users_table.update(
        {"hashed_password": new_hashed_password},
        doc_ids=[user_id]
    )

    # ⚠️ CRÍTICO: Invalidar token para prevenir reuso
    invalidate_reset_token(jti, user_id)

    return {"message": "Contraseña restablecida exitosamente"}


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Cambiar contraseña (usuario autenticado).

    Requiere:
    - Token JWT válido
    - Contraseña actual correcta
    - Nueva contraseña mínimo 8 caracteres

    Args:
        current_password: Contraseña actual del usuario
        new_password: Nueva contraseña (min 8 caracteres)

    Returns:
        Mensaje de confirmación

    Raises:
        - **401**: Token inválido o expirado
        - **400**: Contraseña actual incorrecta
    """
    # Verificar contraseña actual
    if not verify_password(request.current_password, current_user["hashed_password"]):
        raise HTTPException(
            status_code=400,
            detail="Contraseña actual incorrecta"
        )

    # Actualizar contraseña con hash seguro
    new_hashed_password = hash_password(request.new_password)
    users_table.update(
        {"hashed_password": new_hashed_password},
        doc_ids=[current_user.doc_id]
    )

    return {"message": "Contraseña actualizada exitosamente"}
