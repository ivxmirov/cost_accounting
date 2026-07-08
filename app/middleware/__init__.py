# Модуль middleware для FastAPI приложения
# Экспортируем все middleware компоненты для удобного импорта в main.py

# Импортируем компоненты обработки ошибок
from app.middleware.error_handler import (
    GenericExceptionMiddleware,  # Middleware для перехвата неперехваченных исключений
    http_exception_handler,  # Обработчик для HTTPException (400, 404, 403 и т.д.)
    validation_exception_handler,  # Обработчик для RequestValidationError (422)
)

# Импортируем middleware для добавления X-Request-ID
from app.middleware.request_id import RequestIDMiddleware

# Импортируем middleware для логирования запросов
from app.middleware.request_logging import RequestLoggingMiddleware

# Список экспортируемых компонентов (используется при импорте через "from app.middleware import *")
__all__ = [
    "GenericExceptionMiddleware",  # Middleware для обработки неперехваченных исключений
    "http_exception_handler",  # Handler для HTTP ошибок
    "validation_exception_handler",  # Handler для ошибок валидации
    "RequestIDMiddleware",  # Middleware для трейсинга через X-Request-ID
    "RequestLoggingMiddleware",  # Middleware для логирования запросов
]
