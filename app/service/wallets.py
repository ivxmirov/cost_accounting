from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum import CurrencyEnum, WalletType
from app.models import User
from app.repository import wallets as wallets_repository
from app.schemas import TotalBalance, WalletCreateSchema, WalletResponseSchema
from app.service import exchange_service


async def get_total_balance(db: AsyncSession, current_user: User) -> TotalBalance:
    """
    Получает общий баланс всех кошельков пользователя с конвертацией валют в рубли.

    Логика подсчета такова, что кредитный кошелек с кредитным лимитом 300 и текущим балансом 0,
    дает -300 к общему балансу.

    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
    Returns:
        Общий баланс всех кошельков пользователя в рублях
    """
    wallets = await wallets_repository.get_user_wallets(db, current_user.id)
    total_balance = Decimal("0")

    for wallet in wallets:
        # Это условие выполнится только у дебетовых кошельков
        if wallet.credit_limit is None:
            credit_limit = 0
        else:
            # Это условие выполнится только у кредитных кошельков
            credit_limit = wallet.credit_limit

        if wallet.currency == CurrencyEnum.RUB:
            total_balance += wallet.balance - credit_limit
        else:
            exchange_rate = await exchange_service.get_exchange_rate(
                wallet.currency, CurrencyEnum.RUB,
            )
            total_balance += exchange_rate * (wallet.balance - credit_limit)

    return TotalBalance(total_balance=total_balance)


async def create_wallet(
    db: AsyncSession, current_user: User, wallet: WalletCreateSchema,
) -> WalletResponseSchema:
    """
    Создает новый кошелек для пользователя с проверкой на дубликаты
    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
        wallet: Данные для создания кошелька (название, начальный баланс, валюта)
    Returns:
        Информация о созданном кошельке
    Raises:
        HTTPException: Если кошелек с таким названием уже существует
    """
    if await wallets_repository.is_wallet_exist(db, current_user.id, wallet.name):
        raise HTTPException(status_code=400, detail=f"Wallet '{wallet.name}' already exists")

    credit_limit = wallet.credit_limit

    if wallet.type == WalletType.CREDIT:
        if wallet.credit_limit is None:
            raise HTTPException(400, "Кредитный кошелёк требует кредитный лимит")
        if wallet.credit_limit <= 0:
            raise HTTPException(400, "Кредитный лимит должен быть положительным")
        if wallet.initial_balance > wallet.credit_limit:
            raise HTTPException(
                400, "Баланс кредитного кошелька не может быть больше кредитного лимита",
            )

    elif wallet.type == WalletType.DEBIT:
        credit_limit = None

    new_wallet = await wallets_repository.create_wallet(
        db,
        user_id=current_user.id,
        wallet_name=wallet.name,
        amount=wallet.initial_balance,
        currency=wallet.currency,
        wallet_type=wallet.type,
        credit_limit=credit_limit,
    )

    await db.commit()
    return WalletResponseSchema.model_validate(new_wallet)


async def get_user_wallets(db: AsyncSession, current_user: User) -> list[WalletResponseSchema]:
    """
    Получает список всех кошельков пользователя
    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
    Returns:
        Список всех кошельков пользователя
    """
    wallets = await wallets_repository.get_user_wallets(db, current_user.id)
    return [WalletResponseSchema.model_validate(wallet) for wallet in wallets]


async def get_wallet_by_name(
    db: AsyncSession, current_user: User, wallet_name: str,
) -> WalletResponseSchema:
    """
    Получает кошелек пользователя по названию
    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
        wallet_name: Название кошелька для поиска
    Returns:
        Информация о кошельке
    Raises:
        HTTPException: Если кошелек не найден
    """
    if not await wallets_repository.is_wallet_exist(db, current_user.id, wallet_name):
        raise HTTPException(status_code=404, detail=f"Wallet '{wallet_name}' not found")

    wallet = await wallets_repository.get_wallet_by_name(db, current_user.id, wallet_name)

    return WalletResponseSchema.model_validate(wallet)
