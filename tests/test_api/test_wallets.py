from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum import CurrencyEnum, WalletType
from app.models import Wallet


async def test_get_balance_total(client, auth_headers, current_user, db_session: AsyncSession):
    wallet1 = Wallet(
        name="wallet1",
        balance=Decimal("100.46"),
        user_id=current_user.id,
        currency=CurrencyEnum.RUB,
        type=WalletType.DEBIT,
    )
    db_session.add(wallet1)

    wallet2 = Wallet(
        name="wallet2",
        balance=Decimal("200.39"),
        user_id=current_user.id,
        currency=CurrencyEnum.RUB,
        type=WalletType.CREDIT,
        credit_limit=Decimal("300"),
    )
    db_session.add(wallet2)
    await db_session.commit()

    response = client.get("/api/v1/balance", headers=auth_headers)

    assert response.status_code == 200
    assert "total_balance" in response.json()
    assert float(response.json()["total_balance"]) == 0.85


def test_get_balance_total_empty(client, auth_headers):
    response = client.get("/api/v1/balance", headers=auth_headers)

    assert response.status_code == 200
    assert "total_balance" in response.json()
    assert float(response.json()["total_balance"]) == 0.0


@pytest.mark.parametrize("wallet_type", ["debit", "credit"])
async def test_get_balance_by_name(
    client,
    auth_headers,
    wallet_factory,
    wallet_type: str,
    db_session: AsyncSession,
):
    wallet = await wallet_factory(wallet_type)
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


@pytest.mark.parametrize("wallet_type", ["debit", "credit"])
def test_create_wallet_success(client, auth_headers, wallet_type: str):
    wallet_name = f"my_wallet_{wallet_type}"
    response = client.post(
        "/api/v1/wallets",
        json={
            "name": wallet_name,
            "initial_balance": "100.5",
            "type": wallet_type,
            "credit_limit": "200" if wallet_type == WalletType.CREDIT else None,
        },
        headers=auth_headers,
    )

    response_data = response.json()
    assert response.status_code == 201
    assert response_data["name"] == wallet_name
    assert Decimal(str(response_data["balance"])) == Decimal("100.5")
    assert response_data["type"] == wallet_type
    if wallet_type == WalletType.CREDIT:
        assert Decimal(str(response_data["credit_limit"])) == Decimal("200")
    else:
        assert response_data["credit_limit"] is None


@pytest.mark.parametrize("wallet_type", ["debit", "credit"])
async def test_create_wallet_exists(client, auth_headers, wallet_factory, wallet_type: str):

    wallet = await wallet_factory(wallet_type)
    response = client.post(
        "/api/v1/wallets",
        json={
            "name": wallet.name,
            "initial_balance": "0",
            "type": wallet_type,
            "credit_limit": "100" if wallet_type == WalletType.CREDIT else None,
        },
        headers=auth_headers,
    )

    response_data = response.json()
    assert response.status_code == 400
    assert "уже существует" in response_data["message"]


@pytest.mark.parametrize("wallet_type", ["debit", "credit"])
def test_create_wallet_unauthorized(client, wallet_type: str):
    response = client.post(
        "/api/v1/wallets",
        json={
            "name": "my_wallet",
            "initial_balance": "100",
            "type": wallet_type,
            "credit_limit": "100" if wallet_type == WalletType.CREDIT else None,
        },
    )
    assert response.status_code == 401
