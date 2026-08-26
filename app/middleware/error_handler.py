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
    Удаляет поле ctx из каждой ошибки (может содержать несериализуемые объекты).

    Args:
        request: HTTP запрос
        exc: Исключение RequestValidationError

    Returns:
        JSON ответ со стандартизированным форматом ошибки валидации
    """
    if isinstance(exc, RequestValidationError):
        errors = exc.errors()

        details = [{k: v for k, v in err.items() if k != "ctx"} for err in errors]

        return JSONResponse(
            status_code=422,
            content={"code": "422", "message": "Validation error", "details": details},
        )

    return JSONResponse(
        status_code=422, content={"code": "422", "message": "Validation error", "details": None},
    )
