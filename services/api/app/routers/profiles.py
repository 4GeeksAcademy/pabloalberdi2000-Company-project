"""
Profiles Router

Gestión de perfil del usuario autenticado:
- GET /profiles/me - Obtener perfil
- PUT /profiles/me - Actualizar perfil
"""

from fastapi import APIRouter, Depends, HTTPException

from ..schemas.auth import ProfileResponse, ProfileUpdate
from ..tinydb_database import profiles_table, Profile
from ..auth.dependencies import get_current_active_user

router = APIRouter(
    prefix="/profiles",
    tags=["Profiles"]
)


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(current_user: dict = Depends(get_current_active_user)):
    """
    Obtener perfil del usuario autenticado.

    Requiere: Token JWT válido

    Returns:
        Datos del perfil (name, phone, address)

    Raises:
        - **401**: Token inválido
        - **404**: Perfil no encontrado
    """
    # Buscar perfil por user_id
    profile_list = profiles_table.search(Profile.user_id == current_user.doc_id)

    if not profile_list:
        raise HTTPException(
            status_code=404,
            detail="Profile not found. Create one by updating."
        )

    profile = profile_list[0]

    return {
        "id": profile.doc_id,
        "user_id": profile["user_id"],
        "name": profile["name"],
        "phone": profile.get("phone", ""),
        "address": profile.get("address", "")
    }


@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    profile_data: ProfileUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Actualizar perfil del usuario autenticado.

    Si el perfil no existe, lo crea automáticamente.
    Campos no proporcionados no se modifican.

    Requiere: Token JWT válido

    Args:
        - **name**: Nombre completo (opcional)
        - **phone**: Teléfono (opcional)
        - **address**: Dirección (opcional)

    Returns:
        Perfil actualizado

    Raises:
        - **401**: Token inválido
    """
    # Buscar perfil existente
    profile_list = profiles_table.search(Profile.user_id == current_user.doc_id)

    # Caso 1: Perfil no existe - Crear nuevo
    if not profile_list:
        new_profile = {
            "user_id": current_user.doc_id,
            "name": profile_data.name or "",
            "phone": profile_data.phone or "",
            "address": profile_data.address or ""
        }
        profile_id = profiles_table.insert(new_profile)

        return {
            "id": profile_id,
            "user_id": new_profile["user_id"],
            "name": new_profile["name"],
            "phone": new_profile["phone"],
            "address": new_profile["address"]
        }

    # Caso 2: Perfil existe - Actualizar
    profile = profile_list[0]

    # Preparar datos a actualizar (solo campos proporcionados)
    update_data = {}
    if profile_data.name is not None:
        update_data["name"] = profile_data.name
    if profile_data.phone is not None:
        update_data["phone"] = profile_data.phone
    if profile_data.address is not None:
        update_data["address"] = profile_data.address

    # Actualizar en TinyDB
    if update_data:
        profiles_table.update(update_data, doc_ids=[profile.doc_id])

    # Retornar perfil actualizado
    updated_profile = profiles_table.get(doc_id=profile.doc_id)

    return {
        "id": updated_profile.doc_id,
        "user_id": updated_profile["user_id"],
        "name": updated_profile["name"],
        "phone": updated_profile.get("phone", ""),
        "address": updated_profile.get("address", "")
    }
