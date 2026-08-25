import logging
import traceback

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import app.repository.users as users_repository
from app.models import Group, User
from app.repository import groups as groups_repository
from app.schemas import GroupCreateSchema, GroupResponseSchema

logger = logging.getLogger(__name__)


async def create_group(
    db: AsyncSession, current_user: User, group_data: GroupCreateSchema
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
    try:
        # 1. Проверка на дубликат
        if await groups_repository.is_group_exist(
            db, user_id=current_user.id, group_name=group_data.name
        ):
            raise HTTPException(
                status_code=400, detail="Нельзя создавать несколько групп с одинаковым названием"
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
                    status_code=400, detail=f"Пользователь с логином '{login}' не найден"
                )
            members.append(user)

        # 4. Убираем создателя из списка участников (безопасно по ID)
        other_members = [m for m in members if m.id != current_user.id]

        # 5. Проверяем, что остался хотя бы один участник помимо создателя группы
        if not other_members:
            raise HTTPException(
                status_code=400, detail="Добавьте хотя бы одного участника помимо себя"
            )

        new_group: Group = await groups_repository.create_group(
            db, creator_id=current_user.id, group_name=group_data.name, members=other_members
        )

        logger.info(f"Group created: {new_group.id}")
        logger.info(f"Members: {new_group.members}")

        await db.commit()
        return GroupResponseSchema.model_validate(obj=new_group)

    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        raise


async def get_current_user_groups(
    db: AsyncSession, current_user: User
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
    return [GroupResponseSchema.model_validate(group) for group in groups]


# async def get_group_by_id(db: AsyncSession, user_id: int, group_id: int) -> Group | None:
#     result = await db.execute(
#         select(Group).where(Group.id == group_id, Group.user_id == user_id)
#     )
#     return result.scalar_one_or_none()
