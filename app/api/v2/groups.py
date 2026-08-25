from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency import get_current_user, get_db
from app.models import User
from app.schemas import GroupCreateSchema, GroupResponseSchema
from app.service import groups as groups_service

router = APIRouter()


@router.post(path="/groups/", response_model=GroupResponseSchema, status_code=201)
async def create_group_v2(
    group: GroupCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await groups_service.create_group(db, current_user, group)
