from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from app.enum import CurrencyEnum
from app.models import Operation


async def test_report_csv_format(
    client,
    debit_wallet,
    db,
    auth_headers,
):
    """CSV отчёт должен иметь правильный формат с заголовками."""
    operation = Operation(
        wallet_id=debit_wallet.id,
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
        params={"date_from": "2024-06-01", "date_to": "2024-06-30", "currency": "USD"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"

    lines = response.text.strip().split("\n")
    assert len(lines) >= 1
    assert lines[0] == "date,type,wallet_id,amount,category,currency"


async def test_report_csv_content(
    client,
    debit_wallet,
    db,
    auth_headers,
):
    """CSV отчёт должен содержать правильные данные операций."""
    operation1 = Operation(
        wallet_id=debit_wallet.id,
        type="income",
        amount=Decimal("500.0"),
        currency=CurrencyEnum.USD,
        category="Salary",
        transaction_id=uuid4(),
        created_at=datetime(2024, 6, 15, 12, 0, 0),
    )
    operation2 = Operation(
        wallet_id=debit_wallet.id,
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
        params={"date_from": "2024-06-01", "date_to": "2024-06-30", "currency": "USD"},
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
    client,
    debit_wallet,
    db,
    auth_headers,
):
    """CSV отчёт должен иметь заголовки для скачивания файла."""
    operation = Operation(
        wallet_id=debit_wallet.id,
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
        params={"date_from": date_from, "date_to": date_to, "currency": "USD"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "content-disposition" in response.headers
    assert "attachment" in response.headers["content-disposition"]
    assert "filename=report_" in response.headers["content-disposition"]
    assert ".csv" in response.headers["content-disposition"]


async def test_report_csv_with_multiple_operations(
    client,
    debit_wallet,
    db,
    auth_headers,
):
    """CSV отчёт с несколькими операциями должен содержать все данные."""
    operations = [
        Operation(
            wallet_id=debit_wallet.id,
            type="income",
            amount=Decimal("1000.0"),
            currency=CurrencyEnum.USD,
            category="Salary June",
            transaction_id=uuid4(),
            created_at=datetime(2024, 6, 1, 10, 0, 0),
        ),
        Operation(
            wallet_id=debit_wallet.id,
            type="expense",
            amount=Decimal("50.0"),
            currency=CurrencyEnum.USD,
            category="Food",
            transaction_id=uuid4(),
            created_at=datetime(2024, 6, 5, 12, 30, 0),
        ),
        Operation(
            wallet_id=debit_wallet.id,
            type="expense",
            amount=Decimal("200.0"),
            currency=CurrencyEnum.USD,
            category="Transport",
            transaction_id=uuid4(),
            created_at=datetime(2024, 6, 10, 15, 0, 0),
        ),
        Operation(
            wallet_id=debit_wallet.id,
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
        params={"date_from": "2024-06-01", "date_to": "2024-06-30", "currency": "USD"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    assert len(lines) == 5


async def test_report_csv_empty(
    client,
    auth_headers,
):
    """Пустой CSV отчёт должен содержать только заголовки."""
    response = client.get(
        "/api/v1/reports",
        params={"date_from": "2024-06-01", "date_to": "2024-06-30", "currency": "USD"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    assert len(lines) == 1
    assert lines[0] == "date,type,wallet_id,amount,category,currency"


async def test_report_csv_special_characters(
    client,
    debit_wallet,
    db,
    auth_headers,
):
    """CSV должен правильно обрабатывать спецсимволы в категории."""
    operation = Operation(
        wallet_id=debit_wallet.id,
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
        params={"date_from": "2024-06-01", "date_to": "2024-06-30", "currency": "USD"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    assert "Food, Groceries" in lines[1]


async def test_report_csv_currency_conversion(
    client,
    debit_wallet,
    db,
    auth_headers,
    monkeypatch,
):
    """CSV отчёт должен конвертировать валюты правильно."""
    calls = []

    # 1. Готовим фейковый курс: USD -> RUB = 35.0
    async def fake_get_exchange_rate(base, target):
        calls.append((base, target))
        rates = {
            (CurrencyEnum.USD, CurrencyEnum.RUB): Decimal("35.0"),
        }
        return rates.get((base, target), Decimal("1"))

    # 2. Мокаем имя В модуле-потребителе (operations.py)
    monkeypatch.setattr(
        "app.service.operations.get_exchange_rate",
        fake_get_exchange_rate,
    )

    # 3. Данные
    operation = Operation(
        wallet_id=debit_wallet.id,
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
        params={"date_from": "2024-06-01", "date_to": "2024-06-30", "currency": "RUB"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    # Доказательство, что мок реально сработал
    assert calls == [(CurrencyEnum.USD, CurrencyEnum.RUB)]
    lines = response.text.strip().split("\n")
    assert "3500.00" in lines[1]
    assert "RUB" in lines[1]


async def test_report_csv_empty_category(
    client,
    debit_wallet,
    db,
    auth_headers,
):
    """CSV отчёт должен правильно обрабатывать пустые категории."""
    operation = Operation(
        wallet_id=debit_wallet.id,
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
        params={"date_from": "2024-06-01", "date_to": "2024-06-30", "currency": "USD"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    lines = response.text.strip().split("\n")
    assert len(lines) == 2
    assert lines[1].endswith(",USD") or ",," in lines[1]
