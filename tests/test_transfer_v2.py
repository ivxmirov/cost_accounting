from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.enum import CurrencyEnum
from app.models import Wallet


async def test_transfer_v2_with_custom_amount_success(
    client, test_user, db: AsyncSession, auth_headers,
):
    """v2: Перевод с кастомной суммой получения успешно выполняется."""
    wallet1 = Wallet(
        user_id=test_user.id,
        name="RUB Wallet",
        currency=CurrencyEnum.RUB,
        balance=Decimal("10000.0"),
    )
    wallet2 = Wallet(
        user_id=test_user.id, name="USD Wallet", currency=CurrencyEnum.USD, balance=Decimal("0.0"),
    )
    db.add(wallet1)
    db.add(wallet2)
    await db.commit()
    await db.refresh(wallet1)
    await db.refresh(wallet2)

    response = client.put(
        "/api/v2/operations/transfer",
        json={
            "transaction_id": str(uuid4()),
            "from_wallet_id": wallet1.id,
            "to_wallet_id": wallet2.id,
            "amount": "10000.0",
            "received_amount": "100.0",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert float(data["from_wallet"]["balance"]) == 0.0
    assert float(data["to_wallet"]["balance"]) == 100.0
    assert data["transferred_amount"] == "10000.00"
    assert data["received_amount"] == "100.00"
    assert data["exchange_rate"] == 0.01


async def test_transfer_v2_without_custom_amount_fallback_to_v1(
    client, test_user, db: AsyncSession, mock_currency_api, auth_headers,
):
    """v2: Перевод без кастомной суммы работает как v1 (автоконверсия)."""
    wallet1 = Wallet(
        user_id=test_user.id,
        name="USD Wallet",
        currency=CurrencyEnum.USD,
        balance=Decimal("1000.0"),
    )
    wallet2 = Wallet(
        user_id=test_user.id, name="EUR Wallet", currency=CurrencyEnum.EUR, balance=Decimal("0.0"),
    )
    db.add(wallet1)
    db.add(wallet2)
    await db.commit()
    await db.refresh(wallet1)
    await db.refresh(wallet2)

    response = client.put(
        "/api/v2/operations/transfer",
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
    assert data["success"] is True
    assert float(data["from_wallet"]["balance"]) == 900.0
    assert float(data["to_wallet"]["balance"]) > 0


async def test_transfer_v2_custom_amount_same_currency(
    client, test_user, db: AsyncSession, auth_headers,
):
    """v2: Перевод с кастомной суммой между кошельками с одинаковой валютой."""
    wallet1 = Wallet(
        user_id=test_user.id, name="Wallet 1", currency=CurrencyEnum.USD, balance=Decimal("500.0"),
    )
    wallet2 = Wallet(
        user_id=test_user.id, name="Wallet 2", currency=CurrencyEnum.USD, balance=Decimal("200.0"),
    )
    db.add(wallet1)
    db.add(wallet2)
    await db.commit()
    await db.refresh(wallet1)
    await db.refresh(wallet2)

    response = client.put(
        "/api/v2/operations/transfer",
        json={
            "transaction_id": str(uuid4()),
            "from_wallet_id": wallet1.id,
            "to_wallet_id": wallet2.id,
            "amount": "100.0",
            "received_amount": "95.0",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert float(data["from_wallet"]["balance"]) == 400.0
    assert float(data["to_wallet"]["balance"]) == 295.0
    assert data["exchange_rate"] == 0.95


async def test_transfer_v2_custom_amount_insufficient_funds(
    client, test_user, db: AsyncSession, auth_headers,
):
    """v2: Перевод с кастомной суммой при недостатке средств — 400."""
    wallet1 = Wallet(
        user_id=test_user.id, name="Wallet 1", currency=CurrencyEnum.USD, balance=Decimal("50.0"),
    )
    wallet2 = Wallet(
        user_id=test_user.id, name="Wallet 2", currency=CurrencyEnum.USD, balance=Decimal("0.0"),
    )
    db.add(wallet1)
    db.add(wallet2)
    await db.commit()
    await db.refresh(wallet1)
    await db.refresh(wallet2)

    response = client.put(
        "/api/v2/operations/transfer",
        json={
            "transaction_id": str(uuid4()),
            "from_wallet_id": wallet1.id,
            "to_wallet_id": wallet2.id,
            "amount": "100.0",
            "received_amount": "95.0",
        },
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_transfer_v2_custom_amount_wallet_not_found(client, test_user, auth_headers):
    """v2: Перевод при несуществующем кошельке — 404."""
    response = client.put(
        "/api/v2/operations/transfer",
        json={
            "transaction_id": str(uuid4()),
            "from_wallet_id": 111111,
            "to_wallet_id": 222222,
            "amount": "10.0",
            "received_amount": "9.5",
        },
        headers=auth_headers,
    )
    assert response.status_code in (404, 422)


def test_transfer_v2_custom_amount_same_wallet(client, test_user, test_wallet, auth_headers):
    """v2: Перевод в тот же кошелёк недопустим — 422."""
    response = client.put(
        "/api/v2/operations/transfer",
        json={
            "transaction_id": str(uuid4()),
            "from_wallet_id": test_wallet.id,
            "to_wallet_id": test_wallet.id,
            "amount": "100.0",
            "received_amount": "95.0",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_transfer_v2_implied_rate_calculation(
    client, test_user, db: AsyncSession, auth_headers,
):
    """v2: Проверка расчета implied exchange rate."""
    wallet1 = Wallet(
        user_id=test_user.id,
        name="RUB Wallet",
        currency=CurrencyEnum.RUB,
        balance=Decimal("10000.0"),
    )
    wallet2 = Wallet(
        user_id=test_user.id, name="EUR Wallet", currency=CurrencyEnum.EUR, balance=Decimal("0.0"),
    )
    db.add(wallet1)
    db.add(wallet2)
    await db.commit()
    await db.refresh(wallet1)
    await db.refresh(wallet2)

    response = client.put(
        "/api/v2/operations/transfer",
        json={
            "transaction_id": str(uuid4()),
            "from_wallet_id": wallet1.id,
            "to_wallet_id": wallet2.id,
            "amount": "10000.0",
            "received_amount": "95.5",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["transferred_amount"] == "10000.00"
    assert data["received_amount"] == "95.50"
    expected_rate = round(95.5 / 10000.0, 6)
    assert abs(data["exchange_rate"] - expected_rate) < 0.000001


async def test_transfer_v2_idempotency(client, test_user, db: AsyncSession, auth_headers):
    """v2: Повторный запрос с тем же transaction_id возвращает 200."""
    wallet1 = Wallet(
        user_id=test_user.id, name="Wallet 1", currency=CurrencyEnum.USD, balance=Decimal("1000.0"),
    )
    wallet2 = Wallet(
        user_id=test_user.id, name="Wallet 2", currency=CurrencyEnum.EUR, balance=Decimal("0.0"),
    )
    db.add(wallet1)
    db.add(wallet2)
    await db.commit()
    await db.refresh(wallet1)
    await db.refresh(wallet2)

    transaction_id = str(uuid4())

    response1 = client.put(
        "/api/v2/operations/transfer",
        json={
            "transaction_id": transaction_id,
            "from_wallet_id": wallet1.id,
            "to_wallet_id": wallet2.id,
            "amount": "100.0",
            "received_amount": "85.0",
        },
        headers=auth_headers,
    )
    assert response1.status_code == 201

    response2 = client.put(
        "/api/v2/operations/transfer",
        json={
            "transaction_id": transaction_id,
            "from_wallet_id": wallet1.id,
            "to_wallet_id": wallet2.id,
            "amount": "100.0",
            "received_amount": "85.0",
        },
        headers=auth_headers,
    )
    assert response2.status_code == 200
    data = response2.json()
    assert data["success"] is True


async def test_transfer_v2_empty_custom_amount_works_as_v1(
    client, test_user, db: AsyncSession, auth_headers,
):
    """v2: Перевод с пустой кастомной суммой между одинаковыми валютами."""
    wallet1 = Wallet(
        user_id=test_user.id, name="Wallet 1", currency=CurrencyEnum.USD, balance=Decimal("500.0"),
    )
    wallet2 = Wallet(
        user_id=test_user.id, name="Wallet 2", currency=CurrencyEnum.USD, balance=Decimal("200.0"),
    )
    db.add(wallet1)
    db.add(wallet2)
    await db.commit()
    await db.refresh(wallet1)
    await db.refresh(wallet2)

    response = client.put(
        "/api/v2/operations/transfer",
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
    assert data["success"] is True
    assert float(data["from_wallet"]["balance"]) == 350.0
    assert float(data["to_wallet"]["balance"]) == 350.0
    assert data["exchange_rate"] == 1.0
