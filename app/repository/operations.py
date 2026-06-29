from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum import CurrencyEnum
from app.models import Operation


async def create_operation(
    db: AsyncSession,
    wallet_id: int,
    type: str,  # pylint: disable=redefined-builtin
    amount: Decimal,
    currency: CurrencyEnum,
    category: str | None = None,
    subcategory: str | None = None,
) -> Operation:
    operation = Operation(
        wallet_id=wallet_id,
        type=type,
        amount=amount,
        currency=currency,
        category=category,
        subcategory=subcategory,
    )

    db.add(operation)
    await db.flush()
    return operation


async def get_operations_list(
    db: AsyncSession,
    wallets_ids: list[int],
    date_from: datetime | None,
    date_to: datetime | None,
) -> list[Operation]:
    query = select(Operation).filter(Operation.wallet_id.in_(wallets_ids))

    if date_from:
        query = query.filter(Operation.created_at >= date_from)

    if date_to:
        query = query.filter(Operation.created_at <= date_to)

    query = query.order_by(Operation.created_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())
