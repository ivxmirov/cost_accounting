from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency import get_current_user, get_db
from app.models import User
from app.schemas import WalletCreateSchema, WalletResponseSchema, WalletTableSchema
from app.service import wallets as wallets_service

router = APIRouter()


@router.get("/balance")
async def get_balance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await wallets_service.get_total_user_balance(db, current_user)


@router.post("/wallets", response_model=WalletResponseSchema, status_code=201)
async def create_wallet(
    wallet: WalletCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await wallets_service.create_wallet(db, current_user, wallet)


@router.get("/wallets", response_model=list[WalletTableSchema])
async def get_user_wallets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await wallets_service.get_user_wallets_with_effective_balance(db, current_user.id)


@router.delete(
    path="/wallets/{wallet_id}",
    status_code=200,
)
async def delete_wallet(
    wallet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Удаляет кошелек текущего пользователя по ID.
    """
    result = await wallets_service.delete_wallet_by_id(db, current_user, wallet_id)
    return result
