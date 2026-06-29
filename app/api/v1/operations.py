from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency import get_current_user, get_db
from app.models import User
from app.schemas import OperationRequest, OperationResponse, TransferCreateSchema
from app.service import operations as operations_service
from app.service.operations import transfer_between_wallets

router = APIRouter()


@router.post("/operations/income", status_code=201)
async def add_income(
    operation: OperationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await operations_service.add_income(db, current_user, operation)


@router.post("/operations/expense", status_code=201)
async def add_expense(
    operation: OperationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await operations_service.add_expense(db, current_user, operation)


@router.get("/operations", response_model=list[OperationResponse])
async def get_operations_list(
    wallet_id: int | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await operations_service.get_operations_list(db, user, wallet_id, date_from, date_to)


@router.post("/operations/transfer", response_model=OperationResponse, status_code=201)
async def create_transfer(
    payload: TransferCreateSchema,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await transfer_between_wallets(
        db=db,
        user_id=user.id,
        from_wallet_id=payload.from_wallet_id,
        to_wallet_id=payload.to_wallet_id,
        amount=payload.amount,
    )
