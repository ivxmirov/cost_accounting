from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from app.api.v1.auth import router as auth_router
from app.api.v1.operations import router as operations_router
from app.api.v1.users import router as users_router
from app.api.v1.wallets import router as wallet_router
from app.api.v2.groups import router as groups_v2_router
from app.api.v2.operations import router as operations_v2_router
from app.api.v2.users import router as users_v2_router
from app.api.v2.wallets import router as wallets_v2_router
from app.middleware.error_handler import (
    GenericExceptionMiddleware,
    http_exception_handler,
    validation_exception_handler,
)
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware

app = FastAPI()

app.add_middleware(GenericExceptionMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(wallet_router, prefix="/api/v1", tags=["wallet"])
app.include_router(operations_router, prefix="/api/v1", tags=["operations"])
app.include_router(users_router, prefix="/api/v1", tags=["users"])
app.include_router(operations_v2_router, prefix="/api/v2", tags=["operations-v2"])
app.include_router(groups_v2_router, prefix="/api/v2", tags=["groups-v2"])
app.include_router(users_v2_router, prefix="/api/v2", tags=["users-v2"])
app.include_router(wallets_v2_router, prefix="/api/v2", tags=["wallets-v2"])

app.mount("/static", StaticFiles(directory="app/static"), name="static")
