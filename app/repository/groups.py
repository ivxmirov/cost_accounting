from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models import Group, User


async def is_group_exist(db: AsyncSession, user_id: int, group_name: str) -> bool:
    """Проверяет существование группы с таким именем у пользователя, который ее создает"""
    result = await db.execute(
        select(Group).where(Group.name == group_name, Group.creator == user_id),
    )
    return result.scalar_one_or_none() is not None


async def create_group(
    db: AsyncSession, creator_id: int, group_name: str, members: list[User],
) -> Group:
    """
    Создаёт группу и добавляет создателя как участника.

    Args:
        db: Асинхронная сессия БД
        creator_id: ID пользователя-админа
        group_name: Название группы

    Returns:
        Созданная группа с загруженными участниками
    """
    # Получаем создателя группы
    creator = await db.get(User, creator_id)
    group = Group(name=group_name, creator=creator_id)
    group.members.append(creator)  # ty: ignore[invalid-argument-type]  # pyright: ignore[reportArgumentType]

    for member in members:
        group.members.append(member)

    db.add(group)
    await db.flush()

    print(f"Members before select: {group.members}")

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
    """Получает группу по ID без проверки прав пользователя"""
    result = await db.execute(
        select(Group).where(Group.id == group_id).options(selectinload(Group.members)),
    )
    return result.scalar_one_or_none()
