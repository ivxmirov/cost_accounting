from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency import get_current_user, get_db
from app.models import User
from app.schemas import GroupResponseSchema
from app.service import groups as groups_service

router = APIRouter()


@router.get("/users/me/groups", response_model=list[GroupResponseSchema])
async def get_my_groups_v2(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await groups_service.get_current_user_groups(db, current_user)
