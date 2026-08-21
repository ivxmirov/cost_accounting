from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum import CurrencyEnum
from app.models import User, Wallet
from app.schemas import TotalBalance, WalletCreateSchema
from app.service import wallets as wallets_service


async def test_create_wallet(db_session: AsyncSession, current_user):
    payload = WalletCreateSchema(name="test", initial_balance=Decimal(10))

    wallet = await wallets_service.create_wallet(
        db_session, current_user=current_user, wallet=payload
    )

    assert wallet.id == 1
    assert wallet.name == "test"
    assert wallet.balance == Decimal(10)


async def test_create_wallet_exists(db_session: AsyncSession, current_user, wallet):
    payload = WalletCreateSchema(name=wallet.name, initial_balance=Decimal(10))

    with pytest.raises(HTTPException) as exc:
        await wallets_service.create_wallet(
            db_session, current_user=current_user, wallet=payload
        )

    assert exc.value.status_code == 400


async def test_get_wallet_total_balance(db_session: AsyncSession, current_user):
    wallet1 = Wallet(
        name="wallet1",
        balance=Decimal(100),
        user_id=current_user.id,
        currency=CurrencyEnum.RUB,
    )
    db_session.add(wallet1)

    wallet2 = Wallet(
        name="wallet2",
        balance=Decimal(200),
        user_id=current_user.id,
        currency=CurrencyEnum.RUB,
    )
    db_session.add(wallet2)
    await db_session.commit()

    result = await wallets_service.get_total_balance(db_session, current_user=current_user)

    assert isinstance(result, TotalBalance)
    assert float(result.total_balance) == 300.0


async def test_get_wallet_total_balance_empty(db_session: AsyncSession, current_user):
    result = await wallets_service.get_total_balance(db_session, current_user=current_user)

    assert isinstance(result, TotalBalance)
    assert float(result.total_balance) == 0.0


async def test_get_wallet_by_name(db_session: AsyncSession, current_user, wallet):
    wallet.balance = Decimal(150)
    await db_session.flush()

    result = await wallets_service.get_wallet(
        db_session, current_user=current_user, wallet_name=wallet.name
    )

    assert result.id == wallet.id
    assert result.name == wallet.name
    assert result.balance == Decimal(150)


async def test_get_wallet_not_exists(db_session: AsyncSession, current_user):
    with pytest.raises(HTTPException) as exc:
        await wallets_service.get_wallet(
            db_session, current_user=current_user, wallet_name="nonexistent"
        )

    assert exc.value.status_code == 404
    assert "nonexistent" in exc.value.detail


async def test_get_wallet_other_user(db_session: AsyncSession, wallet):
    other_user = User(login="other_user")
    db_session.add(other_user)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await wallets_service.get_wallet(
            db_session, current_user=other_user, wallet_name=wallet.name
        )

    assert exc.value.status_code == 404
