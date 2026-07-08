import uuid  # Для генерации уникальных идентификаторов UUID4

from starlette.middleware.base import BaseHTTPMiddleware  # Базовый класс для создания middleware
from starlette.requests import Request  # Тип для HTTP запроса


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware для добавления уникального идентификатора к каждому запросу"""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID")  # Получаем X-Request-ID из заголовка
        if not request_id:  # Если заголовок отсутствует
            request_id = str(uuid.uuid4())  # Генерируем новый UUID4

        request.state.request_id = request_id  # Сохраняем для доступа из других компонентов

        response = await call_next(request)  # Вызываем следующий middleware или endpoint

        response.headers["X-Request-ID"] = request_id  # Добавляем X-Request-ID в ответ

        return response  # Возвращаем ответ клиенту
