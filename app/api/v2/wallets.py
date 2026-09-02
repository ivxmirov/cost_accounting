from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency import get_current_user, get_db
from app.models import User
from app.service import wallets as wallets_service

router = APIRouter()


@router.delete(
    path="/wallets/{wallet_id}",
    status_code=200,
)
async def delete_wallet_v2(
    wallet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Удаляет кошелек текущего пользователя по ID.
    """
    result = await wallets_service.delete_wallet_by_id(db, current_user, wallet_id)
    return result
