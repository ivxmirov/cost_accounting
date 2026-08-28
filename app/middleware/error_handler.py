from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class GenericExceptionMiddleware(BaseHTTPMiddleware):
    """Middleware для перехвата всех неперехваченных исключений"""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except HTTPException:
            raise
        except Exception:
            return JSONResponse(
                status_code=500,
                content={"code": "500", "message": "Internal server error", "details": None},
            )


async def http_exception_handler(request: Request, exc: HTTPException | Exception) -> JSONResponse:
    """
    Обработчик для HTTPException (400, 404, 403 и т.д.)

    Преобразует HTTPException в стандартизированный формат ответа.
    Если detail - словарь с ключом message, извлекает message и остальные поля в details.
    Если detail - строка, использует её как message.

    Args:
        request: HTTP запрос
        exc: Исключение HTTPException

    Returns:
        JSON ответ со стандартизированным форматом ошибки
    """
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        detail = exc.detail

        if isinstance(detail, dict):
            message = detail.get("message")
            temp_details = {k: v for k, v in detail.items() if k != "message"}
            details = temp_details if temp_details else None
        else:
            message = detail
            details = None

        return JSONResponse(
            status_code=status_code,
            content={"code": str(status_code), "message": message, "details": details},
        )

    return JSONResponse(
        status_code=500,
        content={"code": "500", "message": "Internal server error", "details": None},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError | Exception,
) -> JSONResponse:
    """
    Обработчик для RequestValidationError (422)

    Преобразует ошибки валидации Pydantic в стандартизированный формат.
    Извлекает понятное сообщение об ошибке из ValueError валидаторов.

    Args:
        request: HTTP запрос
        exc: Исключение RequestValidationError

    Returns:
        JSON ответ со стандартизированным форматом ошибки валидации
    """
    if isinstance(exc, RequestValidationError):
        errors = exc.errors()

        # Извлекаем первое сообщение об ошибке
        error_message = "Validation error"

        if errors:
            first_error = errors[0]
            msg = first_error.get("msg", "")

            # Убираем технический префикс "Value error, "
            if msg.startswith("Value error, "):
                error_message = msg.replace("Value error, ", "", 1)
            else:
                # Для других типов ошибок валидации
                field = first_error.get("loc", ["unknown"])[-1] if first_error.get("loc") else "unknown"
                error_type = first_error.get("type", "")

                # Создаем понятные сообщения для разных типов ошибок
                if error_type == "missing":
                    error_message = f"Поле '{field}' обязательно для заполнения"
                elif error_type == "string_too_long":
                    error_message = f"Поле '{field}' слишком длинное"
                elif error_type == "enum":
                    error_message = f"Поле '{field}' имеет недопустимое значение"
                else:
                    error_message = msg

        # Создаем упрощенные детали для отладки
        details = [{k: v for k, v in err.items() if k != "ctx"} for err in errors]

        return JSONResponse(
            status_code=400,  # Меняем 422 на 400 для бизнес-ошибок
            content={
                "detail": error_message,  # Добавляем detail для совместимости с фронтендом
                "code": "400",
                "message": error_message,
                "details": details,
            },
        )

    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "code": "422",
            "message": "Validation error",
            "details": None,
        },
    )
