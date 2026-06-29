from typing import AsyncGenerator
from urllib.parse import unquote

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import User
from app.repository import users as users_repository

security = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    login = unquote(credentials.credentials)
    user = await users_repository.get_user(db, login)

    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return user
