from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum import CurrencyEnum, OperationType
from app.models import User
from app.repository import operations as operations_repository
from app.repository import wallets as wallets_repository
from app.schemas import (
    BulkOperationsCreateSchema,
    ExpenseCreateSchema,
    IncomeCreateSchema,
    OperationResponse,
    TransferCreateSchemaV2,
    TransferResponse,
    WalletResponse,
)
from app.service.exchange_service import get_exchange_rate


async def add_income(
    db: AsyncSession, current_user: User, operation: IncomeCreateSchema
) -> tuple[OperationResponse, int]:
    """
    Добавляет доход к балансу кошелька с проверкой существования кошелька и идемпотентностью
    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
        operation: Данные операции (transaction_id, wallet_name, сумма, описание)
    Returns:
        Кортеж из информации об операции и HTTP статус кода (200 если существует, 201 если создана)
    Raises:
        HTTPException: Если кошелек не найден
    """
    existing_operation = await operations_repository.get_by_transaction_id(
        db, operation.transaction_id
    )

    if existing_operation:
        return (OperationResponse.model_validate(existing_operation), 200)

    if not await wallets_repository.is_wallet_exist(db, current_user.id, operation.wallet_name):
        raise HTTPException(status_code=404, detail=f"Wallet '{operation.wallet_name}' not found")

    wallet = await wallets_repository.add_income(
        db, current_user.id, operation.wallet_name, operation.amount
    )

    new_operation = await operations_repository.create_operation(
        db=db,
        wallet_id=wallet.id,
        type=OperationType.INCOME,
        amount=operation.amount,
        currency=wallet.currency,
        transaction_id=operation.transaction_id,
        category=operation.description,
    )
    await db.commit()
    return (OperationResponse.model_validate(new_operation), 201)


async def add_expense(
    db: AsyncSession, current_user: User, operation: ExpenseCreateSchema
) -> tuple[OperationResponse, int]:
    """
    Вычитает расход из баланса кошелька
    Проверяет существования кошелька, достаточность средств
    и обеспечивает идемпотентность
    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
        operation: Данные операции (transaction_id, wallet_name, сумма, описание)
    Returns:
        Кортеж из информации об операции и HTTP статус кода (200 если существует, 201 если создана)
    Raises:
        HTTPException: Если кошелек не найден или недостаточно средств
    """
    existing_operation = await operations_repository.get_by_transaction_id(
        db, operation.transaction_id
    )
    if existing_operation:
        return (OperationResponse.model_validate(existing_operation), 200)

    wallet = await wallets_repository.get_wallet_by_name(db, current_user.id, operation.wallet_name)

    if not wallet:
        raise HTTPException(status_code=404, detail=f"Wallet '{operation.wallet_name}' not found")

    if wallet.balance < operation.amount:
        raise HTTPException(
            status_code=400, detail=f"Insufficient funds. Available: {wallet.balance}"
        )

    wallet = await wallets_repository.add_expense(
        db, current_user.id, operation.wallet_name, operation.amount
    )
    new_operation = await operations_repository.create_operation(
        db=db,
        wallet_id=wallet.id,
        type=OperationType.EXPENSE,
        amount=operation.amount,
        currency=wallet.currency,
        transaction_id=operation.transaction_id,
        category=operation.description,
    )
    await db.commit()
    return (OperationResponse.model_validate(new_operation), 201)


