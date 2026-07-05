from decimal import Decimal
from uuid import uuid4

from app.enum import CurrencyEnum
from app.models import Wallet


async def test_transfer_v1_success(client, test_user, db, mock_currency_api, auth_headers):
    """v1: Перевод между кошельками должен успешно списать/зачислить средства."""
    wallet1 = Wallet(
        user_id=test_user.id,
        name="USD Wallet",
        currency=CurrencyEnum.USD,
        balance=Decimal("1000.0"),
    )
    wallet2 = Wallet(
        user_id=test_user.id, name="EUR Wallet", currency=CurrencyEnum.EUR, balance=Decimal("0.0")
    )
    db.add(wallet1)
    db.add(wallet2)
    db.commit()
    db.refresh(wallet1)
    db.refresh(wallet2)

    response = client.put(
        "/api/v1/operations/transfer",
        json={
            "transaction_id": str(uuid4()),
            "from_wallet_id": wallet1.id,
            "to_wallet_id": wallet2.id,
            "amount": "100.0",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()

    assert data["type"] == "transfer"
    assert data["wallet_id"] == wallet1.id

    db.refresh(wallet1)
    db.refresh(wallet2)
    assert float(wallet1.balance) == 900.0
    assert float(wallet2.balance) > 0


def test_transfer_v1_wallet_not_found(client, test_user, auth_headers):
    """v1: Перевод при несуществующем кошельке — 404."""
    response = client.put(
        "/api/v1/operations/transfer",
        json={
            "transaction_id": str(uuid4()),
            "from_wallet_id": 111111,
            "to_wallet_id": 222222,
            "amount": "10.0",
        },
        headers=auth_headers,
    )
    assert response.status_code in (404, 422)


def test_transfer_v1_insufficient_funds(client, test_user, db, auth_headers):
    """v1: Перевод при недостатке средств — 400."""
    wallet1 = Wallet(
        user_id=test_user.id, name="Wallet 1", currency=CurrencyEnum.USD, balance=Decimal("50.0")
    )
    wallet2 = Wallet(
        user_id=test_user.id, name="Wallet 2", currency=CurrencyEnum.USD, balance=Decimal("0.0")
    )
    db.add(wallet1)
    db.add(wallet2)
    db.commit()
    db.refresh(wallet1)
    db.refresh(wallet2)

    response = client.put(
        "/api/v1/operations/transfer",
        json={
            "transaction_id": str(uuid4()),
            "from_wallet_id": wallet1.id,
            "to_wallet_id": wallet2.id,
            "amount": "100.0",
        },
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_transfer_v1_same_wallet(client, test_user, test_wallet, auth_headers):
    """v1: Перевод в тот же кошелёк недопустим — FastAPI вернёт 422 (валидация)."""
    response = client.put(
        "/api/v1/operations/transfer",
        json={
            "transaction_id": str(uuid4()),
            "from_wallet_id": test_wallet.id,
            "to_wallet_id": test_wallet.id,
            "amount": "100.0",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_transfer_v1_same_currency(client, test_user, db, auth_headers):
    """v1: Перевод между кошельками с одной валютой."""
    wallet1 = Wallet(
        user_id=test_user.id, name="Wallet 1", currency=CurrencyEnum.USD, balance=Decimal("500.0")
    )
    wallet2 = Wallet(
        user_id=test_user.id, name="Wallet 2", currency=CurrencyEnum.USD, balance=Decimal("200.0")
    )
    db.add(wallet1)
    db.add(wallet2)
    db.commit()
    db.refresh(wallet1)
    db.refresh(wallet2)

    response = client.put(
        "/api/v1/operations/transfer",
        json={
            "transaction_id": str(uuid4()),
            "from_wallet_id": wallet1.id,
            "to_wallet_id": wallet2.id,
            "amount": "150.0",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()

    assert data["type"] == "transfer"

    db.refresh(wallet1)
    db.refresh(wallet2)
    assert float(wallet1.balance) == 350.0
    assert float(wallet2.balance) == 350.0


async def test_transfer_v1_idempotency(client, test_user, db, mock_currency_api, auth_headers):
    """v1: Повторный запрос с тем же transaction_id возвращает 200."""
    wallet1 = Wallet(
        user_id=test_user.id, name="Wallet 1", currency=CurrencyEnum.USD, balance=Decimal("1000.0")
    )
    wallet2 = Wallet(
        user_id=test_user.id, name="Wallet 2", currency=CurrencyEnum.EUR, balance=Decimal("0.0")
    )
    db.add(wallet1)
    db.add(wallet2)
    db.commit()
    db.refresh(wallet1)
    db.refresh(wallet2)

    transaction_id = str(uuid4())

    response1 = client.put(
        "/api/v1/operations/transfer",
        json={
            "transaction_id": transaction_id,
            "from_wallet_id": wallet1.id,
            "to_wallet_id": wallet2.id,
            "amount": "100.0",
        },
        headers=auth_headers,
    )
    assert response1.status_code == 201

    response2 = client.put(
        "/api/v1/operations/transfer",
        json={
            "transaction_id": transaction_id,
            "from_wallet_id": wallet1.id,
            "to_wallet_id": wallet2.id,
            "amount": "100.0",
        },
        headers=auth_headers,
    )
    assert response2.status_code == 200
    data = response2.json()

    assert data["type"] == "transfer"
