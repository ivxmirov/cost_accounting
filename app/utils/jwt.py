# Импортируем классы для работы с датой и временем (с поддержкой временных зон)
from datetime import datetime, timedelta, timezone

# Импортируем библиотеку для работы с JWT токенами
import jwt

# Импортируем настройки приложения (секретный ключ, алгоритм, время жизни токенов)
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
    # Копируем данные чтобы не изменить оригинальный словарь
    to_encode = data.copy()
    # Вычисляем время истечения токена
    if expires_delta:
        # Если передано пользовательское время - используем его
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Иначе используем настройку по умолчанию из конфигурации
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    # Добавляем время истечения в payload токена (поле "exp")
    to_encode.update({"exp": expire})
    # Кодируем данные в JWT токен используя секретный ключ и алгоритм
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Создает JWT refresh токен для обновления access токена

    Args:
        data: Данные для включения в токен (обычно {"sub": "username"})

    Returns:
        Подписанный JWT refresh токен в виде строки
    """
    # Копируем данные чтобы не изменить оригинальный словарь
    to_encode = data.copy()
    # Вычисляем время истечения refresh токена (больше чем у access)
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    # Добавляем время истечения в payload токена
    to_encode.update({"exp": expire})
    # Кодируем данные в JWT токен
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
        # Пытаемся декодировать токен используя секретный ключ и алгоритм
        # algorithms=[settings.ALGORITHM] - явно указываем разрешенные алгоритмы для безопасности
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Возвращаем извлеченные данные из токена
        return payload
    except jwt.ExpiredSignatureError:
        # Если токен истек - выбрасываем исключение с понятным сообщением
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        # Если токен невалидный (подделан, неверный формат и т.д.)
        raise ValueError("Invalid token")
