from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency import get_current_user, get_db
from app.models import User
from app.schemas import CreateWalletRequest, WalletResponse
from app.service import wallets as wallets_service

router = APIRouter()


@router.get("/balance")
async def get_balance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await wallets_service.get_total_balance(db, current_user)


@router.post("/wallets", response_model=WalletResponse, status_code=201)
async def create_wallet(
    wallet: CreateWalletRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await wallets_service.create_wallet(db, current_user, wallet)


@router.get("/wallets", response_model=list[WalletResponse])
async def get_all_wallets(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return await wallets_service.get_all_wallets(db, current_user)
