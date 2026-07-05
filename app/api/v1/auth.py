from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency import get_db
from app.schemas import LoginRequest, RefreshRequest, TokenResponse
from app.service import auth as auth_service

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Эндпоинт для входа в систему (аутентификации пользователя)
    Принимает логин и пароль, проверяет их корректность
    и возвращает JWT токены для дальнейшей работы с API
    Args:
        request: Данные для входа (логин и пароль)
        db: Сессия базы данных (внедряется автоматически)
    Returns:
        JWT токены (access и refresh) и тип токена
    """
    return await auth_service.login(db, request)


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Эндпоинт для обновления access токена
    Принимает refresh токен и возвращает новый access токен
    (refresh токен остается прежним)
    Args:
        request: Данные с refresh токеном
        db: Сессия базы данных (внедряется автоматически)
    Returns:
        Новый access токен и тот же refresh токен
    """
    return await auth_service.refresh_token(db, request)