async def get_operations_list(
    db: AsyncSession,
    current_user: User,
    wallet_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[OperationResponse]:
    """
    Получает список операций пользователя с фильтрацией по кошельку и датам
    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
        wallet_id: Идентификатор кошелька для фильтрации
        date_from: Начальная дата для фильтрации
        date_to: Конечная дата для фильтрации
    Returns:
        Список операций в формате OperationResponse
    Raises:
        HTTPException: Если указанный кошелек не найден
    """
    if wallet_id:
        wallet = await wallets_repository.get_wallet_by_id(db, current_user.id, wallet_id)
        if not wallet:
            raise HTTPException(status_code=404, detail=f"Wallet '{wallet_id}' not found")
        wallets_ids = [wallet.id]
    else:
        wallets = await wallets_repository.get_all_wallets(db, current_user.id)
        wallets_ids = [w.id for w in wallets]

    operations = await operations_repository.get_operations_list(
        db,
        wallets_ids,
        date_from,
        date_to,
    )
    result = []
    for operation in operations:
        result.append(OperationResponse.model_validate(operation))
    return result


async def transfer_between_wallets(
    db: AsyncSession,
    user_id: int,
    transaction_id: UUID,
    from_wallet_id: int,
    to_wallet_id: int,
    amount: Decimal,
) -> tuple[OperationResponse, int]:
    """
    Переводит деньги между кошельками пользователя
    Обеспечивает идемпотентность и, при необходимости, конвертацию валют
    Args:
        db: Сессия базы данных
        user_id: Идентификатор пользователя
        transaction_id: Уникальный идентификатор транзакции для идемпотентности
        from_wallet_id: Идентификатор кошелька-отправителя
        to_wallet_id: Идентификатор кошелька-получателя
        amount: Сумма перевода
    Returns:
        Кортеж из информации об операции и HTTP статус кода (200 если существует, 201 если создана)
    Raises:
        HTTPException: Если кошелек не найден или недостаточно средств
    """
    existing_operation = await operations_repository.get_by_transaction_id(db, transaction_id)
    if existing_operation:
        return (OperationResponse.model_validate(existing_operation), 200)

    from_wallet = await wallets_repository.get_wallet_by_id(db, user_id, from_wallet_id)
    to_wallet = await wallets_repository.get_wallet_by_id(db, user_id, to_wallet_id)

    if not from_wallet or not to_wallet:
        raise HTTPException(404, "Wallet not Found")
    if from_wallet.balance < amount:
        raise HTTPException(400, f"Not enough money: {from_wallet.balance} {from_wallet.currency}")

    target_amount = amount
    if from_wallet.currency != to_wallet.currency:
        exchange_rate = await get_exchange_rate(from_wallet.currency, to_wallet.currency)
        target_amount = amount * exchange_rate

    from_wallet.balance = from_wallet.balance - amount
    to_wallet.balance = to_wallet.balance + target_amount

    new_operation = await operations_repository.create_operation(
        db=db,
        wallet_id=from_wallet.id,
        type=OperationType.TRANSFER,
        amount=target_amount,
        currency=to_wallet.currency,
        transaction_id=transaction_id,
        category="перевод",
    )
    db.add(from_wallet)
    db.add(to_wallet)
    db.add(new_operation)
    await db.commit()
    return (OperationResponse.model_validate(new_operation), 201)


async def transfer_between_wallets_v2(
    db: AsyncSession,
    transfer: TransferCreateSchemaV2,
    user_id: int,
) -> tuple[TransferResponse, int]:
    """
    Переводит деньги между кошельками пользователя
    Обеспечивает идемпотентность и, при необходимости, конвертацию валют
    Args:
        db: Сессия базы данных
        transfer: Информация об операции
        user_id: Идентификатор пользователя
    Returns:
        Кортеж из информации об операции и HTTP статус кода (200 если существует, 201 если создана)
    Raises:
        HTTPException: Если хотя бы один из кошельков не найден
                       Если оба кошелька - это один и тот же кошелек
                       Если недостаточно средств для перевода
    """
    existing_operation = await operations_repository.get_by_transaction_id(
        db, transfer.transaction_id
    )
    from_wallet = await wallets_repository.get_wallet_by_id(db, user_id, transfer.from_wallet_id)
    to_wallet = await wallets_repository.get_wallet_by_id(db, user_id, transfer.to_wallet_id)

    if not from_wallet or not to_wallet:
        raise HTTPException(404, "Wallet not Found")
    if from_wallet.id == to_wallet.id:
        raise HTTPException(400, "Same wallets ids!")
    if from_wallet.balance < transfer.amount:
        raise HTTPException(400, f"Not enough money: {from_wallet.balance} {from_wallet.currency}")

    if transfer.received_amount is not None:
        target_amount = transfer.received_amount
        exchange_rate = transfer.received_amount / transfer.amount
    else:
        if from_wallet.currency == to_wallet.currency:
            exchange_rate = Decimal(1.0)
            target_amount = transfer.amount
        else:
            exchange_rate = await get_exchange_rate(from_wallet.currency, to_wallet.currency)
            target_amount = transfer.amount * exchange_rate

    if existing_operation:
        return (
            TransferResponse(
                success=True,
                from_wallet=WalletResponse.model_validate(from_wallet),
                to_wallet=WalletResponse.model_validate(to_wallet),
                transferred_amount=existing_operation.amount,
                received_amount=target_amount,
                exchange_rate=exchange_rate,
            ),
            200,
        )

    from_wallet.balance = from_wallet.balance - transfer.amount
    to_wallet.balance = to_wallet.balance + target_amount

    new_operation = await operations_repository.create_operation(
        db=db,
        wallet_id=from_wallet.id,
        type=OperationType.TRANSFER,
        amount=target_amount,
        currency=to_wallet.currency,
        transaction_id=transfer.transaction_id,
        category="перевод",
    )
    db.add(from_wallet)
    db.add(to_wallet)
    db.add(new_operation)
    await db.commit()
    await db.refresh(from_wallet)
    await db.refresh(to_wallet)

    return (
        TransferResponse(
            success=True,
            from_wallet=WalletResponse.model_validate(from_wallet),
            to_wallet=WalletResponse.model_validate(to_wallet),
            transferred_amount=transfer.amount,
            received_amount=target_amount,
            exchange_rate=exchange_rate,
        ),
        201,
    )


async def create_bulk_operations(
    db: AsyncSession, user: User, bulk_request: BulkOperationsCreateSchema
) -> list[OperationResponse]:
    """
    Создает несколько операций за один раз с поддержкой транзакций
    Все операции выполняются атомарно: при ошибке откатываются все изменения
    Args:
        db: Сессия базы данных
        user: Текущий пользователь
        bulk_request: Данные для массовых операций (список операций доходов и расходов)
    Returns:
        Список созданных операций в формате OperationResponse
    Raises:
        HTTPException: Если кошелек не найден
    """
    try:
        unique_wallet_ids = {operation.wallet_id for operation in bulk_request.operations}
        wallet_cache = {}
        projected_balances = {}

        for wallet_id in unique_wallet_ids:
            wallet = await wallets_repository.get_wallet_by_id_without_user_check(db, wallet_id)
            if not wallet:
                raise HTTPException(status_code=404, detail=f"Кошелек {wallet_id} не найден")
            if wallet.user_id != user.id:
                raise HTTPException(status_code=403, detail="Это не ваш кошелек")
            wallet_cache[wallet_id] = wallet
            projected_balances[wallet_id] = wallet.balance

        operations_payload = []
        for operation in bulk_request.operations:
            wallet = wallet_cache[operation.wallet_id]
            current_balance = projected_balances[operation.wallet_id]

            if operation.operation_type == OperationType.INCOME:
                new_balance = round(current_balance + operation.amount, 2)
                operations_payload.append(
                    {
                        "wallet_id": operation.wallet_id,
                        "type": OperationType.INCOME.value,
                        "amount": operation.amount,
                        "currency": wallet.currency,
                        "category": operation.description,
                    }
                )
                projected_balances[operation.wallet_id] = new_balance

            elif operation.operation_type == OperationType.EXPENSE:
                if current_balance < operation.amount:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Недостаточно средств для кошелька {operation.wallet_id}",
                    )
                new_balance = round(current_balance - operation.amount, 2)
                operations_payload.append(
                    {
                        "wallet_id": operation.wallet_id,
                        "type": OperationType.EXPENSE.value,
                        "amount": operation.amount,
                        "currency": wallet.currency,
                        "category": operation.category,
                        "subcategory": operation.subcategory,
                    }
                )
                projected_balances[operation.wallet_id] = new_balance

        for wallet_id, wallet in wallet_cache.items():
            wallet.balance = projected_balances[wallet_id]

        created_operations = await operations_repository.create_operations_bulk(
            db, operations_payload
        )
        await db.commit()

        for wallet in wallet_cache.values():
            await db.refresh(wallet)

        return [OperationResponse.model_validate(op) for op in created_operations]

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def generate_csv_report(
    db: AsyncSession,
    user: User,
    date_from: str,
    date_to: str,
    currency: str,
) -> str:
    """
    Генерирует CSV отчёт с операциями пользователя за указанный период с конвертацией валют
    Args:
        db: Сессия базы данных
        user: Текущий пользователь
        date_from: Начальная дата в формате yyyy-mm-dd
        date_to: Конечная дата в формате yyyy-mm-dd
        currency: Целевая валюта для конвертации всех сумм
    Returns:
        CSV строка с заголовками и данными операций
    """
    date_from_dt = datetime.strptime(date_from, "%Y-%m-%d").replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    date_to_dt = datetime.strptime(date_to, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59, microsecond=999999
    )

    operations = await get_operations_list(
        db, user, wallet_id=None, date_from=date_from_dt, date_to=date_to_dt
    )

    target_currency = CurrencyEnum(currency.lower())
    csv_lines = ["date,type,wallet_id,amount,category,currency"]

    for operation in operations:
        date_str = operation.created_at.strftime("%Y-%m-%d %H:%M:%S")
        type_str = operation.type
        wallet_id_str = str(operation.wallet_id)

        if operation.currency == target_currency:
            converted_amount = float(operation.amount)
        else:
            exchange_rate = await get_exchange_rate(operation.currency, target_currency)
            converted_amount = float(operation.amount) * float(exchange_rate)

        amount_str = f"{converted_amount:.2f}"
        category = operation.category or ""
        category = category.replace("\n", " ").replace("\r", " ")
        csv_line = f"{date_str},{type_str},{wallet_id_str},{amount_str},{category},{currency}"
        csv_lines.append(csv_line)

    csv_content = "\n".join(csv_lines)
    return csv_content
