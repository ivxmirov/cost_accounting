from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum import CurrencyEnum
from app.models import Wallet


async def add_income(
    db: AsyncSession, user_id: int, wallet_name: str, amount: Decimal
) -> Wallet | None:
    result = await db.execute(
        select(Wallet).filter(Wallet.name == wallet_name, Wallet.user_id == user_id)
    )
    wallet = result.scalars().first()
    if wallet:
        wallet.balance += amount
    return wallet


async def add_expense(
    db: AsyncSession, user_id: int, wallet_name: str, amount: Decimal
) -> Wallet | None:
    result = await db.execute(
        select(Wallet).filter(Wallet.name == wallet_name, Wallet.user_id == user_id)
    )
    wallet = result.scalars().first()
    if wallet:
        wallet.balance -= amount
    return wallet


async def is_wallet_exist(db: AsyncSession, user_id: int, wallet_name: str) -> bool:
    result = await db.execute(
        select(Wallet).filter(Wallet.name == wallet_name, Wallet.user_id == user_id)
    )
    return result.scalars().first() is not None


async def get_wallet_balance_by_name(
    db: AsyncSession, user_id: int, wallet_name: str
) -> Wallet | None:
    result = await db.execute(
        select(Wallet).filter(Wallet.name == wallet_name, Wallet.user_id == user_id)
    )
    return result.scalars().first()


async def get_wallet_by_id(db: AsyncSession, user_id: int, wallet_id: int) -> Wallet | None:
    result = await db.execute(
        select(Wallet).filter(Wallet.id == wallet_id, Wallet.user_id == user_id)
    )
    return result.scalars().first()


async def get_all_wallets(db: AsyncSession, user_id: int) -> list[Wallet]:
    result = await db.execute(select(Wallet).filter(Wallet.user_id == user_id))
    return list(result.scalars().all())


async def create_wallet(
    db: AsyncSession,
    user_id: int,
    wallet_name: str,
    initial_balance: Decimal,
    currency: CurrencyEnum,
) -> Wallet:
    wallet = Wallet(name=wallet_name, balance=initial_balance, user_id=user_id, currency=currency)
    db.add(wallet)
    await db.flush()
    return wallet
