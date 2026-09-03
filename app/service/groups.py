import logging
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import app.repository.users as users_repository
from app.enum import CurrencyEnum
from app.models import Group, User, Wallet
from app.repository import groups as groups_repository
from app.repository.groups import is_user_in_group
from app.schemas import GroupCreateSchema, GroupResponseSchema, MemberBalanceSchema
from app.service import exchange_service
from app.service.wallets import wallets_repository

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
        user = await users_repository.get_user_by_login(db, login)
        if not user:
            raise HTTPException(
                status_code=400,
                detail=f"Пользователь с логином '{login}' не найден",
            )
        members.append(user)

    # 3. Убираем создателя из списка участников (безопасно по Уникальный идентификатор)
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

    # Проверяем, существует ли группа
    if not group:
        raise HTTPException(status_code=404, detail="Такой группы не существует")

    # Проверяем, является ли пользователь участником группы
    if not await is_user_in_group(db, current_user.id, group_id):
        raise HTTPException(status_code=403, detail="Вы не являетесь участником этой группы")

    total_balance: Decimal = await calculate_group_balance(db, group_id)
    member_balances = await calculate_member_balances(db, group_id)

    # Сортируем участников по алфавиту
    group.members.sort(key=lambda member: member.login.lower())
    member_balances.sort(key=lambda x: x.login.lower())
    group_schema = GroupResponseSchema.model_validate(group)
    group_schema.total_balance = total_balance
    group_schema.member_balances = member_balances

    return group_schema


async def calculate_wallet_effective_balance(wallet):
    """
    Рассчитывает эффективный баланс кошелька.

    Для дебетовых кошельков: эффективный баланс = текущий баланс.
    Для кредитных кошельков: эффективный баланс = текущий баланс - кредитный лимит.
    """
    # Это условие выполнится только у дебетовых кошельков
    if wallet.credit_limit is None:
        credit_limit = Decimal("0")
    else:
        # Это условие выполнится только у кредитных кошельков
        credit_limit: Decimal = wallet.credit_limit

    if wallet.currency == CurrencyEnum.RUB:
        return wallet.balance - credit_limit
    else:
        exchange_rate = await exchange_service.get_exchange_rate(
            wallet.currency,
            CurrencyEnum.RUB,
        )
        return exchange_rate * (wallet.balance - credit_limit)


async def calculate_member_balances(
    db: AsyncSession,
    group_id: int,
) -> list[MemberBalanceSchema]:
    """
    Рассчитывает эффективный баланс каждого участника группы.

    Бизнес-логика:
        Учитываются только те кошельки, которые участники прикрепили к группе.
        Каждый участник группы сам решает, какие из своих кошельков прикреплять.
        Участник группы может не прикреплять ни одного кошелька.
        При расчете баланса группы учитываются эффективные балансы кошельков.

    Args:
        db: Сессия БД
        group_id: Уникальный идентификатор группы

    Returns:
        Список балансов участников, отсортированный по алфавиту
    """
    wallets = await groups_repository.get_group_wallets(db, group_id)

    # Словарь для хранения балансов участников
    member_balances_dict = {}

    for wallet in wallets:
        effective_balance: Decimal = await calculate_wallet_effective_balance(wallet)

        # Добавляем к балансу участника
        user_login = wallet.user.login
        if user_login not in member_balances_dict:
            member_balances_dict[user_login] = Decimal("0")
        member_balances_dict[user_login] += effective_balance

    # Создаем список и сортируем по алфавиту
    member_balances: list[MemberBalanceSchema] = [
        MemberBalanceSchema(login=login, effective_balance=balance)
        for login, balance in member_balances_dict.items()
    ]
    return member_balances


async def calculate_group_balance(db: AsyncSession, group_id: int) -> Decimal:
    """
    Получает общий баланс группы с конвертацией валют в рубли.

    Бизнес-логика:
        Учитываются только те кошельки, которые участники прикрепили к группе.
        Каждый участник группы сам решает, какие из своих кошельков прикреплять.
        Участник группы может не прикреплять ни одного кошелька.
        При расчете баланса группы учитываются эффективные балансы кошельков.

    Args:
        db: Сессия базы данных
        group_id: Уникальный идентификатор группы
    Returns:
        Общий баланс группы в рублях
    """
    wallets: list[Wallet] = await groups_repository.get_group_wallets(db, group_id)
    total_balance = Decimal("0")

    for wallet in wallets:
        total_balance += await calculate_wallet_effective_balance(wallet)

    return total_balance


