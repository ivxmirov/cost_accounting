from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository import users as users_repository
from app.schemas import UserResponse
from app.utils.password import hash_password


async def create_user(db: AsyncSession, login: str, password: str) -> UserResponse:
    """
    Создает нового пользователя с проверкой на дубликаты и хешированием пароля
    Args:
        db: Сессия базы данных
        login: Логин нового пользователя
        password: Пароль пользователя в открытом виде (опционально для обратной совместимости)
    Returns:
        Информация о созданном пользователе
    Raises:
        HTTPException: Если пользователь с таким логином уже существует
    """
    if await users_repository.get_user(db, login):
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")
    password_hash = hash_password(password)
    user = await users_repository.create_user(db, login, password_hash)
    await db.commit()
    return UserResponse.model_validate(user)
