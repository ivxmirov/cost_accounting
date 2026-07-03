import uuid
from decimal import Decimal

import pytest

from app.models import Wallet


def test_income_idempotency(client, test_user, test_wallet, db, auth_headers):
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

    initial_balance = db.get(Wallet, test_wallet.id).balance

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

    final_balance = db.get(Wallet, test_wallet.id).balance
    assert final_balance == initial_balance


def test_expense_idempotency(client, test_user, test_wallet, db, auth_headers):
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

    initial_balance = db.get(Wallet, test_wallet.id).balance

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

    final_balance = db.get(Wallet, test_wallet.id).balance
    assert final_balance == initial_balance


@pytest.mark.asyncio
async def test_transfer_idempotency(client, test_user, db, mock_currency_api, auth_headers):
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
    db.commit()
    db.refresh(wallet1)
    db.refresh(wallet2)

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

    balance1_after_first = db.get(Wallet, wallet1.id).balance
    balance2_after_first = db.get(Wallet, wallet2.id).balance

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

    balance1_after_second = db.get(Wallet, wallet1.id).balance
    balance2_after_second = db.get(Wallet, wallet2.id).balance

    assert balance1_after_second == balance1_after_first
    assert balance2_after_second == balance2_after_first


def test_different_transaction_ids_create_separate_operations(
    client, test_user, test_wallet, db, auth_headers
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


def test_idempotency_preserves_wallet_balance(client, test_user, test_wallet, db, auth_headers):
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

    db.refresh(test_wallet)
    expected_balance = initial_balance + Decimal("200.0")  
    assert test_wallet.balance == expected_balance

