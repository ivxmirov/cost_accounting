import logging  # Для создания логгера и логирования событий
import time  # Для измерения времени выполнения запроса

from starlette.middleware.base import BaseHTTPMiddleware  # Базовый класс для middleware
from starlette.requests import Request  # Тип для HTTP запроса

logger = logging.getLogger(__name__)  # Создаем logger для этого модуля


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования метаданных каждого HTTP-запроса"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()  # Засекаем время начала обработки запроса

        request_id = getattr(request.state, "request_id", "unknown")  # Получаем request_id

        query_params = dict(request.query_params)  # Получаем query параметры как словарь

        response = await call_next(request)  # Вызываем следующий middleware или endpoint

        duration = (time.time() - start_time) * 1000  # Вычисляем время выполнения в мс

        logger.info(  # Логируем метаданные запроса
            f"{request.method} {request.url.path} | query={query_params} "
            f"| request_id={request_id} | time={duration:.2f}ms"
        )

        return response  # Возвращаем ответ клиенту
