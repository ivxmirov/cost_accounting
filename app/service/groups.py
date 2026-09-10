import logging
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import app.repository.users as users_repository
from app.enum import CurrencyEnum
from app.models import Group, User, Wallet
from app.repository import groups as groups_repository
from app.schemas import (
    GroupCreateSchema,
    GroupDetailResponseSchema,
    GroupListResponseSchema,
    MemberBalanceSchema,
    WalletTableSchema,
)
from app.service import exchange_service
from app.service.wallets import wallets_repository

logger = logging.getLogger(__name__)


async def create_group(
    db: AsyncSession,
    current_user: User,
    group_data: GroupCreateSchema,
) -> GroupDetailResponseSchema:
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
    # Проверка на дубликат
    if await groups_repository.is_group_exist(
        db,
        user_id=current_user.id,
        group_name=group_data.name,
    ):
        raise HTTPException(
            status_code=400,
            detail="Нельзя создавать несколько групп с одинаковым названием",
        )

    # Получаем всех участников по логинам с проверкой на существование
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

    # Убираем создателя из списка участников (безопасно по Уникальный идентификатор)
    other_members = [m for m in members if m.id != current_user.id]

    # Проверяем, что остался хотя бы один участник помимо создателя группы
    if not other_members:
        raise HTTPException(status_code=400, detail="Добавьте хотя бы одного участника помимо себя")

    new_group: Group = await groups_repository.create_group(
        db,
        creator_id=current_user.id,
        group_name=group_data.name,
        members=other_members,
    )

    await db.commit()
    await db.refresh(new_group)

    return GroupDetailResponseSchema(
        id=new_group.id,
        name=new_group.name,
        creator=new_group.creator,
        creator_login=current_user.login,
        members=[current_user.login] + [member.login for member in other_members],
        created_at=new_group.created_at,
        total_balance=Decimal("0"),
        member_balances=[],
        wallets=[],
    )


async def delete_group(
    db: AsyncSession,
    current_user: User,
    group_id: int,
) -> None:
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
    # Проверяем, существует ли группа
    # Проверяем, является ли текущий пользователь создателем группы
    await _get_group_and_check_creator(db, current_user, group_id)

    await groups_repository.delete_group(db, group_id)


async def get_current_user_groups(
    db: AsyncSession,
    current_user: User,
) -> list[GroupListResponseSchema]:
    """
    Получение списка групп для отображения в таблице.
    """
    groups: list[Group] = await groups_repository.get_user_groups(db, user_id=current_user.id)
    groups.sort(key=lambda group: group.name.lower())
    result = []

    for group in groups:
        total_balance = await calculate_group_balance(db, group.id)
        members_count = len(group.members)

        schema = GroupListResponseSchema(
            id=group.id,
            name=group.name,
            creator_id=group.creator,
            members_count=members_count,
            created_at=group.created_at,
            total_balance=total_balance,
        )

        result.append(schema)

    return result


async def _get_group_and_check_membership(
    db: AsyncSession,
    current_user: User,
    group_id: int,
) -> Group:
    """
    Получает группу и проверяет, что текущий пользователь является её участником.

    Raises:
        HTTPException 404: Если группа не найдена
        HTTPException 403: Если пользователь не является участником группы
    """
    group = await groups_repository.get_group_by_id(db, group_id)

    if not group:
        raise HTTPException(status_code=404, detail="Такой группы не существует")

    if not await groups_repository.is_user_in_group(db, current_user.id, group_id):
        raise HTTPException(status_code=403, detail="Вы не являетесь участником этой группы")

    return group


async def _get_group_and_check_creator(
    db: AsyncSession,
    current_user: User,
    group_id: int,
) -> Group:
    """
    Получает группу и проверяет, что текущий пользователь является её создателем.

    Raises:
        HTTPException 404: Если группа не найдена
        HTTPException 403: Если пользователь не является создателем группы
    """
    group = await groups_repository.get_group_by_id(db, group_id)

    if not group:
        raise HTTPException(status_code=404, detail="Такой группы не существует")

    if not await groups_repository.is_user_group_creator(db, group_id, current_user.id):
        raise HTTPException(
            status_code=403,
            detail="Только создатель группы может выполнить это действие",
        )

    return group


