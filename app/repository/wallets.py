from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum import CurrencyEnum, WalletType
from app.models import Wallet


async def is_wallet_exist(db: AsyncSession, user_id: int, wallet_name: str) -> bool:
    result = await db.execute(
        select(Wallet).where(Wallet.name == wallet_name, Wallet.user_id == user_id)
    )
    return result.scalar_one_or_none() is not None


async def add_income(db: AsyncSession, user_id: int, wallet_name: str, amount: Decimal) -> Wallet:
    result = await db.execute(
        select(Wallet).where(Wallet.name == wallet_name, Wallet.user_id == user_id)
    )
    wallet = result.scalar_one()
    wallet.balance += amount
    return wallet


async def get_wallet_by_name(db: AsyncSession, user_id: int, wallet_name: str) -> Wallet | None:
    result = await db.execute(
        select(Wallet).where(Wallet.name == wallet_name, Wallet.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def add_expense(db: AsyncSession, user_id: int, wallet_name: str, amount: Decimal) -> Wallet:
    result = await db.execute(
        select(Wallet).where(Wallet.name == wallet_name, Wallet.user_id == user_id)
    )
    wallet = result.scalar_one()
    wallet.balance -= amount
    return wallet


async def get_user_wallets(
    db: AsyncSession,
    user_id: int,
) -> list[Wallet]:
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    return list(result.scalars().all())


async def create_wallet(
    db: AsyncSession,
    user_id: int,
    wallet_name: str,
    amount: Decimal,
    currency: CurrencyEnum,
    wallet_type: WalletType,
    credit_limit: Decimal | None,
) -> Wallet:
    wallet = Wallet(
        name=wallet_name,
        balance=amount,
        user_id=user_id,
        currency=currency,
        type=wallet_type,
        credit_limit=credit_limit,
    )
    db.add(wallet)
    await db.flush()
    return wallet


async def get_wallet_by_id(db: AsyncSession, user_id: int, wallet_id: int) -> Wallet | None:
    result = await db.execute(
        select(Wallet).where(Wallet.id == wallet_id, Wallet.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_wallet_by_id_without_user_check(db: AsyncSession, wallet_id: int) -> Wallet | None:
    """
    Находит кошелек в базе данных по идентификатору БЕЗ проверки владельца
    Используется для различия между ошибками 404 (кошелек не найден) и 403 (чужой кошелек)
    Args:
        db: Сессия базы данных
        wallet_id: Идентификатор кошелька для поиска
    Returns:
        Объект кошелька или None, если кошелек не найден
    """
    result = await db.execute(select(Wallet).where(Wallet.id == wallet_id))
    return result.scalar_one_or_none()
