from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_all_users(db: AsyncSession) -> list[User]:
    """
    Получение списка всех пользователей.

    Args:
        db: Сессия БД

    Returns:
        list[User]: Список пользователей
    """
    result = await db.execute(select(User).order_by(User.login))
    return list(result.scalars().all())


async def get_user_by_login(db: AsyncSession, login: str) -> User | None:
    result = await db.execute(select(User).where(User.login == login))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, login: str, password_hash: str) -> User:
    user = User(login=login, password_hash=password_hash)
    db.add(user)
    await db.flush()
    return user
