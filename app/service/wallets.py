from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum import CurrencyEnum
from app.models import User
from app.repository import wallets as wallets_repository
from app.schemas import CreateWalletRequest, TotalBalance, WalletResponse
from app.service import exchange_service


async def get_total_balance(db: AsyncSession, current_user: User) -> TotalBalance:
    """
    Получает общий баланс всех кошельков пользователя с конвертацией валют в рубли
    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
    Returns:
        Общий баланс всех кошельков в рублях
    """
    wallets = await wallets_repository.get_all_wallets(db, current_user.id)
    total_balance = Decimal(0)
    for wallet in wallets:
        if wallet.currency == CurrencyEnum.RUB:
            total_balance += wallet.balance
        else:
            exchange_rate = await exchange_service.get_exchange_rate(
                wallet.currency, CurrencyEnum.RUB
            )
            total_balance += exchange_rate * wallet.balance
    return TotalBalance(total_balance=total_balance)


async def create_wallet(
    db: AsyncSession, current_user: User, wallet: CreateWalletRequest
) -> WalletResponse:
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

    new_wallet = await wallets_repository.create_wallet(
        db, current_user.id, wallet.name, wallet.initial_balance, wallet.currency
    )
    await db.commit()
    return WalletResponse.model_validate(new_wallet)


async def get_all_wallets(db: AsyncSession, current_user: User) -> list[WalletResponse]:
    """
    Получает список всех кошельков пользователя
    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
    Returns:
        Список всех кошельков пользователя
    """
    wallets = await wallets_repository.get_all_wallets(db, current_user.id)
    return [WalletResponse.model_validate(wallet) for wallet in wallets]


async def get_wallet(db: AsyncSession, current_user: User, wallet_name: str) -> WalletResponse:
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
    wallet = await wallets_repository.get_wallet_balance_by_name(db, current_user.id, wallet_name)
    if not wallet:
        raise HTTPException(status_code=404, detail=f"Wallet '{wallet_name}' not found")
    return WalletResponse.model_validate(wallet)
