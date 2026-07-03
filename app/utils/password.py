# Импортируем модуль hashlib для хеширования паролей
import hashlib


def hash_password(password: str) -> str:
    """
    Хеширует пароль с использованием алгоритма SHA-256

    Args:
        password: Пароль в открытом виде (строка)

    Returns:
        Хеш пароля в виде строки из 64 символов (hexadecimal)
    """
    # Преобразуем строку пароля в байты (encode())
    # Применяем алгоритм SHA-256 для хеширования
    # Преобразуем результат в строку шестнадцатеричных символов (hexdigest())
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет соответствие пароля его хешу

    Args:
        plain_password: Пароль в открытом виде для проверки
        hashed_password: Сохраненный хеш пароля из базы данных

    Returns:
        True если пароль верный, False если неверный
    """
    # Хешируем введенный пароль и сравниваем с сохраненным хешем
    return hash_password(plain_password) == hashed_password
