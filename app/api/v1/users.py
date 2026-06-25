from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependency import get_current_user as get_user
from app.dependency import get_db
from app.models import User
from app.schemas import UserRequest, UserResponse
from app.service import users as users_service

router = APIRouter()


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(payload: UserRequest, db: Session = Depends(get_db)):
    return users_service.create_user(db, payload.login)


@router.get("/users/me", response_model=UserResponse)
def get_current_user(current_user: User = Depends(get_user)):
    return UserResponse.model_validate(current_user)
