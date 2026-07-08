from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest
import pytest_asyncio
from aioresponses import aioresponses
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.dependency import get_db
from app.enum import CurrencyEnum
from app.models import User, Wallet
from app.utils.jwt import create_access_token
from app.utils.password import hash_password
from main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_test_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


app.dependency_overrides[get_db] = get_test_db


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as db:
        yield db


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    password_hash = hash_password("testpassword")
    user = User(login="testuser", password_hash=password_hash)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def current_user(test_user):
    return test_user


@pytest.fixture
def auth_headers(test_user):
    access_token = create_access_token(data={"sub": test_user.login})
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def wallet(db_session: AsyncSession, test_user):
    wallet_obj = Wallet(
        name="test_wallet",
        balance=Decimal(1000),
        user_id=test_user.id,
        currency=CurrencyEnum.USD,
    )
    db_session.add(wallet_obj)
    await db_session.commit()
    await db_session.refresh(wallet_obj)
    return wallet_obj


@pytest.fixture
def test_wallet(wallet):
    return wallet


@pytest.fixture
def db(db_session):
    return db_session


@pytest.fixture
def mock_currency_api():
    with aioresponses() as m:
        m.get(
            "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json",
            payload={"date": "2025-01-01", "usd": {"eur": 0.9, "rub": 95.0}},
        )
        m.get(
            "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/eur.json",
            payload={"date": "2025-01-01", "eur": {"usd": 1.1, "rub": 103.0}},
        )
        m.get(
            "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/rub.json",
            status=500,
        )
        yield m
