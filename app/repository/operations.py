from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum import CurrencyEnum
from app.models import Operation


async def get_by_transaction_id(db: AsyncSession, transaction_id: UUID) -> Operation | None:
    """
    Находит операцию по уникальному идентификатору транзакции

    Args:
        db: Сессия базы данных
        transaction_id: Уникальный идентификатор транзакции

    Returns:
        Объект операции или None, если операция не найдена
    """
    result = await db.execute(select(Operation).where(Operation.transaction_id == transaction_id))
    return result.scalar_one_or_none()


async def create_operation(
    db: AsyncSession,
    wallet_id: int,
    type: str,
    amount: Decimal,
    currency: CurrencyEnum,
    transaction_id: UUID,
    category: str | None = None,
    subcategory: str | None = None,
) -> Operation:
    """
    Создает новую операцию в базе данных

    Args:
        db: Сессия базы данных
        wallet_id: Идентификатор кошелька, к которому относится операция
        type: Тип операции (расход, доход или перевод)
        amount: Сумма операции
        currency: Валюта операции
        transaction_id: Уникальный идентификатор транзакции для идемпотентности
        category: Категория операции (необязательное поле)
        subcategory: Подкатегория операции (необязательное поле)

    Returns:
        Созданный объект операции
    """
    operation = Operation(
        wallet_id=wallet_id,
        type=type,
        amount=round(amount, 2),
        currency=currency,
        transaction_id=transaction_id,
        category=category,
        subcategory=subcategory,
    )
    db.add(operation)
    await db.flush()
    return operation


async def get_operations_list(
    db: AsyncSession, wallets_ids: list[int], date_from: datetime | None, date_to: datetime | None,
) -> list[Operation]:
    """
    Получает список операций из базы данных с фильтрацией по кошелькам и датам

    Args:
        db: Сессия базы данных
        wallets_ids: Список идентификаторов кошельков для фильтрации
        date_from: Начальная дата для фильтрации
        date_to: Конечная дата для фильтрации

    Returns:
        Список операций, соответствующих критериям фильтрации
    """
    query = select(Operation).where(Operation.wallet_id.in_(wallets_ids))

    if date_from:
        query = query.where(Operation.created_at >= date_from)

    if date_to:
        query = query.where(Operation.created_at <= date_to)

    result = await db.execute(query)
    return list(result.scalars().all())


async def create_operations_bulk(
    db: AsyncSession, operations_payload: list[dict],
) -> list[Operation]:
    """
    Создает несколько операций за один раз (пакетная вставка)

    Args:
        db: Сессия базы данных
        operations_payload: Список словарей с данными операций

    Returns:
        Список созданных объектов операций с заполненными id
    """
    db_operations = [Operation(**payload) for payload in operations_payload]
    db.add_all(db_operations)
    await db.flush()
    return db_operations