async def get_user_group_by_id(
    db: AsyncSession,
    current_user: User,
    group_id: int,
) -> GroupDetailResponseSchema:
    """
    Получает информацию о группе с общим балансом.
    """
    # Проверяем, существует ли группа
    # Проверяем, является ли пользователь участником группы
    group = await _get_group_and_check_membership(db, current_user, group_id)

    total_balance: Decimal = await calculate_group_balance(db, group_id)
    member_balances = await calculate_member_balances(db, group_id)

    # Сортируем участников: сначала текущий пользователь, потом остальные по алфавиту
    # Кортеж (member.login != current_user.login, member.login.lower()) сортирует:
    #   - сначала по False (0) - текущий пользователь;
    #   - потом по True (1) - остальные;
    #   - внутри каждой группы - по алфавиту.
    group.members.sort(
        key=lambda member: (member.login != current_user.login, member.login.lower())
    )
    member_balances.sort(key=lambda x: (x.login != current_user.login, x.login.lower()))

    user_wallets = await groups_repository.get_user_group_wallets(
        db, group_id=group_id, user_id=current_user.id
    )

    return GroupDetailResponseSchema(
        id=group.id,
        name=group.name,
        creator=group.creator,
        creator_login=group.creator_login if group.creator_user else None,
        members=[member.login for member in group.members],
        created_at=group.created_at,
        total_balance=total_balance,
        member_balances=member_balances,
        wallets=[
            WalletTableSchema(
                id=wallet.id,
                name=wallet.name,
                currency=wallet.currency,
                type=wallet.type,
                user_id=wallet.user_id,
                effective_balance=wallet.effective_balance,
                balance=wallet.balance,
            )
            for wallet in user_wallets
        ],
    )


async def get_user_group_wallets(
    db: AsyncSession,
    current_user: User,
    group_id: int,
) -> list[WalletTableSchema]:
    """
    Получает список кошельков текущего пользователя, которые прикрелены к указанной группе.
    """
    # Проверяем, существует ли группа
    # Проверяем, является ли пользователь участником группы
    await _get_group_and_check_membership(db, current_user, group_id)

    wallets: list[Wallet] = await groups_repository.get_user_group_wallets(
        db, group_id, current_user.id
    )
    wallets.sort(key=lambda wallet: wallet.name.lower())

    result = []
    for wallet in wallets:
        effective_balance: Decimal = await calculate_wallet_effective_balance(wallet)
        result.append(
            WalletTableSchema(
                id=wallet.id,
                name=wallet.name,
                currency=wallet.currency,
                type=wallet.type,
                balance=wallet.balance,
                user_id=wallet.user_id,
                effective_balance=effective_balance,
            )
        )

    return result


async def calculate_wallet_effective_balance(wallet: Wallet) -> Decimal:
    """
    Рассчитывает эффективный баланс кошелька в рублях.
    """
    if wallet.currency == CurrencyEnum.RUB:
        return wallet.effective_balance
    exchange_rate = await exchange_service.get_exchange_rate(
        wallet.currency,
        CurrencyEnum.RUB,
    )
    return exchange_rate * wallet.effective_balance


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
    # Проверяем, является ли пользователь участником группы
    await _get_group_and_check_membership(db, current_user, group_id)

    # Проверяем, что кошелек принадлежит пользователю
    if not await wallets_repository.get_wallet_by_id(db, current_user.id, wallet_id):
        raise HTTPException(status_code=404, detail="У вас нет такого кошелька")

    # Проверяем, не прикреплен ли уже кошелек к группе
    if await groups_repository.is_wallet_attached_to_group(db, group_id, wallet_id):
        raise HTTPException(status_code=400, detail="Кошелек уже прикреплен к группе")

    # Если все проверки пройдены, прикрепляем кошелек к группе
    await groups_repository.attach_wallet_to_group(db, group_id, wallet_id)

    # Возвращаем обновленную группу
    return await groups_repository.get_group_by_id(db, group_id)


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
    # Проверяем, является ли пользователь участником группы
    await _get_group_and_check_membership(db, current_user, group_id)

    # Проверяем, что кошелек принадлежит пользователю
    if not await wallets_repository.get_wallet_by_id(db, current_user.id, wallet_id):
        raise HTTPException(status_code=404, detail="У вас нет такого кошелька")

    # Проверяем, прикреплен ли кошелек к этой группе
    if not await groups_repository.is_wallet_attached_to_group(db, group_id, wallet_id):
        raise HTTPException(status_code=400, detail="Кошелек не прикреплен к группе")

    # Если все проверки пройдены, открепляем кошелек от группы
    await groups_repository.detach_wallet_from_group(db, group_id, wallet_id)

    # Возвращаем обновленную группу
    return await groups_repository.get_group_by_id(db, group_id)


