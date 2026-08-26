from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Создает JWT access токен для аутентификации пользователя

    Args:
        data: Данные для включения в токен (обычно {"sub": "username"})
        expires_delta: Пользовательское время жизни токена (опционально)

    Returns:
        Подписанный JWT токен в виде строки
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Создает JWT refresh токен для обновления access токена

    Args:
        data: Данные для включения в токен (обычно {"sub": "username"})

    Returns:
        Подписанный JWT refresh токен в виде строки
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> dict:
    """
    Верифицирует JWT токен и извлекает данные

    Args:
        token: JWT токен для проверки

    Returns:
        Payload токена (словарь с данными пользователя)

    Raises:
        ValueError: Если токен невалидный или истек
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
