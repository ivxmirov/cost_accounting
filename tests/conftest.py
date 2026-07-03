from decimal import Decimal
from typing import Generator

import pytest
from aioresponses import aioresponses
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.dependency import get_db
from app.enum import CurrencyEnum
from app.models import User, Wallet
from app.utils.jwt import create_access_token
from app.utils.password import hash_password
from main import app


TEST_DATABASE_URL = "sqlite:///./test.db"



test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)




TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)



def get_test_db() -> Generator[Session, None, None]:
    
    db = TestSessionLocal()
    try:
        
        yield db
    finally:
        
        db.close()



app.dependency_overrides[get_db] = get_test_db


@pytest.fixture()
def client():
    
    yield TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    
    Base.metadata.create_all(bind=test_engine)
    yield
    
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    
    db = TestSessionLocal()
    try:
        
        yield db
    finally:
        
        db.close()


@pytest.fixture
def test_user(db_session):
    
    password_hash = hash_password("testpassword")  
    user = User(login="testuser", password_hash=password_hash)  
    db_session.add(user)  
    db_session.commit()  
    db_session.refresh(user)  
    return user  


@pytest.fixture
def current_user(test_user):
    """
    Alias для test_user для обратной совместимости со старыми тестами

    Args:
        test_user: Тестовый пользователь

    Returns:
        Тот же объект test_user
    """
    return test_user


@pytest.fixture
def auth_headers(db_session, test_user):
    """
    Заголовки авторизации с JWT токеном для test_user

    Args:
        db_session: Сессия базы данных
        test_user: Тестовый пользователь (создается fixture test_user)

    Returns:
        Словарь с заголовками Authorization содержащими валидный JWT токен
    """
    
    access_token = create_access_token(data={"sub": test_user.login})
    
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def wallet(db_session, test_user):
    
    wallet = Wallet(
        name="test_wallet",  
        balance=Decimal(1000),  
        user_id=test_user.id,  
        currency=CurrencyEnum.USD,  
    )
    db_session.add(wallet)  
    db_session.commit()  
    db_session.refresh(wallet)  
    return wallet  


@pytest.fixture
def test_wallet(wallet):
    
    return wallet


@pytest.fixture
def db(db_session):
    
    return db_session


@pytest.fixture
def mock_currency_api():
    """Мокает внешний API курсов валют для E2E тестов."""
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
