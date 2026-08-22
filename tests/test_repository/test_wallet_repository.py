from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.enum import CurrencyEnum
from app.models import User, Wallet
from app.repository import wallets as wallets_repository


async def test_create_wallet(db_session: AsyncSession, current_user):
    wallet = await wallets_repository.create_wallet(
        db_session,
        user_id=current_user.id,
        wallet_name="test",
        amount=Decimal(10),
        currency=CurrencyEnum.USD,
    )

    assert wallet.id == 1
    assert wallet.user_id == current_user.id
    assert wallet.name == "test"
    assert wallet.balance == Decimal(10)


async def test_is_wallet_exists_success(db_session: AsyncSession, current_user, wallet):
    is_exists = await wallets_repository.is_wallet_exist(
        db_session, user_id=current_user.id, wallet_name=wallet.name
    )

    assert is_exists is True


async def test_is_wallet_exists_not_exists(db_session: AsyncSession, current_user):
    is_exists = await wallets_repository.is_wallet_exist(
        db_session, user_id=current_user.id, wallet_name="nonexists"
    )

    assert is_exists is False


async def test_is_wallet_exists_other_user(db_session: AsyncSession, wallet):
    user = User(login="test_1")
    db_session.add(user)
    await db_session.flush()

    is_exists = await wallets_repository.is_wallet_exist(
        db_session, user_id=user.id, wallet_name=wallet.name
    )

    assert is_exists is False


async def test_get_wallet_by_name_success(db_session: AsyncSession, current_user, wallet):
    found_wallet = await wallets_repository.get_wallet_by_name(
        db_session, user_id=current_user.id, wallet_name=wallet.name
    )

    assert found_wallet is not None
    assert found_wallet.name == wallet.name
    assert found_wallet.balance == wallet.balance
    assert found_wallet.user_id == current_user.id


async def test_get_wallet_by_name_not_exists(db_session: AsyncSession, current_user):
    found_wallet = await wallets_repository.get_wallet_by_name(
        db_session, user_id=current_user.id, wallet_name="nonexistent"
    )

    assert found_wallet is None


async def test_get_wallet_by_name_other_user(db_session: AsyncSession, wallet):
    user = User(login="test_2")
    db_session.add(user)
    await db_session.flush()

    found_wallet = await wallets_repository.get_wallet_by_name(
        db_session, user_id=user.id, wallet_name=wallet.name
    )

    assert found_wallet is None


async def test_add_income(db_session: AsyncSession, current_user, wallet):
    initial_balance = wallet.balance
    income_amount = Decimal(50)

    updated_wallet = await wallets_repository.add_income(
        db_session,
        user_id=current_user.id,
        wallet_name=wallet.name,
        amount=income_amount,
    )

    assert updated_wallet.balance == initial_balance + income_amount
    assert updated_wallet.id == wallet.id


async def test_add_expense(db_session: AsyncSession, current_user, wallet):
    wallet.balance = Decimal(100)
    await db_session.flush()

    expense_amount = Decimal(30)
    updated_wallet = await wallets_repository.add_expense(
        db_session,
        user_id=current_user.id,
        wallet_name=wallet.name,
        amount=expense_amount,
    )

    assert updated_wallet.balance == Decimal(100) - expense_amount
    assert updated_wallet.id == wallet.id


async def test_get_all_wallets(db_session: AsyncSession, current_user):
    wallet1 = Wallet(
        name="wallet1",
        balance=Decimal(100),
        user_id=current_user.id,
        currency=CurrencyEnum.USD,
    )
    db_session.add(wallet1)

    wallet2 = Wallet(
        name="wallet2",
        balance=Decimal(200),
        user_id=current_user.id,
        currency=CurrencyEnum.USD,
    )
    db_session.add(wallet2)
    await db_session.flush()

    wallets = await wallets_repository.get_all_wallets(db_session, user_id=current_user.id)

    assert len(wallets) == 2
    assert wallets[0].name == "wallet1" or wallets[1].name == "wallet1"
    assert wallets[0].name == "wallet2" or wallets[1].name == "wallet2"


async def test_get_all_wallets_empty(db_session: AsyncSession, current_user):
    wallets = await wallets_repository.get_all_wallets(db_session, user_id=current_user.id)

    assert len(wallets) == 0


async def test_get_all_wallets_other_user(db_session: AsyncSession):
    other_user = User(login="other_user")
    db_session.add(other_user)
    await db_session.flush()

    wallets = await wallets_repository.get_all_wallets(db_session, user_id=other_user.id)

    assert len(wallets) == 0


async def test_get_wallet_by_id_without_user_check_success(
    db_session: AsyncSession, current_user, wallet
):
    found_wallet = await wallets_repository.get_wallet_by_id_without_user_check(
        db_session, wallet_id=wallet.id
    )

    assert found_wallet is not None
    assert found_wallet.id == wallet.id
    assert found_wallet.name == wallet.name
    assert found_wallet.balance == wallet.balance
    assert found_wallet.user_id == current_user.id


async def test_get_wallet_by_id_without_user_check_not_exists(db_session: AsyncSession):
    found_wallet = await wallets_repository.get_wallet_by_id_without_user_check(
        db_session, wallet_id=99999
    )

    assert found_wallet is None


async def test_get_wallet_by_id_without_user_check_other_user(db_session: AsyncSession, wallet):
    other_user = User(login="other_user_test")
    db_session.add(other_user)
    await db_session.flush()

    found_wallet = await wallets_repository.get_wallet_by_id_without_user_check(
        db_session, wallet_id=wallet.id
    )

    assert found_wallet is not None
    assert found_wallet.id == wallet.id
    assert found_wallet.user_id == wallet.user_id
