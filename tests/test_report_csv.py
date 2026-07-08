from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from app.enum import CurrencyEnum
from app.models import Operation


async def test_report_csv_format(client, test_user, test_wallet, db, auth_headers, mock_currency_api):
    """CSV отчёт должен иметь правильный формат с заголовками."""
    operation = Operation(
        wallet_id=test_wallet.id,
        type="income",
        amount=Decimal("500.0"),
        currency=CurrencyEnum.USD,
        category="Test income",
        transaction_id=uuid4(),
        created_at=datetime(2024, 6, 15, 12, 0, 0),
    )
    db.add(operation)
    await db.commit()

    response = client.get(
        "/api/v1/reports",
        params={
            "date_from": "2024-06-01",
            "date_to": "2024-06-30",
            "currency": "USD",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"

    lines = response.text.strip().split("\n")
    assert len(lines) >= 1
    assert lines[0] == "date,type,wallet_id,amount,category,currency"


async def test_report_csv_content(client, test_user, test_wallet, db, auth_headers, mock_currency_api):
    """CSV отчёт должен содержать правильные данные операций."""
    operation1 = Operation(
        wallet_id=test_wallet.id,
        type="income",
        amount=Decimal("500.0"),
        currency=CurrencyEnum.USD,
        category="Salary",
        transaction_id=uuid4(),
        created_at=datetime(2024, 6, 15, 12, 0, 0),
    )
    operation2 = Operation(
        wallet_id=test_wallet.id,
        type="expense",
        amount=Decimal("100.0"),
        currency=CurrencyEnum.USD,
        category="Food",
        transaction_id=uuid4(),
        created_at=datetime(2024, 6, 16, 14, 30, 0),
    )
    db.add(operation1)
    db.add(operation2)
    await db.commit()

    response = client.get(
        "/api/v1/reports",
        params={
            "date_from": "2024-06-01",
            "date_to": "2024-06-30",
            "currency": "USD",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    assert len(lines) == 3

    assert "2024-06-15 12:00:00,income," in lines[1]
    assert "500.00" in lines[1]
    assert "Salary" in lines[1]
    assert "USD" in lines[1]

    assert "2024-06-16 14:30:00,expense," in lines[2]
    assert "100.00" in lines[2]
    assert "Food" in lines[2]
    assert "USD" in lines[2]


async def test_report_csv_download_headers(
    client, test_user, test_wallet, db, auth_headers, mock_currency_api
):
    """CSV отчёт должен иметь заголовки для скачивания файла."""
    operation = Operation(
        wallet_id=test_wallet.id,
        type="income",
        amount=Decimal("500.0"),
        currency=CurrencyEnum.USD,
        transaction_id=uuid4(),
        created_at=datetime(2024, 6, 15, 12, 0, 0),
    )
    db.add(operation)
    await db.commit()

    date_from = "2024-06-01"
    date_to = "2024-06-30"

    response = client.get(
        "/api/v1/reports",
        params={
            "date_from": date_from,
            "date_to": date_to,
            "currency": "USD",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "content-disposition" in response.headers
    assert "attachment" in response.headers["content-disposition"]
    assert "filename=report_" in response.headers["content-disposition"]
    assert ".csv" in response.headers["content-disposition"]


async def test_report_csv_with_multiple_operations(
    client, test_user, test_wallet, db, auth_headers, mock_currency_api
):
    """CSV отчёт с несколькими операциями должен содержать все данные."""
    operations = [
        Operation(
            wallet_id=test_wallet.id,
            type="income",
            amount=Decimal("1000.0"),
            currency=CurrencyEnum.USD,
            category="Salary June",
            transaction_id=uuid4(),
            created_at=datetime(2024, 6, 1, 10, 0, 0),
        ),
        Operation(
            wallet_id=test_wallet.id,
            type="expense",
            amount=Decimal("50.0"),
            currency=CurrencyEnum.USD,
            category="Food",
            transaction_id=uuid4(),
            created_at=datetime(2024, 6, 5, 12, 30, 0),
        ),
        Operation(
            wallet_id=test_wallet.id,
            type="expense",
            amount=Decimal("200.0"),
            currency=CurrencyEnum.USD,
            category="Transport",
            transaction_id=uuid4(),
            created_at=datetime(2024, 6, 10, 15, 0, 0),
        ),
        Operation(
            wallet_id=test_wallet.id,
            type="income",
            amount=Decimal("100.0"),
            currency=CurrencyEnum.USD,
            category="Freelance",
            transaction_id=uuid4(),
            created_at=datetime(2024, 6, 20, 18, 0, 0),
        ),
    ]

    for op in operations:
        db.add(op)
    await db.commit()

    response = client.get(
        "/api/v1/reports",
        params={
            "date_from": "2024-06-01",
            "date_to": "2024-06-30",
            "currency": "USD",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    assert len(lines) == 5


async def test_report_csv_empty(client, test_user, test_wallet, db, auth_headers, mock_currency_api):
    """Пустой CSV отчёт должен содержать только заголовки."""
    response = client.get(
        "/api/v1/reports",
        params={
            "date_from": "2024-06-01",
            "date_to": "2024-06-30",
            "currency": "USD",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    assert len(lines) == 1
    assert lines[0] == "date,type,wallet_id,amount,category,currency"


async def test_report_csv_special_characters(
    client, test_user, test_wallet, db, auth_headers, mock_currency_api
):
    """CSV должен правильно обрабатывать спецсимволы в категории."""
    operation = Operation(
        wallet_id=test_wallet.id,
        type="expense",
        amount=Decimal("50.0"),
        currency=CurrencyEnum.USD,
        category="Food, Groceries",
        transaction_id=uuid4(),
        created_at=datetime(2024, 6, 15, 12, 0, 0),
    )
    db.add(operation)
    await db.commit()

    response = client.get(
        "/api/v1/reports",
        params={
            "date_from": "2024-06-01",
            "date_to": "2024-06-30",
            "currency": "USD",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    assert "Food, Groceries" in lines[1]


async def test_report_csv_currency_conversion(
    client, test_user, test_wallet, db, auth_headers, mock_currency_api
):
    """CSV отчёт должен конвертировать валюты правильно."""
    operation = Operation(
        wallet_id=test_wallet.id,
        type="income",
        amount=Decimal("100.0"),
        currency=CurrencyEnum.USD,
        category="Salary",
        transaction_id=uuid4(),
        created_at=datetime(2024, 6, 15, 12, 0, 0),
    )
    db.add(operation)
    await db.commit()

    response = client.get(
        "/api/v1/reports",
        params={
            "date_from": "2024-06-01",
            "date_to": "2024-06-30",
            "currency": "RUB",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    assert "9500.00" in lines[1]
    assert "RUB" in lines[1]


async def test_report_csv_empty_category(
    client, test_user, test_wallet, db, auth_headers, mock_currency_api
):
    """CSV отчёт должен правильно обрабатывать пустые категории."""
    operation = Operation(
        wallet_id=test_wallet.id,
        type="income",
        amount=Decimal("500.0"),
        currency=CurrencyEnum.USD,
        category=None,
        transaction_id=uuid4(),
        created_at=datetime(2024, 6, 15, 12, 0, 0),
    )
    db.add(operation)
    await db.commit()

    response = client.get(
        "/api/v1/reports",
        params={
            "date_from": "2024-06-01",
            "date_to": "2024-06-30",
            "currency": "USD",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    assert len(lines) == 2
    assert lines[1].endswith(",USD") or ",," in lines[1]
