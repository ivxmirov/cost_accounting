from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository import users as users_repository
from app.schemas import UserResponseSchema
from app.utils.password import hash_password


async def get_all_users(db: AsyncSession) -> list[UserResponseSchema]:
    """
    Получение списка всех пользователей.

    Args:
        db: Сессия БД

    Returns:
        list[UserResponseSchema]: Список пользователей
    """
    users = await users_repository.get_all_users(db)

    return [UserResponseSchema.model_validate(user) for user in users]


async def create_user(db: AsyncSession, login: str, password: str) -> UserResponseSchema:
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
    if await users_repository.get_user_by_login(db, login):
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")
    password_hash = hash_password(password)
    user = await users_repository.create_user(db, login, password_hash)
    await db.commit()
    return UserResponseSchema.model_validate(user)


async def search_user_by_login(db: AsyncSession, login: str) -> UserResponseSchema | None:
    """
    Поиск пользователя по точному логину.

    Args:
        db: Сессия БД
        login: Логин пользователя

    Returns:
        UserResponseSchema | None: Схема пользователя или None
    """
    # Проверяем, что логин не пустой
    if not login or not login.strip():
        return None

    # Переиспользуем существующую функцию из репозитория
    user = await users_repository.get_user_by_login(db, login.strip())

    if not user:
        return None

    # Возвращаем схему пользователя
    return UserResponseSchema.model_validate(user)
