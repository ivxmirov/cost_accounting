from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository import users as users_repository
from app.schemas import UserResponse


async def create_user(db: AsyncSession, login: str) -> UserResponse:
    existing_user = await users_repository.get_user(db, login)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists.")

    user = await users_repository.create_user(db, login)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)
