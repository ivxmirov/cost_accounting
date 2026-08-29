from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Group
from app.repository import groups as groups_repository


async def test_create_group_without_adding_members_not_exists(
    db_session: AsyncSession,
    current_user,
):
    group: Group = await groups_repository.create_group(
        db_session,
        creator_id=current_user.id,
        group_name="test_group",
    )

    # members уже загружен через selectinload в репозитории
    assert group.id == 1
    assert group.creator == current_user.id
    assert group.name == "test_group"
    assert len(group.members) == 1
    assert group.members[0].id == current_user.id
