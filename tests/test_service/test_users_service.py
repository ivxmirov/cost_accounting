import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.service import users as users_service


async def test_create_user_success(db_session: AsyncSession):
    user = await users_service.create_user(db_session, "test", "testpassword123")

    assert user.login == "test"
    assert user.id == 1


async def test_create_user_user_exists(db_session: AsyncSession, current_user):
    with pytest.raises(HTTPException) as exc:
        await users_service.create_user(db_session, current_user.login, "testpassword123")

    assert exc.value.status_code == 400
