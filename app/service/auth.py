from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository import users as users_repository
from app.schemas import LoginRequest, RefreshRequest, TokenResponse
from app.utils.jwt import create_access_token, create_refresh_token, verify_token
from app.utils.password import verify_password


async def login(db: AsyncSession, request: LoginRequest) -> TokenResponse:
    """
    Аутентифицирует пользователя и возвращает JWT токены
    Args:
        db: Сессия базы данных
        request: Данные для входа (логин и пароль)
    Returns:
        JWT токены (access и refresh) для дальнейшей аутентификации
    Raises:
        HTTPException: Если логин или пароль неверны (401)
    """
    user = await users_repository.get_user_by_login(db, request.login)
    if (
        not user
        or not user.password_hash
        or not verify_password(request.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    token_data = {"sub": user.login}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=user.id,
        login=user.login,
    )


async def refresh_token(db: AsyncSession, request: RefreshRequest) -> TokenResponse:
    """
    Обновляет access токен используя refresh токен
    Args:
        db: Сессия базы данных
        request: Данные с refresh токеном
    Returns:
        Новый access токен и тот же refresh токен
    Raises:
        HTTPException: Если refresh токен невалидный или истек (401)
    """
    try:
        payload = verify_token(request.refresh_token)
        login = payload.get("sub")
        if not login:
            raise HTTPException(status_code=401, detail="Invalid token")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await users_repository.get_user_by_login(db, login)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    token_data = {"sub": user.login}
    new_access_token = create_access_token(data=token_data)
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=request.refresh_token,
        token_type="bearer",
        user_id=user.id,
        login=user.login,
    )
