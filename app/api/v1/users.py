from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency import get_current_user, get_db
from app.models import User
from app.schemas import UserRequest, UserResponseSchema
from app.service import users as users_service

router = APIRouter()


@router.post("/users", response_model=UserResponseSchema, status_code=201)
async def create_user(
    payload: UserRequest,
    db: AsyncSession = Depends(get_db),
):
    return await users_service.create_user(db, payload.login, payload.password)


@router.get("/users/me", response_model=UserResponseSchema)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return UserResponseSchema.model_validate(current_user)
