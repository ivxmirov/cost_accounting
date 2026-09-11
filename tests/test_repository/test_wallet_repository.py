from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum import CurrencyEnum, WalletType
from app.models import User, Wallet
from app.repository import wallets as wallets_repository


async def test_create_wallet(db_session: AsyncSession, current_user):
    wallet = await wallets_repository.create_wallet(
        db_session,
        user_id=current_user.id,
        wallet_name="test",
        amount=Decimal("10"),
        currency=CurrencyEnum.USD,
        wallet_type=WalletType.DEBIT,
        credit_limit=Decimal("0"),
    )

    assert wallet.id == 1
    assert wallet.user_id == current_user.id
    assert wallet.name == "test"
    assert wallet.balance == Decimal("10")


@pytest.mark.parametrize("wallet_type", ["debit", "credit"])
async def test_is_wallet_exists_success(
    db_session: AsyncSession,
    current_user,
    wallet_factory,
    wallet_type: str,
):
    wallet = await wallet_factory(wallet_type)

    is_exists = await wallets_repository.is_wallet_exist(
        db_session,
        user_id=current_user.id,
        wallet_name=wallet.name,
    )

    assert is_exists is True


async def test_is_wallet_exists_not_exists(db_session: AsyncSession, current_user):
    is_exists = await wallets_repository.is_wallet_exist(
        db_session,
        user_id=current_user.id,
        wallet_name="nonexists",
    )

    assert is_exists is False


async def test_is_wallet_exists_other_user(
    db_session: AsyncSession,
    debit_wallet,
):
    user = User(login="test_1")
    db_session.add(user)
    await db_session.flush()

    is_exists = await wallets_repository.is_wallet_exist(
        db_session,
        user_id=user.id,
        wallet_name=debit_wallet.name,
    )

    assert is_exists is False


async def test_get_wallet_by_name_success(db_session: AsyncSession, current_user, credit_wallet):
    found_wallet = await wallets_repository.get_wallet_by_name(
        db_session,
        user_id=current_user.id,
        wallet_name=credit_wallet.name,
    )

    assert found_wallet is not None
    assert found_wallet.name == credit_wallet.name
    assert found_wallet.balance == credit_wallet.balance
    assert found_wallet.user_id == current_user.id


async def test_get_wallet_by_name_not_exists(db_session: AsyncSession, current_user):
    found_wallet = await wallets_repository.get_wallet_by_name(
        db_session,
        user_id=current_user.id,
        wallet_name="nonexistent",
    )

    assert found_wallet is None


async def test_get_wallet_by_name_other_user(db_session: AsyncSession, debit_wallet):
    user = User(login="test_2")
    db_session.add(user)
    await db_session.flush()

    found_wallet = await wallets_repository.get_wallet_by_name(
        db_session,
        user_id=user.id,
        wallet_name=debit_wallet.name,
    )

    assert found_wallet is None


@pytest.mark.parametrize("wallet_type", ["debit", "credit"])
async def test_add_income(
    db_session: AsyncSession,
    current_user,
    wallet_factory,
    wallet_type: str,
):
    wallet = await wallet_factory(wallet_type, balance=Decimal("100"))
    initial_balance = wallet.balance
    income_amount = Decimal("50")

    updated_wallet = await wallets_repository.add_income(
        db_session,
        user_id=current_user.id,
        wallet_name=wallet.name,
        amount=income_amount,
    )

    assert updated_wallet.balance == initial_balance + income_amount
    assert updated_wallet.id == wallet.id


@pytest.mark.parametrize("wallet_type", ["debit", "credit"])
async def test_add_expense(
    db_session: AsyncSession,
    current_user,
    wallet_factory,
    wallet_type: str,
):
    wallet = await wallet_factory(wallet_type, balance=Decimal("100"))
    initial_balance = wallet.balance
    expense_amount = Decimal("50")
    
    updated_wallet = await wallets_repository.add_expense(
        db_session,
        user_id=current_user.id,
        wallet_name=wallet.name,
        amount=expense_amount,
    )

    assert updated_wallet.balance == initial_balance - expense_amount
    assert updated_wallet.id == wallet.id


async def test_get_user_wallets(db_session: AsyncSession, current_user):
    wallet1 = Wallet(
        name="wallet1",
        balance=Decimal("100"),
        user_id=current_user.id,
        currency=CurrencyEnum.USD,
        type=WalletType.DEBIT,
    )
    db_session.add(wallet1)

    wallet2 = Wallet(
        name="wallet2",
        balance=Decimal("200"),
        user_id=current_user.id,
        currency=CurrencyEnum.USD,
        type=WalletType.CREDIT,
        credit_limit=Decimal("250")
    )
    db_session.add(wallet2)
    await db_session.flush()

    wallets = await wallets_repository.get_user_wallets(db_session, user_id=current_user.id)

    assert len(wallets) == 2
    assert wallets[0].name == "wallet1" or wallets[1].name == "wallet1"
    assert wallets[0].name == "wallet2" or wallets[1].name == "wallet2"


async def test_get_user_wallets_empty(db_session: AsyncSession, current_user):
    wallets = await wallets_repository.get_user_wallets(db_session, user_id=current_user.id)

    assert len(wallets) == 0


async def test_get_user_wallets_other_user(db_session: AsyncSession):
    other_user = User(login="other_user")
    db_session.add(other_user)
    await db_session.flush()

    wallets = await wallets_repository.get_user_wallets(db_session, user_id=other_user.id)

    assert len(wallets) == 0


async def test_get_wallet_by_id_without_user_check_success(
    db_session: AsyncSession,
    current_user,
    debit_wallet,
):
    found_wallet = await wallets_repository.get_wallet_by_id_without_user_check(
        db_session,
        wallet_id=debit_wallet.id,
    )

    assert found_wallet is not None
    assert found_wallet.id == debit_wallet.id
    assert found_wallet.name == debit_wallet.name
    assert found_wallet.balance == debit_wallet.balance
    assert found_wallet.user_id == current_user.id


async def test_get_wallet_by_id_without_user_check_not_exists(db_session: AsyncSession):
    found_wallet = await wallets_repository.get_wallet_by_id_without_user_check(
        db_session,
        wallet_id=99999,
    )

    assert found_wallet is None


async def test_get_wallet_by_id_without_user_check_other_user(db_session: AsyncSession, credit_wallet):
    other_user = User(login="other_user_test")
    db_session.add(other_user)
    await db_session.flush()

    found_wallet = await wallets_repository.get_wallet_by_id_without_user_check(
        db_session,
        wallet_id=credit_wallet.id,
    )

    assert found_wallet is not None
    assert found_wallet.id == credit_wallet.id
    assert found_wallet.user_id == credit_wallet.user_id
