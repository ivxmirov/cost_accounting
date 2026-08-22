import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Wallet


async def test_income_idempotency(client, test_user, test_wallet, db: AsyncSession, auth_headers):
    """
    Повторный запрос income с тем же transaction_id возвращает 200 OK с той же операцией.
    Баланс кошелька не должен измениться при повторном запросе.
    """
    transaction_id = str(uuid.uuid4())

    response1 = client.put(
        "/api/v1/operations/income",
        json={
            "transaction_id": transaction_id,
            "wallet_name": test_wallet.name,
            "amount": 500.0,
            "description": "First income",
        },
        headers=auth_headers,
    )
    assert response1.status_code == 201
    data1 = response1.json()
    assert data1["type"] == "income"
    assert data1["amount"] == "500.00"

    wallet = await db.get(Wallet, test_wallet.id)
    initial_balance = wallet.balance

    response2 = client.put(
        "/api/v1/operations/income",
        json={
            "transaction_id": transaction_id,
            "wallet_name": test_wallet.name,
            "amount": 500.0,
            "description": "First income",
        },
        headers=auth_headers,
    )
    assert response2.status_code == 200
    data2 = response2.json()

    assert data2["id"] == data1["id"]
    assert data2["type"] == data1["type"]
    assert data2["amount"] == data1["amount"]

    wallet = await db.get(Wallet, test_wallet.id)
    assert wallet.balance == initial_balance


async def test_expense_idempotency(client, test_user, test_wallet, db: AsyncSession, auth_headers):
    """
    Повторный запрос expense с тем же transaction_id возвращает 200 OK с той же операцией.
    Баланс кошелька не должен измениться при повторном запросе.
    """
    transaction_id = str(uuid.uuid4())

    response1 = client.put(
        "/api/v1/operations/expense",
        json={
            "transaction_id": transaction_id,
            "wallet_name": test_wallet.name,
            "amount": 100.0,
            "description": "First expense",
        },
        headers=auth_headers,
    )
    assert response1.status_code == 201
    data1 = response1.json()
    assert data1["type"] == "expense"
    assert data1["amount"] == "100.00"

    wallet = await db.get(Wallet, test_wallet.id)
    initial_balance = wallet.balance

    response2 = client.put(
        "/api/v1/operations/expense",
        json={
            "transaction_id": transaction_id,
            "wallet_name": test_wallet.name,
            "amount": 100.0,
            "description": "First expense",
        },
        headers=auth_headers,
    )
    assert response2.status_code == 200
    data2 = response2.json()

    assert data2["id"] == data1["id"]
    assert data2["type"] == data1["type"]
    assert data2["amount"] == data1["amount"]
    assert data2["category"] == data1["category"]

    wallet = await db.get(Wallet, test_wallet.id)
    assert wallet.balance == initial_balance


async def test_transfer_idempotency(
    client, test_user, db: AsyncSession, mock_currency_api, auth_headers
):
    """
    Повторный запрос transfer с тем же transaction_id возвращает 200 OK.
    Балансы кошельков не должны измениться при повторном запросе.
    """
    from app.enum import CurrencyEnum

    wallet1 = Wallet(
        user_id=test_user.id, name="USD Wallet", currency=CurrencyEnum.USD, balance=1000.0
    )
    wallet2 = Wallet(
        user_id=test_user.id, name="EUR Wallet", currency=CurrencyEnum.EUR, balance=0.0
    )
    db.add(wallet1)
    db.add(wallet2)
    await db.commit()
    await db.refresh(wallet1)
    await db.refresh(wallet2)

    transaction_id = str(uuid.uuid4())

    response1 = client.put(
        "/api/v1/operations/transfer",
        json={
            "transaction_id": transaction_id,
            "from_wallet_id": wallet1.id,
            "to_wallet_id": wallet2.id,
            "amount": 100.0,
        },
        headers=auth_headers,
    )
    assert response1.status_code == 201
    data1 = response1.json()
    assert data1["type"] == "transfer"

    wallet1_obj = await db.get(Wallet, wallet1.id)
    wallet2_obj = await db.get(Wallet, wallet2.id)
    balance1_after_first = wallet1_obj.balance
    balance2_after_first = wallet2_obj.balance

    response2 = client.put(
        "/api/v1/operations/transfer",
        json={
            "transaction_id": transaction_id,
            "from_wallet_id": wallet1.id,
            "to_wallet_id": wallet2.id,
            "amount": 100.0,
        },
        headers=auth_headers,
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["id"] == data1["id"]

    wallet1_obj = await db.get(Wallet, wallet1.id)
    wallet2_obj = await db.get(Wallet, wallet2.id)
    assert wallet1_obj.balance == balance1_after_first
    assert wallet2_obj.balance == balance2_after_first


def test_different_transaction_ids_create_separate_operations(
    client, test_user, test_wallet, auth_headers
):
    """
    Разные transaction_id должны создавать отдельные операции.
    Каждый запрос с уникальным transaction_id возвращает 201 Created.
    """
    response1 = client.put(
        "/api/v1/operations/income",
        json={
            "transaction_id": str(uuid.uuid4()),
            "wallet_name": test_wallet.name,
            "amount": 100.0,
            "description": "First income",
        },
        headers=auth_headers,
    )
    assert response1.status_code == 201

    response2 = client.put(
        "/api/v1/operations/income",
        json={
            "transaction_id": str(uuid.uuid4()),
            "wallet_name": test_wallet.name,
            "amount": 100.0,
            "description": "Second income",
        },
        headers=auth_headers,
    )
    assert response2.status_code == 201

    assert response1.json()["id"] != response2.json()["id"]


async def test_idempotency_preserves_wallet_balance(
    client, test_user, test_wallet, db: AsyncSession, auth_headers
):
    """
    Идемпотентность должна сохранять баланс кошелька при повторных запросах.
    Баланс должен увеличиться только один раз, несмотря на 3 одинаковых запроса.
    """
    transaction_id = str(uuid.uuid4())
    initial_balance = test_wallet.balance

    for _ in range(3):
        response = client.put(
            "/api/v1/operations/income",
            json={
                "transaction_id": transaction_id,
                "wallet_name": test_wallet.name,
                "amount": 200.0,
                "description": "Repeated income",
            },
            headers=auth_headers,
        )
        assert response.status_code in (200, 201)

    await db.refresh(test_wallet)
    expected_balance = initial_balance + Decimal("200.0")
    assert test_wallet.balance == expected_balance