async def leave_group(
    db: AsyncSession,
    current_user: User,
    group_id: int,
) -> None:
    """
    Удаляет текущего пользователя из группы.

    Бизнес-логика:
        если создатель группы выходит из нее, то удаляется вся группа

    Args:
        db: Сессия БД
        current_user: Текущий пользователь
        group_id: Уникальный идентификатор группы

    Raises:
        HTTPException: Если группа не найдена или пользователь не является участником группы
    """

    # Проверяем, существует ли группа
    # Проверяем, является ли пользователь участником группы
    await _get_group_and_check_membership(db, current_user, group_id)

    # Если пользователь является создателем группы, то удаляем группу
    if await groups_repository.is_user_group_creator(db, group_id, current_user.id):
        await groups_repository.delete_group(db, group_id)
    else:
        # Если пользователь не является создателем группы, то открепляем его кошельки от группы
        await groups_repository.detach_user_wallets_from_group(db, group_id, current_user.id)
        # Текущий пользователь удаляется из группы
        await groups_repository.remove_user_from_group(db, group_id, current_user.id)


async def add_user_to_group(
    db: AsyncSession,
    current_user: User,
    group_id: int,
    user_id: int,
) -> None:
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
    # Проверяем, является ли текущий пользователь создателем группы
    await _get_group_and_check_creator(db, current_user, group_id)

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


async def add_users_to_group(
    db: AsyncSession,
    current_user: User,
    group_id: int,
    user_ids: list[int],
) -> dict:
    """
    Добавить несколько пользователей в группу.

    Returns:
        dict: {added: [...], skipped: [...], not_found: [...]}
    """
    # Проверяем, существует ли группа
    # Проверяем, является ли текущий пользователь создателем группы
    await _get_group_and_check_creator(db, current_user, group_id)

    if not user_ids:
        raise HTTPException(status_code=400, detail="Добавьте хотя бы одного пользователя")

    # Убираем дубликаты
    unique_ids = set(user_ids)

    if len(unique_ids) == 1 and current_user.id in unique_ids:
        raise HTTPException(
            status_code=400,
            detail="Добавьте хотя бы одного пользователя помимо себя",
        )

    # Убираем создателя группы
    unique_ids.discard(current_user.id)

    added = []
    skipped = []
    not_found = []

    for user_id in unique_ids:
        user = await users_repository.get_user_by_id(db, user_id)
        if not user:
            not_found.append(user_id)
            continue

        if await groups_repository.is_user_in_group(db, user_id, group_id):
            skipped.append(user.login)
            continue

        await groups_repository.add_user_to_group(db, group_id, user_id)
        added.append(user.login)

    return {
        "message": (
            f"Добавлено: {len(added)}, пропущено: {len(skipped)}, не найдено: {len(not_found)}"
        ),
        "added": added,
        "skipped": skipped,
        "not_found": not_found,
    }


async def remove_user_from_group(
    db: AsyncSession,
    current_user: User,
    group_id: int,
    user_id: int,
) -> None:
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
    # Проверяем, является ли текущий пользователь создателем группы
    await _get_group_and_check_creator(db, current_user, group_id)

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
