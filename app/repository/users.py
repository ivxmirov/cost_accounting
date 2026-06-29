from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_user(db: AsyncSession, login: str) -> User | None:
    result = await db.execute(select(User).filter(User.login == login))
    return result.scalars().first()


async def create_user(db: AsyncSession, login: str) -> User:
    user = User(login=login)
    db.add(user)
    await db.flush()
    return user
