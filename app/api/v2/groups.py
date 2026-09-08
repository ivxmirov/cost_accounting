from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency import get_current_user, get_db
from app.models import User
from app.schemas import (
    GroupCreateSchema,
    GroupDetailResponseSchema,
    GroupListResponseSchema,
    WalletTableSchema,
)
from app.service import groups as groups_service

router = APIRouter()


@router.post(path="/groups", response_model=GroupDetailResponseSchema, status_code=201)
async def create_group_v2(
    group: GroupCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await groups_service.create_group(db, current_user, group)


@router.get(path="/groups/{group_id}", response_model=GroupDetailResponseSchema, status_code=200)
async def get_group_v2(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await groups_service.get_user_group_by_id(db, current_user, group_id)


@router.get(path="/groups", response_model=list[GroupListResponseSchema], status_code=200)
async def get_user_groups_v2(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получение списка групп текущего пользователя.
    """
    return await groups_service.get_current_user_groups(db, current_user)


@router.get(
    path="/groups/{group_id}/wallets/me",
    response_model=list[WalletTableSchema],
    status_code=200,
)
async def get_my_group_wallets_v2(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получает список кошельков текущего пользователя, которые прикрелены к указанной группе.
    """
    return await groups_service.get_user_group_wallets(db, current_user, group_id)


@router.post(
    path="/groups/{group_id}/wallets/{wallet_id}",
    status_code=200,
    response_model=GroupDetailResponseSchema,
)
async def attach_wallet_to_group_v2(
    group_id: int,
    wallet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Прикрепляет кошелек к группе.
    """
    return await groups_service.attach_wallet_to_group(db, current_user, group_id, wallet_id)


@router.delete(
    path="/groups/{group_id}/wallets/{wallet_id}",
    status_code=200,
    response_model=GroupDetailResponseSchema,
)
async def detach_wallet_from_group_v2(
    group_id: int,
    wallet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Открепляет кошелек от группы.
    """
    return await groups_service.detach_wallet_from_group(db, current_user, group_id, wallet_id)


@router.delete(
    path="/groups/{group_id}/members/me",
    status_code=200,
)
async def leave_group_v2(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Выход текущего пользователя из группы.
    """
    await groups_service.leave_group(db, current_user, group_id)
    return {"message": "Вы вышли из группы"}


@router.post(
    path="/groups/{group_id}/members/{user_id}",
    status_code=200,
)
async def add_member_to_group_v2(
    group_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Добавление участника в группу.
    """
    await groups_service.add_user_to_group(db, current_user, group_id, user_id)
    return {"message": "Пользователь добавлен в группу"}


@router.delete(
    path="/groups/{group_id}/members/{user_id}",
    status_code=200,
)
async def remove_member_from_group_v2(
    group_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Удаление участника из группы.
    """
    await groups_service.remove_user_from_group(db, current_user, group_id, user_id)
    return {"message": "Участник удален из группы"}


@router.delete(
    path="/groups/{group_id}",
    status_code=200,
)
async def delete_group_v2(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Удаление группы.
    """
    return await groups_service.delete_group(db, current_user, group_id)
