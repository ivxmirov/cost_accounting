from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency import get_current_user, get_db
from app.models import User
from app.schemas import GroupDetailResponseSchema, UserResponseSchema
from app.service import groups as groups_service
from app.service import users as users_service

router = APIRouter()


@router.get(
    path="/users",
    status_code=200,
    response_model=list[UserResponseSchema],
)
async def get_all_users_v2(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Получить список всех пользователей."""

    return await users_service.get_all_users(db)


@router.get("/users/me/groups", response_model=list[GroupDetailResponseSchema])
async def get_my_groups_v2(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await groups_service.get_current_user_groups(db, current_user)


@router.get(path="/users/search", status_code=200)
async def search_users_v2(
    login: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Искать пользователя по логину."""

    return await users_service.search_user_by_login(db, login)


@router.delete(path="users/me", status_code=200)
async def delete_current_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Удалить текущего пользователя."""

    return await users_service.delete_current_user(db, current_user)
