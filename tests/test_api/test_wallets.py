from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.enum import CurrencyEnum
from app.models import Wallet


async def test_get_balance_total(client, auth_headers, current_user, db_session: AsyncSession):
    wallet1 = Wallet(
        name="wallet1", balance=Decimal("100"), user_id=current_user.id, currency=CurrencyEnum.RUB,
    )
    db_session.add(wallet1)

    wallet2 = Wallet(
        name="wallet2", balance=Decimal("200"), user_id=current_user.id, currency=CurrencyEnum.RUB,
    )
    db_session.add(wallet2)
    await db_session.commit()

    response = client.get("/api/v1/balance", headers=auth_headers)

    assert response.status_code == 200
    assert "total_balance" in response.json()
    assert float(response.json()["total_balance"]) == 300.0


def test_get_balance_total_empty(client, auth_headers):
    response = client.get("/api/v1/balance", headers=auth_headers)

    assert response.status_code == 200
    assert "total_balance" in response.json()
    assert float(response.json()["total_balance"]) == 0.0


async def test_get_balance_by_name(client, auth_headers, wallet, db_session: AsyncSession):
    wallet.balance = Decimal("150")
    await db_session.commit()
    await db_session.refresh(wallet)

    response = client.get("/api/v1/balance", headers=auth_headers)

    assert response.status_code == 200
    assert "total_balance" in response.json()


def test_get_balance_not_exists(client, auth_headers):
    response = client.get("/api/v1/balance", headers=auth_headers)

    assert response.status_code == 200


def test_get_balance_unauthorized(client):
    response = client.get("/api/v1/balance")

    assert response.status_code == 401


def test_create_wallet_success(client, auth_headers):
    response = client.post(
        "/api/v1/wallets",
        json={"name": "my_wallet", "initial_balance": 100.0},
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["name"] == "my_wallet"
    assert Decimal(str(response.json()["balance"])) == Decimal("100")


def test_create_wallet_exists(client, auth_headers, wallet):
    response = client.post(
        "/api/v1/wallets",
        json={"name": wallet.name, "initial_balance": 100.0},
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_create_wallet_unauthorized(client):
    response = client.post("/api/v1/wallets", json={"name": "my_wallet", "initial_balance": 100.0})

    assert response.status_code == 401
