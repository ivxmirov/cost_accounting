from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency import get_current_user, get_db
from app.models import User
from app.schemas import (
    BulkOperationsCreateSchema,
    ExpenseCreateSchema,
    IncomeCreateSchema,
    OperationResponse,
    TransferCreateSchema,
)
from app.service import operations as operations_service

router = APIRouter()


@router.put("/operations/income", response_model=OperationResponse)
async def add_income(
    operation: IncomeCreateSchema,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result, status_code = await operations_service.add_income(db, current_user, operation)
    response.status_code = status_code
    return result


@router.put("/operations/expense", response_model=OperationResponse)
async def add_expense(
    operation: ExpenseCreateSchema,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result, status_code = await operations_service.add_expense(db, current_user, operation)
    response.status_code = status_code
    return result


@router.get("/operations", response_model=list[OperationResponse])
async def get_operations_list(
    wallet_id: int | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await operations_service.get_operations_list(db, user, wallet_id, date_from, date_to)


@router.put("/operations/transfer", response_model=OperationResponse)
async def create_transfer(
    payload: TransferCreateSchema,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result, status_code = await operations_service.transfer_between_wallets(
        db,
        user.id,
        payload.transaction_id,
        payload.from_wallet_id,
        payload.to_wallet_id,
        payload.amount,
    )
    response.status_code = status_code
    return result


@router.post("/operations/bulk", response_model=list[OperationResponse], status_code=201)
async def create_bulk_operations(
    bulk_request: BulkOperationsCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await operations_service.create_bulk_operations(db, current_user, bulk_request)


@router.get("/reports")
async def get_csv_report(
    date_from: str = Query(..., description="Начальная дата в формате yyyy-mm-dd"),
    date_to: str = Query(..., description="Конечная дата в формате yyyy-mm-dd"),
    currency: str = Query("RUB", description="Целевая валюта для конвертации"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    csv_content = await operations_service.generate_csv_report(
        db, user, date_from, date_to, currency,
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{date_from}_{date_to}.csv"},
    )
