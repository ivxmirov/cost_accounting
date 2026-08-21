from fastapi import (
    APIRouter,
    Depends,
    Response,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency import get_current_user, get_db
from app.models import User
from app.schemas import (
    TransferCreateSchemaV2,
    TransferResponseSchema,
)
from app.service import operations as operations_service

router = APIRouter()


@router.put("/operations/transfer", response_model=TransferResponseSchema)
async def create_transfer_v2(
    transfer_data: TransferCreateSchemaV2,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result, status_code = await operations_service.transfer_between_wallets_v2(
        db,
        transfer_data,
        user.id,
    )
    response.status_code = status_code
    return result
