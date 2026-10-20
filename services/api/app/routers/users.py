"""
Users Router

CRUD completo de usuarios:
- POST /users - Registro (público)
- GET /users - Listar (protegido)
- GET /users/{id} - Obtener (protegido)
- PUT /users/{id} - Actualizar (protegido con permisos)
- DELETE /users/{id} - Eliminar (solo admin)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime

from ..schemas.auth import UserCreate, UserUpdate, UserResponse
from ..tinydb_database import users_table, profiles_table, get_user_by_email, User, Profile
from ..auth.password import hash_password
from ..auth.dependencies import get_current_active_user, require_admin

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.post("", response_model=UserResponse, status_code=201)
async def register_user(user_data: UserCreate):
    """
    Registrar nuevo usuario (endpoint público).

    Crea User + Profile si se proporcionan datos de perfil inicial.
    Por defecto, role='user' (puede cambiarse en el request).

    Args:
        - **email**: Email único
        - **password**: Mínimo 8 caracteres
        - **role**: admin | manager | user (default: user)
        - **name**: Nombre completo (opcional, crea Profile)
        - **phone**: Teléfono (opcional)
        - **address**: Dirección (opcional)

    Returns:
        Datos del usuario creado (sin contraseña)

    Raises:
        - **400**: Email ya registrado
    """
    # Verificar email único
    if get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Crear documento de usuario
    user_doc = {
        "email": user_data.email,
        "hashed_password": hash_password(user_data.password),
        "is_active": True,
        "role": user_data.role,
        "created_at": datetime.utcnow().isoformat()
    }

    # Insertar en TinyDB
    user_id = users_table.insert(user_doc)

    # Crear perfil si hay datos
    if user_data.name or user_data.phone or user_data.address:
        profile_doc = {
            "user_id": user_id,
            "name": user_data.name or "",
            "phone": user_data.phone or "",
            "address": user_data.address or ""
        }
        profiles_table.insert(profile_doc)

    # Retornar usuario sin contraseña
    return {
        "id": user_id,
        "email": user_doc["email"],
        "role": user_doc["role"],
        "is_active": user_doc["is_active"],
        "created_at": user_doc["created_at"]
    }


@router.get("", response_model=List[UserResponse])
async def list_users(current_user: dict = Depends(get_current_active_user)):
    """
    Listar todos los usuarios (protegido).

    Requiere: Token JWT válido

    Returns:
        Lista de usuarios (sin contraseñas)

    Raises:
        - **401**: Token inválido o expirado
    """
    all_users = users_table.all()

    return [
        {
            "id": user.doc_id,
            "email": user["email"],
            "role": user["role"],
            "is_active": user["is_active"],
            "created_at": user["created_at"]
        }
        for user in all_users
    ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Obtener usuario por ID (protegido).

    Requiere: Token JWT válido

    Args:
        - **user_id**: ID de TinyDB del usuario

    Returns:
        Datos del usuario (sin contraseña)

    Raises:
        - **401**: Token inválido
        - **404**: Usuario no encontrado
    """
    user = users_table.get(doc_id=user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "id": user.doc_id,
        "email": user["email"],
        "role": user["role"],
        "is_active": user["is_active"],
        "created_at": user["created_at"]
    }


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Actualizar usuario (protegido con permisos).

    Permisos:
    - Admin: Puede actualizar cualquier usuario, incluyendo role
    - Usuario: Solo puede actualizar su propio email

    Args:
        - **user_id**: ID del usuario a actualizar
        - **email**: Nuevo email (opcional)
        - **role**: Nuevo role (opcional, solo admin)
        - **is_active**: Activar/desactivar (opcional, solo admin)

    Returns:
        Usuario actualizado

    Raises:
        - **401**: Token inválido
        - **403**: Sin permisos suficientes
        - **404**: Usuario no encontrado
    """
    # Buscar usuario a actualizar
    user = users_table.get(doc_id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Verificar permisos
    is_admin = current_user["role"] == "admin"
    is_self = current_user.doc_id == user_id

    if not is_admin and not is_self:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions. You can only update your own user."
        )

    # Solo admin puede cambiar role
    if user_data.role is not None and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can change roles"
        )

    # Solo admin puede cambiar is_active
    if user_data.is_active is not None and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can activate/deactivate users"
        )

    # Preparar datos a actualizar
    update_data = {}
    if user_data.email is not None:
        # Verificar que nuevo email no esté en uso
        existing_user = get_user_by_email(user_data.email)
        if existing_user and existing_user.doc_id != user_id:
            raise HTTPException(
                status_code=400,
                detail="Email already in use"
            )
        update_data["email"] = user_data.email

    if user_data.role is not None:
        update_data["role"] = user_data.role

    if user_data.is_active is not None:
        update_data["is_active"] = user_data.is_active

    # Actualizar en TinyDB
    if update_data:
        users_table.update(update_data, doc_ids=[user_id])

    # Retornar usuario actualizado
    updated_user = users_table.get(doc_id=user_id)
    return {
        "id": updated_user.doc_id,
        "email": updated_user["email"],
        "role": updated_user["role"],
        "is_active": updated_user["is_active"],
        "created_at": updated_user["created_at"]
    }


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    admin_user: dict = Depends(require_admin)
):
    """
    Eliminar usuario y su perfil vinculado (solo admin).

    Requiere: Token JWT con role='admin'

    Args:
        - **user_id**: ID del usuario a eliminar

    Returns:
        204 No Content

    Raises:
        - **401**: Token inválido
        - **403**: No es admin
        - **404**: Usuario no encontrado
    """
    # Verificar que usuario existe
    user = users_table.get(doc_id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Eliminar perfil vinculado (si existe)
    profiles_table.remove(Profile.user_id == user_id)

    # Eliminar usuario
    users_table.remove(doc_ids=[user_id])

    # 204 No Content (sin return)
