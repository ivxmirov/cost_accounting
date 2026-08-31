import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas import ExpenseCreateSchema, IncomeCreateSchema
from app.service import operations as operations_service


@pytest.mark.parametrize("wallet_type", ["debit", "credit"])
async def test_add_income_success(
    db_session: AsyncSession,
    current_user,
    wallet_factory,
    wallet_type: str,
):
    wallet = await wallet_factory(wallet_type)
    wallet.balance = Decimal("50")
    await db_session.flush()

    payload = IncomeCreateSchema(
        transaction_id=uuid.uuid4(),
        wallet_name=wallet.name,
        amount=Decimal("100"),
        description="Salary",
    )

    response, status_code = await operations_service.add_income(
        db_session,
        current_user=current_user,
        operation=payload,
    )

    assert response is not None
    assert status_code == 201
    assert response.amount == payload.amount
    assert response.type == "income"
    assert response.currency == wallet.currency
    assert response.category == payload.description
    assert wallet.balance == Decimal("150")


async def test_add_income_wallet_not_exists(db_session: AsyncSession, current_user):
    payload = IncomeCreateSchema(
        transaction_id=uuid.uuid4(),
        wallet_name="nonexistent",
        amount=Decimal("100"),
        description="Salary",
    )

    with pytest.raises(HTTPException) as exc:
        await operations_service.add_income(
            db_session,
            current_user=current_user,
            operation=payload,
        )

    assert exc.value.status_code == 404
    assert "nonexistent" in exc.value.detail


@pytest.mark.parametrize("wallet_type", ["debit", "credit"])
async def test_add_income_other_user(db_session: AsyncSession, wallet_factory, wallet_type):
    wallet = await wallet_factory(wallet_type)
    other_user = User(login="other_user")
    db_session.add(other_user)
    await db_session.flush()

    payload = IncomeCreateSchema(
        transaction_id=uuid.uuid4(),
        wallet_name=wallet.name,
        amount=Decimal("100"),
        description="Salary",
    )

    with pytest.raises(HTTPException) as exc:
        await operations_service.add_income(db_session, current_user=other_user, operation=payload)

    assert exc.value.status_code == 404


@pytest.mark.parametrize("wallet_type", ["debit", "credit"])
async def test_add_expense_success(
    db_session: AsyncSession,
    current_user,
    wallet_factory,
    wallet_type,
):
    wallet = await wallet_factory(wallet_type)
    wallet.balance = Decimal("200")
    await db_session.flush()

    payload = ExpenseCreateSchema(
        transaction_id=uuid.uuid4(),
        wallet_name=wallet.name,
        amount=Decimal("50"),
        description="Groceries",
    )

    response, status_code = await operations_service.add_expense(
        db_session,
        current_user=current_user,
        operation=payload,
    )

    assert response is not None
    assert status_code == 201
    assert response.amount == payload.amount
    assert response.type == "expense"
    assert response.currency == wallet.currency
    assert response.category == payload.description
    assert wallet.balance == Decimal("150")


async def test_add_expense_wallet_not_exists(db_session: AsyncSession, current_user):
    payload = ExpenseCreateSchema(
        transaction_id=uuid.uuid4(),
        wallet_name="nonexistent",
        amount=Decimal("50"),
        description="Groceries",
    )

    with pytest.raises(HTTPException) as exc:
        await operations_service.add_expense(
            db_session,
            current_user=current_user,
            operation=payload,
        )

    assert exc.value.status_code == 404
    assert "nonexistent" in exc.value.detail


@pytest.mark.parametrize("wallet_type", ["debit", "credit"])
async def test_add_expense_other_user(db_session: AsyncSession, wallet_factory, wallet_type):
    wallet = await wallet_factory(wallet_type)
    other_user = User(login="other_user")
    db_session.add(other_user)
    await db_session.flush()

    payload = ExpenseCreateSchema(
        transaction_id=uuid.uuid4(),
        wallet_name=wallet.name,
        amount=Decimal("50"),
        description="Groceries",
    )

    with pytest.raises(HTTPException) as exc:
        await operations_service.add_expense(db_session, current_user=other_user, operation=payload)

    assert exc.value.status_code == 404


@pytest.mark.parametrize("wallet_type", ["debit", "credit"])
async def test_add_expense_insufficient_funds(
    db_session: AsyncSession,
    current_user,
    wallet_factory,
    wallet_type,
):
    wallet = await wallet_factory(wallet_type)
    wallet.balance = Decimal("30")
    await db_session.flush()

    payload = ExpenseCreateSchema(
        transaction_id=uuid.uuid4(),
        wallet_name=wallet.name,
        amount=Decimal("50"),
        description="Groceries",
    )

    with pytest.raises(HTTPException) as exc:
        await operations_service.add_expense(
            db_session,
            current_user=current_user,
            operation=payload,
        )

    assert exc.value.status_code == 400
    assert "Insufficient funds" in exc.value.detail
