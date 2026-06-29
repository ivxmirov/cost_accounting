from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.operations import router as operations_router
from app.api.v1.users import router as users_router
from app.api.v1.wallets import router as wallets_router
from app.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # При запуске — ничего не делаем (миграции через Alembic)
    yield
    # При завершении — закрываем соединения
    await engine.dispose()

app = FastAPI()

app.include_router(operations_router, prefix="/api/v1", tags=["operations"])
app.include_router(wallets_router, prefix="/api/v1", tags=["wallets"])
app.include_router(users_router, prefix="/api/v1", tags=["users"])

app.mount("/static", StaticFiles(directory="app/static"), name="static")