async def attach_wallet_to_group(
    db: AsyncSession,
    current_user: User,
    group_id: int,
    wallet_id: int,
) -> Group | None:
    """
    Прикрепляет кошелек к группе.

    Args:
        db: Сессия БД
        current_user: Текущий пользователь
        group_id: Уникальный идентификатор группы
        wallet_id: Уникальный идентификатор кошелька

    Raises:
        HTTPException: Если группа не найдена, кошелек не найден,
                       пользователь не участник группы, или кошелек уже прикреплен
    """

    # Проверяем, существует ли группа
    if not await groups_repository.get_group_by_id(db, group_id):
        raise HTTPException(status_code=404, detail="Такой группы не существует")

    # Проверяем, является ли пользователь участником группы
    if not await groups_repository.is_user_in_group(db, current_user.id, group_id):
        raise HTTPException(status_code=403, detail="Вы не являетесь участником группы")

    # Проверяем, что кошелек принадлежит пользователю
    if not await wallets_repository.get_wallet_by_id(db, current_user.id, wallet_id):
        raise HTTPException(status_code=404, detail="У вас нет такого кошелька")

    # Проверяем, не прикреплен ли уже кошелек к группе
    if await groups_repository.is_wallet_attached_to_group(db, group_id, wallet_id):
        raise HTTPException(status_code=400, detail="Кошелек уже прикреплен к группе")

    # Если все проверки пройдены, прикрепляем кошелек к группе
    await groups_repository.attach_wallet_to_group(db, group_id, wallet_id)

    # Возвращаем обновленную группу
    updated_group = await groups_repository.get_group_by_id(db, group_id)
    return updated_group


async def detach_wallet_from_group(
    db: AsyncSession,
    current_user: User,
    group_id: int,
    wallet_id: int,
) -> Group | None:
    """
    Открепляет кошелек от группы.

    Args:
        db: Сессия БД
        current_user: Текущий пользователь
        group_id: Уникальный идентификатор группы
        wallet_id: Уникальный идентификатор кошелька

    Raises:
        HTTPException: Если группа не найдена, кошелек не найден,
                       пользователь не участник группы, или кошелек не прикреплен к группе
    """

    # Проверяем, существует ли группа
    if not await groups_repository.get_group_by_id(db, group_id):
        raise HTTPException(status_code=404, detail="Такой группы не существует")

    # Проверяем, является ли пользователь участником группы
    if not await groups_repository.is_user_in_group(db, current_user.id, group_id):
        raise HTTPException(status_code=403, detail="Вы не являетесь участником этой группы")

    # Проверяем, что кошелек принадлежит пользователю
    if not await wallets_repository.get_wallet_by_id(db, current_user.id, wallet_id):
        raise HTTPException(status_code=404, detail="У вас нет такого кошелька")

    # Проверяем, прикреплен ли кошелек к этой группе
    if not await groups_repository.is_wallet_attached_to_group(db, group_id, wallet_id):
        raise HTTPException(status_code=400, detail="Кошелек не прикреплен к группе")

    # Если все проверки пройдены, открепляем кошелек от группы
    await groups_repository.detach_wallet_from_group(db, group_id, wallet_id)

    # Возвращаем обновленную группу
    updated_group = await groups_repository.get_group_by_id(db, group_id)
    return updated_group


async def leave_group(
    db: AsyncSession,
    current_user: User,
    group_id: int,
) -> None:
    """
    Удаляет текущего пользователя из группы.

    Args:
        db: Сессия БД
        current_user: Текущий пользователь
        group_id: Уникальный идентификатор группы

    Raises:
        HTTPException: Если группа не найдена или пользователь не является участником группы
    """
    # Проверяем, существует ли группа
    if not await groups_repository.get_group_by_id(db, group_id):
        raise HTTPException(status_code=404, detail="Такой группы не существует")

    # Проверяем, является ли пользователь участником группы
    if not await groups_repository.is_user_in_group(db, current_user.id, group_id):
        raise HTTPException(status_code=403, detail="Вы не являетесь участником этой группы")

    # Открепляем кошельки пользователя от группы
    await groups_repository.detach_user_wallets_from_group(db, group_id, current_user.id)

    # Если все проверки пройдены, текущий пользователь удаляется из группы
    await groups_repository.remove_user_from_group(db, group_id, current_user.id)


