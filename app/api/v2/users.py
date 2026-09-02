from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency import get_current_user, get_db
from app.models import User
from app.schemas import GroupResponseSchema, UserResponseSchema
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
    current_user: User = Depends(get_current_user),
):
    """
    Получение списка всех пользователей.
    """
    users = await users_service.get_all_users(db)
    return users


@router.get("/users/me/groups", response_model=list[GroupResponseSchema])
async def get_my_groups_v2(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await groups_service.get_current_user_groups(db, current_user)


@router.get(
    path="/users/search",
    status_code=200,
)
async def search_users_v2(
    login: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Поиск пользователя по логину.
    """
    if not login:
        return []

    user = await users_service.search_user_by_login(db, login)

    if not user:
        return []

    return user
