from typing import AsyncGenerator

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import User
from app.repository import users as users_repository
from app.utils.jwt import verify_token

security = HTTPBearer(auto_error=False)


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
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials

    # Декодируем токен и извлекаем логин
    try:
        payload = verify_token(token)
        login = payload.get("sub")
        if not login:
            raise HTTPException(status_code=401, detail="Invalid token: no subject")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Ищем пользователя по логину из токена
    user = await users_repository.get_user_by_login(db, login)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