async def add_user_to_group(
    db: AsyncSession,
    current_user: User,
    group_id: int,
    user_id: int,
) -> dict:
    """
    Добавляет пользователя в группу.

    Args:
        db: Сессия БД
        current_user: Текущий пользователь
        group_id: Уникальный идентификатор группы
        user_id: Уникальный идентификатор добавляемого пользователя

    Raises:
        HTTPException: Если группа не найдена
                       или добавляемый пользователь не найден,
                       или текущий пользователь не является создателем группы
    """

    # Проверяем, существует ли группа
    if not await groups_repository.get_group_by_id(db, group_id):
        raise HTTPException(status_code=404, detail="Такой группы не существует")

    # Проверяем, является ли текущий пользователь создателем группы
    if not await groups_repository.is_user_group_creator(db, group_id, current_user.id):
        raise HTTPException(status_code=403, detail="Вы не можете добавлять участников группы")

    # Проверяем, существует ли добавляемый пользователь
    user = await users_repository.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Нельзя добавить самого себя
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя добавить самого себя")

    # Проверяем, является ли добавляемый пользователь участником группы
    if await groups_repository.is_user_in_group(db, user_id, group_id):
        raise HTTPException(status_code=400, detail="Пользователь уже является участником группы")

    # Если все проверки пройдены, пользователь добавляется в группу
    await groups_repository.add_user_to_group(db, group_id, user_id)

    return {"message": "Пользователь успешно добавлен в группу"}


async def remove_user_from_group(
    db: AsyncSession,
    current_user: User,
    group_id: int,
    user_id: int,
) -> dict:
    """
    Удаление пользователя из группы создателем группы.

    Args:
        db: Сессия БД
        current_user: Текущий пользователь
        group_id: Уникальный идентификатор группы
        user_id: Уникальный идентификатор удаляемого пользователя

    Raises:
        HTTPException: Если группа не найдена
                       или удаляемый пользователь не является участником группы,
                       или текущий пользователь не является создателем группы
    """

    # Проверяем, существует ли группа
    if not await groups_repository.get_group_by_id(db, group_id):
        raise HTTPException(status_code=404, detail="Такой группы не существует")

    # Проверяем, является ли текущий пользователь создателем группы
    if not await groups_repository.is_user_group_creator(db, group_id, current_user.id):
        raise HTTPException(status_code=403, detail="Вы не можете удалять участников группы")

    # Нельзя удалить самого себя
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")

    # Проверяем, является ли удаляемый пользователь участником группы
    if not await groups_repository.is_user_in_group(db, user_id, group_id):
        raise HTTPException(status_code=404, detail="Пользователь не является участником группы")

    # Открепляем кошельки пользователя от группы
    await groups_repository.detach_user_wallets_from_group(db, group_id, user_id)

    # Если все проверки пройдены, пользователь удаляется из группы
    await groups_repository.remove_user_from_group(db, group_id, user_id)

    return {"message": "Пользователь успешно удален из группы"}


async def delete_group(
    db: AsyncSession,
    current_user: User,
    group_id: int,
) -> dict:
    """
    Удаляет группу.

    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
        group_id: Уникальный идентификатор группы

    Returns:
        dict: Сообщение об успешном удалении

    Raises:
        HTTPException: Если группа не найдена
                       или текущий пользователь не является создателем группы
    """
    group = await groups_repository.get_group_by_id(db, group_id)

    if group is None:
        raise HTTPException(status_code=404, detail="Такой группы не существует")

    if not await groups_repository.is_user_group_creator(db, group_id, current_user.id):
        raise HTTPException(status_code=403, detail="Только создатель группы может удалить ее")

    await groups_repository.delete_group(db, group_id)

    return {"message": "Группа удалена"}
