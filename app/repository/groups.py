from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Group, User


async def is_group_exist(db: AsyncSession, user_id: int, group_name: str) -> bool:
    """Проверяет существование группы с таким именем у пользователя, который ее создает"""
    result = await db.execute(
        select(Group).where(Group.name == group_name, Group.creator == user_id)
    )
    return result.scalar_one_or_none() is not None


async def create_group(
    db: AsyncSession, creator_id: int, group_name: str, members: list[User]
) -> Group:
    """
    Создаёт группу и добавляет админа как участника.

    Args:
        db: Асинхронная сессия БД
        creator_id: ID пользователя-админа
        group_name: Название группы

    Returns:
        Созданная группа с загруженными участниками
    """
    # Получаем создателя
    creator = await db.get(User, creator_id)
    group = Group(name=group_name, creator=creator_id)
    group.members.append(creator)  # ty: ignore[invalid-argument-type]  # pyright: ignore[reportArgumentType]

    for member in members:
        group.members.append(member)

    db.add(group)
    await db.flush()

    print(f"Members before select: {group.members}")  # Может вызвать ошибку!

    # Загружаем с отношениями
    result = await db.execute(
        select(Group).options(selectinload(Group.members)).where(Group.id == group.id)
    )
    return result.scalar_one()


# async def get_group_by_id(db: AsyncSession, user_id: int, group_id: int) -> Group | None:
#     result = await db.execute(
#         select(Group).where(Group.id == group_id, Group.user_id == user_id)
#     )
#     return result.scalar_one_or_none()
