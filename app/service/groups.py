import logging

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import app.repository.users as users_repository
from app.models import Group, User
from app.repository import groups as groups_repository
from app.schemas import GroupCreateSchema, GroupResponseSchema

logger = logging.getLogger(__name__)


async def create_group(
    db: AsyncSession, current_user: User, group_data: GroupCreateSchema,
) -> GroupResponseSchema:
    """
    Создает новую группу с бизнес-валидацией.

    Бизнес-правила:
    1. Группа с таким названием у пользователя-создателя не должна существовать
    2. Минимум 2 участника (создатель + минимум 1 дополнительный)
    3. Создатель не может быть в списке дополнительных участников

    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
        group_data: Данные для создания группы (название, члены группы)
    Returns:
        Информация о созданной группе
    Raises:
        HTTPException: Если группа с таким названием уже существует
        HTTPException: Если создатель в списке участников
        HTTPException: Если какой-то пользователь не найден
    """
    # 1. Проверка на дубликат
    if await groups_repository.is_group_exist(
        db, user_id=current_user.id, group_name=group_data.name,
    ):
        raise HTTPException(
            status_code=400, detail="Нельзя создавать несколько групп с одинаковым названием",
        )

    # 2. Проверка, что в группу добавлен хотя бы один участник
    if len(group_data.members_logins) == 0:
        raise HTTPException(status_code=400, detail="Добавьте хотя бы одного участника")

    # 3. Получаем всех участников по логинам с проверкой на существование
    members = []
    for login in group_data.members_logins:
        user = await users_repository.get_user(db, login)
        if not user:
            raise HTTPException(
                status_code=400, detail=f"Пользователь с логином '{login}' не найден",
            )
        members.append(user)

    # 4. Убираем создателя из списка участников (безопасно по ID)
    other_members = [m for m in members if m.id != current_user.id]

    # 5. Проверяем, что остался хотя бы один участник помимо создателя группы
    if not other_members:
        raise HTTPException(status_code=400, detail="Добавьте хотя бы одного участника помимо себя")

    new_group: Group = await groups_repository.create_group(
        db, creator_id=current_user.id, group_name=group_data.name, members=other_members,
    )

    await db.commit()
    return GroupResponseSchema.model_validate(obj=new_group)


async def get_current_user_groups(
    db: AsyncSession, current_user: User,
) -> list[GroupResponseSchema]:
    """
    Возвращает список всех групп, в которых состоит текущий пользователь.

    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
    Returns:
        Список всех групп, в которых состоит текущий пользователь
    """
    groups = await groups_repository.get_user_groups(db, user_id=current_user.id)
    result = []
    for group in groups:
        schema = GroupResponseSchema(
            name=group.name,
            creator=group.creator,
            creator_login=(
                group.creator_user.login if group.creator_user else f"User_{group.creator}"
            ),
            members=[member.login for member in group.members],
            created_at=group.created_at,
        )
        result.append(schema)

    return result


async def get_user_group_by_id(
    db: AsyncSession, current_user: User, group_id: int,
) -> GroupResponseSchema:
    """Получает группу с проверкой прав доступа пользователя"""

    group = await groups_repository.get_group_by_id(db, group_id)

    if not group:
        raise HTTPException(status_code=404, detail="Такой группы не существует")

    # Проверяем, является ли пользователь участником группы
    if current_user.id not in [member.id for member in group.members]:
        raise HTTPException(status_code=403, detail="Вы не состоите в этой группе")

    return GroupResponseSchema(
        name=group.name,
        creator=group.creator,
        creator_login=group.creator_user.login if group.creator_user else f"User_{group.creator}",
        members=[member.login for member in group.members],
        created_at=group.created_at,
    )
