from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models import Group, User, Wallet, group_members, group_wallets
from app.repository.wallets import get_user_wallets


async def is_group_exist(db: AsyncSession, user_id: int, group_name: str) -> bool:
    """Проверяет существование группы с таким именем у пользователя, который ее создает"""
    result = await db.execute(
        select(Group).where(Group.name == group_name, Group.creator == user_id),
    )
    return result.scalar_one_or_none() is not None


async def create_group(
    db: AsyncSession,
    creator_id: int,
    group_name: str,
    members: list[User],
) -> Group:
    """
    Создаёт группу и добавляет создателя как участника.

    Args:
        db: Асинхронная сессия БД
        creator_id: Уникальный идентификатор пользователя-админа
        group_name: Название группы

    Returns:
        Созданная группа с загруженными участниками
    """
    creator = await db.get(User, creator_id)
    group = Group(name=group_name, creator=creator_id)
    group.members.append(creator)  # ty: ignore[invalid-argument-type]  # pyright: ignore[reportArgumentType]

    for member in members:
        group.members.append(member)

    db.add(group)
    await db.flush()

    # Загружаем с отношениями
    result = await db.execute(
        select(Group).options(selectinload(Group.members)).where(Group.id == group.id),
    )
    return result.scalar_one()


async def get_user_groups(db: AsyncSession, user_id: int) -> list[Group]:
    """
    Возвращает из базы данных список всех групп, в которых состоит пользователь.

    Args:
        db: Сессия базы данных
        user_id: Уникальный идентификатор пользователя

    Returns:
        Список групп, в которых состоит пользователь
    """
    result = await db.execute(
        select(Group)
        .join(Group.members)
        .where(User.id == user_id)
        .options(
            selectinload(Group.members),
            joinedload(Group.creator_user),
        ),
    )
    return list(result.scalars().unique().all())


async def get_group_by_id(db: AsyncSession, group_id: int) -> Group | None:
    """Получает группу по Уникальный идентификатор без проверки прав пользователя"""
    result = await db.execute(
        select(Group).where(Group.id == group_id).options(selectinload(Group.members)),
    )
    return result.scalar_one_or_none()


async def attach_wallet_to_group(
    db: AsyncSession,
    group_id: int,
    wallet_id: int,
) -> None:
    """
    Прикрепляет кошелек к группе.

    Args:
        db: Сессия БД
        group_id: Уникальный идентификатор группы
        wallet_id: Уникальный идентификатор кошелька
    """

    await db.execute(
        group_wallets.insert().values(
            group_id=group_id,
            wallet_id=wallet_id,
        ),
    )
    await db.commit()


async def detach_wallet_from_group(
    db: AsyncSession,
    group_id: int,
    wallet_id: int,
) -> None:
    """
    Открепляет кошелек от группы.

    Args:
        db: Сессия БД
        group_id: Уникальный идентификатор группы
        wallet_id: Уникальный идентификатор кошелька
    """
    await db.execute(
        group_wallets.delete().where(
            group_wallets.c.group_id == group_id,
            group_wallets.c.wallet_id == wallet_id,
        ),
    )
    await db.commit()


async def get_group_wallets(
    db: AsyncSession,
    group_id: int,
) -> list[Wallet]:
    """
    Получает все кошельки, прикрепленные к группе.

    Args:
        db: Сессия БД
        group_id: Уникальный идентификатор группы

    Returns:
        Список кошельков группы
    """
    result = await db.execute(
        select(Wallet).join(group_wallets).where(group_wallets.c.group_id == group_id),
    )
    return list(result.scalars().all())


async def is_user_in_group(
    db: AsyncSession,
    user_id: int,
    group_id: int,
) -> bool:
    """
    Проверяет, состоит ли пользователь в группе.

    Args:
        db: Сессия БД
        user_id: Уникальный идентификатор пользователя
        group_id: Уникальный идентификатор группы

    Returns:
        True, если пользователь состоит в группе, иначе False
    """
    stmt = select(
        exists().where(
            group_members.c.group_id == group_id,
            group_members.c.user_id == user_id,
        ),
    )
    result = await db.execute(stmt)
    return bool(result.scalar())


async def is_user_group_creator(
    db: AsyncSession,
    user_id: int,
    group_id: int,
) -> bool:
    """
    Проверяет, является ли пользователь создателем группы.

    Args:
        db: Сессия БД
        group_id: Уникальный идентификатор группы
        user_id: Уникальный идентификатор пользователя

    Returns:
        True, если пользователь является создателем группы, иначе False
    """
    stmt = select(
        exists().where(
            Group.id == group_id,
            Group.creator == user_id,
        ),
    )
    result = await db.execute(stmt)
    return bool(result.scalar())


async def is_wallet_attached_to_group(
    db: AsyncSession,
    group_id: int,
    wallet_id: int,
) -> bool:
    """
    Проверяет, прикреплен ли кошелек к группе.

    Args:
        db: Сессия БД
        group_id: Уникальный идентификатор группы
        wallet_id: Уникальный идентификатор кошелька

    Returns:
        True, если кошелек прикреплен к группе, иначе False
    """
    stmt = select(
        exists().where(
            group_wallets.c.group_id == group_id,
            group_wallets.c.wallet_id == wallet_id,
        ),
    )
    result = await db.execute(stmt)
    return bool(result.scalar())


async def remove_member_from_group(
    db: AsyncSession,
    group_id: int,
    user_id: int,
) -> None:
    """
    Удаляет пользователя из группы.

    Args:
        db: Сессия БД
        group_id: Уникальный идентификатор группы
        user_id: Уникальный идентификатор пользователя
    """
    await db.execute(
        group_members.delete().where(
            group_members.c.group_id == group_id,
            group_members.c.user_id == user_id,
        ),
    )
    await db.commit()


async def detach_user_wallets_from_group(
    db: AsyncSession,
    group_id: int,
    user_id: int,
) -> None:
    """
    Открепляет все кошельки пользователя от группы.

    Args:
        db: Сессия БД
        group_id: Уникальный идентификатор группы
        user_id: Уникальный идентификатор пользователя
    """
    # Получаем все кошельки пользователя
    user_wallets = await get_user_wallets(db, user_id)

    # Если у пользователя нет кошельков, ничего не делаем
    if not user_wallets:
        return

    # Получаем ID всех кошельков пользователя
    wallet_ids = [wallet.id for wallet in user_wallets]

    # Удаляем все связи кошельков пользователя с группой
    await db.execute(
        group_wallets.delete().where(
            group_wallets.c.group_id == group_id,
            group_wallets.c.wallet_id.in_(wallet_ids),
        ),
    )
    await db.commit()

