import logging
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import app.repository.users as users_repository
from app.enum import CurrencyEnum
from app.models import Group, User
from app.repository import groups as groups_repository
from app.repository.groups import is_user_in_group
from app.schemas import GroupCreateSchema, GroupResponseSchema
from app.service import exchange_service

logger = logging.getLogger(__name__)


async def create_group(
    db: AsyncSession,
    current_user: User,
    group_data: GroupCreateSchema,
) -> GroupResponseSchema:
    """
    Создает новую группу с бизнес-валидацией.

    Бизнес-правила:
    1. Группа с таким названием у пользователя-создателя не должна существовать
    2. Минимум 2 участника (создатель + минимум 1 дополнительный)

    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
        group_data: Данные для создания группы (название, члены группы)
    Returns:
        Информация о созданной группе
    Raises:
        HTTPException: Если группа с таким названием уже существует
        HTTPException: Если создатель в списке участников
        HTTPException: Если какой-то пользователь не найден
    """
    # 1. Проверка на дубликат
    if await groups_repository.is_group_exist(
        db,
        user_id=current_user.id,
        group_name=group_data.name,
    ):
        raise HTTPException(
            status_code=400,
            detail="Нельзя создавать несколько групп с одинаковым названием",
        )

    # 2. Получаем всех участников по логинам с проверкой на существование
    unique_logins = set(group_data.members_logins)
    members = []
    for login in unique_logins:
        user = await users_repository.get_user(db, login)
        if not user:
            raise HTTPException(
                status_code=400,
                detail=f"Пользователь с логином '{login}' не найден",
            )
        members.append(user)

    # 3. Убираем создателя из списка участников (безопасно по ID)
    other_members = [m for m in members if m.id != current_user.id]

    # 4. Проверяем, что остался хотя бы один участник помимо создателя группы
    if not other_members:
        raise HTTPException(status_code=400, detail="Добавьте хотя бы одного участника помимо себя")

    new_group: Group = await groups_repository.create_group(
        db,
        creator_id=current_user.id,
        group_name=group_data.name,
        members=other_members,
    )

    await db.commit()
    return GroupResponseSchema.model_validate(obj=new_group)


async def get_current_user_groups(
    db: AsyncSession,
    current_user: User,
) -> list[GroupResponseSchema]:
    """
    Возвращает список всех групп, в которых состоит текущий пользователь.

    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
    Returns:
        Список всех групп, в которых состоит текущий пользователь
    """
    groups = await groups_repository.get_user_groups(db, user_id=current_user.id)
    result = []

    for group in groups:
        schema = GroupResponseSchema.model_validate(obj=group)
        result.append(schema)

    return result


async def get_user_group_by_id(
    db: AsyncSession,
    current_user: User,
    group_id: int,
) -> GroupResponseSchema:
    """
    Получает информацию о группе с общим балансом.

    Args:
        db: Сессия БД
        current_user: Текущий пользователь
        group_id: Уникальный идентификатор группы

    Returns:
        Информация о группе с балансом

    Raises:
        HTTPException: Если группа не найдена или у пользователя нет к ней доступа
    """

    group = await groups_repository.get_group_by_id(db, group_id)

    if not group:
        raise HTTPException(status_code=404, detail="Такой группы не существует")

    # Проверяем, является ли пользователь участником группы
    if not await is_user_in_group(db, current_user.id, group_id):
        raise HTTPException(status_code=403, detail="Вы не состоите в этой группе")

    total_balance: Decimal = await calculate_group_balance(db, group_id)

    group_schema = GroupResponseSchema.model_validate(group)
    group_schema.total_balance = total_balance

    return group_schema


async def calculate_group_balance(db: AsyncSession, group_id: int) -> Decimal:
    """
    Получает общий баланс группы с конвертацией валют в рубли.

    Бизнес-логика:
        Учитываются только те кошельки, которые участники прикрепили к группе.
        Каждый участник группы сам решает, какие из своих кошельков прикреплять.
        Участник группы может не прикреплять ни одного кошелька.

        При расчете баланса группы учитывается эффективный баланс кошелька.
        Для дебетовых кошельков: эффективный баланс = текущий баланс.
        Для кредитных кошельков: эффективный баланс = текущий баланс - кредитный лимит.

    Args:
        db: Сессия базы данных
        group_id: Уникальный идентификатор группы
    Returns:
        Общий баланс группы в рублях
    """
    wallets = await groups_repository.get_group_wallets(db, group_id)
    total_balance = Decimal("0")

    for wallet in wallets:
        # Это условие выполнится только у дебетовых кошельков
        if wallet.credit_limit is None:
            credit_limit = Decimal("0")
        else:
            # Это условие выполнится только у кредитных кошельков
            credit_limit: Decimal = wallet.credit_limit

        if wallet.currency == CurrencyEnum.RUB:
            total_balance += wallet.balance - credit_limit
        else:
            exchange_rate = await exchange_service.get_exchange_rate(
                wallet.currency,
                CurrencyEnum.RUB,
            )
            total_balance += exchange_rate * (wallet.balance - credit_limit)

    return total_balance


# async def attach_wallet_to_group(
#     db: AsyncSession, group_id: int, wallet_id: int,
# ) -> None:
#     """
#     Прикрепляет кошелек к группе.

#     Args:
#         db: Сессия БД
#         group_id: ID группы
#         wallet_id: ID кошелька
#     """
#     # Проверяем, что кошелек принадлежит участнику группы
#     result = await db.execute(
#         select(Group)
#         .join(group_members)
#         .join(Wallet)
#         .where(
#             Group.id == group_id,
#             Wallet.id == wallet_id,
#             Wallet.user_id == group_members.c.user_id,
#         )
#     )

#     if not result.scalar_one_or_none():
#         raise HTTPException(
#             status_code=403,
#             detail="Кошелек должен принадлежать участнику группы",
#         )

#     # Вставляем связь
#     await db.execute(
#         group_wallets.insert().values(
#             group_id=group_id,
#             wallet_id=wallet_id,
#         ),
#     )
