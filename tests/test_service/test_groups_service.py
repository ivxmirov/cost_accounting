from decimal import Decimal

import aiohttp
import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.enum import CurrencyEnum, WalletType
from app.models import Group, User, Wallet
from app.schemas import GroupCreateSchema
from app.service import groups as groups_service

# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def group(db_session: AsyncSession, test_user: User, second_user: User) -> Group:
    """Группа, созданная test_user с участием second_user."""
    payload = GroupCreateSchema(name="Test Group", members_logins=[second_user.login])
    created = await groups_service.create_group(db_session, test_user, payload)
    group_obj = await db_session.get(Group, created.id)
    assert group_obj is not None
    return group_obj


@pytest_asyncio.fixture
async def rub_wallet(db_session: AsyncSession, test_user: User) -> Wallet:
    """Дебетовый рублёвый кошелек — не требует обращения к курсовому API."""
    wallet = Wallet(
        name="rub_wallet",
        balance=Decimal("500"),
        user_id=test_user.id,
        currency=CurrencyEnum.RUB,
        type=WalletType.DEBIT,
        credit_limit=None,
    )
    db_session.add(wallet)
    await db_session.commit()
    await db_session.refresh(wallet)
    return wallet


@pytest_asyncio.fixture
async def second_user_rub_wallet(db_session: AsyncSession, second_user: User) -> Wallet:
    """Рублевый кошелек второго участника группы."""
    wallet = Wallet(
        name="buddy_wallet",
        balance=Decimal("300"),
        user_id=second_user.id,
        currency=CurrencyEnum.RUB,
        type=WalletType.DEBIT,
        credit_limit=None,
    )
    db_session.add(wallet)
    await db_session.commit()
    await db_session.refresh(wallet)
    return wallet


@pytest.fixture
def stub_rate(monkeypatch):
    """Подменяет курс валют, чтобы тесты не зависели от внешнего API."""

    def _stub(rate: Decimal):
        async def fake_get_exchange_rate(base, target):  # noqa: ARG001
            return rate

        monkeypatch.setattr(
            "app.service.exchange_service.get_exchange_rate",
            fake_get_exchange_rate,
        )

    return _stub


# ---------------------------------------------------------------------------
# create_group
# ---------------------------------------------------------------------------


async def test_create_group_success(db_session: AsyncSession, test_user: User, second_user: User):
    """Группа создаётся, создатель и участники попадают в список."""
    payload = GroupCreateSchema(name="Friends", members_logins=[second_user.login])

    result = await groups_service.create_group(db_session, test_user, payload)

    assert result.name == "Friends"
    assert result.creator == test_user.id
    assert result.creator_login == test_user.login
    assert sorted(result.members) == sorted([test_user.login, second_user.login])
    assert result.total_balance == Decimal("0")
    assert result.member_balances == []
    assert result.wallets == []
    assert result.created_at is not None


async def test_create_group_deduplicates_member_logins(
    db_session: AsyncSession, test_user: User, second_user: User
):
    """Дубликаты логинов схлопываются в одного участника."""
    payload = GroupCreateSchema(
        name="Dedup Group",
        members_logins=[second_user.login, second_user.login],
    )

    result = await groups_service.create_group(db_session, test_user, payload)

    assert result.members.count(second_user.login) == 1


async def test_create_group_skips_creator_in_members(
    db_session: AsyncSession, test_user: User, second_user: User
):
    """Если создатель перечислен в members_logins, он не дублируется в составе."""
    payload = GroupCreateSchema(
        name="Self In List",
        members_logins=[test_user.login, second_user.login],
    )

    result = await groups_service.create_group(db_session, test_user, payload)

    assert result.members.count(test_user.login) == 1
    assert second_user.login in result.members


async def test_create_group_duplicate_name_raises_400(
    db_session: AsyncSession,
    test_user: User,
    second_user: User,
    group: Group,  # noqa: ARG001
):
    """Нельзя создать вторую группу с таким же названием у того же создателя."""
    payload = GroupCreateSchema(name="Test Group", members_logins=[second_user.login])

    with pytest.raises(HTTPException) as exc:
        await groups_service.create_group(db_session, test_user, payload)

    assert exc.value.status_code == 400
    assert "одинаковым названием" in exc.value.detail


async def test_create_group_same_name_other_creator_is_allowed(
    db_session: AsyncSession, group: Group, other_group_creator: User, second_user: User
):
    """Другой пользователь может создать группу с тем же названием."""
    payload = GroupCreateSchema(name="Test Group", members_logins=[second_user.login])

    result = await groups_service.create_group(db_session, other_group_creator, payload)

    assert result.id != group.id
    assert result.name == "Test Group"


async def test_create_group_unknown_member_raises_400(db_session: AsyncSession, test_user: User):
    """Логин несуществующего пользователя приводит к 400."""
    payload = GroupCreateSchema(name="Ghost Group", members_logins=["nobody_here"])

    with pytest.raises(HTTPException) as exc:
        await groups_service.create_group(db_session, test_user, payload)

    assert exc.value.status_code == 400
    assert "не найден" in exc.value.detail


async def test_create_group_without_extra_members_raises_400(
    db_session: AsyncSession, test_user: User
):
    """Пустой список участников запрещён — нужен хотя бы один человек кроме создателя."""
    payload = GroupCreateSchema(name="Lonely Group", members_logins=[])

    with pytest.raises(HTTPException) as exc:
        await groups_service.create_group(db_session, test_user, payload)

    assert exc.value.status_code == 400
    assert "хотя бы одного участника" in exc.value.detail


async def test_create_group_only_self_raises_400(db_session: AsyncSession, test_user: User):
    """Список из одного создателя тоже запрещён."""
    payload = GroupCreateSchema(name="Solo", members_logins=[test_user.login])

    with pytest.raises(HTTPException) as exc:
        await groups_service.create_group(db_session, test_user, payload)

    assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# delete_group
# ---------------------------------------------------------------------------


async def test_delete_group_success(db_session: AsyncSession, test_user: User, group: Group):
    """Создатель удаляет группу — она исчезает из БД."""
    await groups_service.delete_group(db_session, test_user, group.id)

    assert await db_session.get(Group, group.id) is None


async def test_delete_group_not_found(db_session: AsyncSession, test_user: User):
    with pytest.raises(HTTPException) as exc:
        await groups_service.delete_group(db_session, test_user, 9999)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Такой группы не существует"


async def test_delete_group_not_creator(db_session: AsyncSession, second_user: User, group: Group):
    """Участник, но не создатель, группу удалить не может."""
    with pytest.raises(HTTPException) as exc:
        await groups_service.delete_group(db_session, second_user, group.id)

    assert exc.value.status_code == 403
    assert "Только создатель" in exc.value.detail


async def test_delete_group_by_outsider(db_session: AsyncSession, group: Group, third_user: User):
    """Сторонний пользователь тоже получает 403."""
    with pytest.raises(HTTPException) as exc:
        await groups_service.delete_group(db_session, third_user, group.id)

    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# get_current_user_groups
# ---------------------------------------------------------------------------


async def test_get_current_user_groups_empty(db_session: AsyncSession, test_user: User):
    result = await groups_service.get_current_user_groups(db_session, test_user)

    assert result == []


async def test_get_current_user_groups_sorted_by_name(
    db_session: AsyncSession, test_user: User, second_user: User
):
    """Список групп отсортирован по названию без учёта регистра."""
    for name in ("beta", "Alpha", "gamma"):
        await groups_service.create_group(
            db_session, test_user, GroupCreateSchema(name=name, members_logins=[second_user.login])
        )

    result = await groups_service.get_current_user_groups(db_session, test_user)

    assert [g.name for g in result] == ["Alpha", "beta", "gamma"]
    assert all(g.members_count == 2 for g in result)
    assert all(g.creator_id == test_user.id for g in result)


async def test_get_current_user_groups_calculates_balance(
    db_session: AsyncSession,
    test_user: User,
    group: Group,
    rub_wallet: Wallet,
    db,  # noqa: ARG001
):
    """В список попадает суммарный баланс прикреплённых кошельков."""
    await groups_service.attach_wallet_to_group(db_session, test_user, group.id, rub_wallet.id)

    result = await groups_service.get_current_user_groups(db_session, test_user)

    assert len(result) == 1
    assert result[0].total_balance == Decimal("500")


# ---------------------------------------------------------------------------
# get_user_group_by_id
# ---------------------------------------------------------------------------


async def test_get_user_group_by_id_success(
    db_session: AsyncSession,
    test_user: User,
    second_user: User,
    group: Group,
    rub_wallet: Wallet,
    second_user_rub_wallet: Wallet,
):
    """Детальная информация о группе: баланс, участники, кошельки."""
    await groups_service.attach_wallet_to_group(db_session, test_user, group.id, rub_wallet.id)
    await groups_service.attach_wallet_to_group(
        db_session, second_user, group.id, second_user_rub_wallet.id
    )

    result = await groups_service.get_user_group_by_id(db_session, test_user, group.id)

    assert result.id == group.id
    assert result.name == "Test Group"
    assert result.creator_login == test_user.login
    assert result.total_balance == Decimal("800")
    # текущий пользователь идёт первым в списке участников
    assert result.members[0] == test_user.login
    assert set(result.members) == {test_user.login, second_user.login}
    # в детальном ответе только кошельки текущего пользователя
    assert [w.id for w in result.wallets] == [rub_wallet.id]
    assert result.member_balances[0].login == test_user.login
    assert result.member_balances[0].effective_balance == Decimal("500")
    assert result.member_balances[1].login == second_user.login


async def test_get_user_group_by_id_group_not_found(db_session: AsyncSession, test_user: User):
    with pytest.raises(HTTPException) as exc:
        await groups_service.get_user_group_by_id(db_session, test_user, 4242)

    assert exc.value.status_code == 404


async def test_get_user_group_by_id_not_a_member(
    db_session: AsyncSession, group: Group, third_user: User
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.get_user_group_by_id(db_session, third_user, group.id)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Вы не являетесь участником этой группы"


# ---------------------------------------------------------------------------
# get_user_group_wallets
# ---------------------------------------------------------------------------


async def test_get_user_group_wallets_success(
    db_session: AsyncSession,
    test_user: User,
    group: Group,
    rub_wallet: Wallet,
    second_user_rub_wallet: Wallet,
    second_user: User,
):
    """Возвращаются только кошельки текущего пользователя, прикреплённые к группе."""
    await groups_service.attach_wallet_to_group(db_session, test_user, group.id, rub_wallet.id)
    await groups_service.attach_wallet_to_group(
        db_session, second_user, group.id, second_user_rub_wallet.id
    )

    result = await groups_service.get_user_group_wallets(db_session, test_user, group.id)

    assert [w.id for w in result] == [rub_wallet.id]
    assert result[0].effective_balance == Decimal("500")


async def test_get_user_group_wallets_sorted_by_name(
    db_session: AsyncSession, test_user: User, group: Group, db
):
    """Кошельки отсортированы по названию без учёта регистра."""
    wallet_z = Wallet(
        name="zeta",
        balance=Decimal("10"),
        user_id=test_user.id,
        currency=CurrencyEnum.RUB,
        type=WalletType.DEBIT,
        credit_limit=None,
    )
    wallet_a = Wallet(
        name="Alpha",
        balance=Decimal("20"),
        user_id=test_user.id,
        currency=CurrencyEnum.RUB,
        type=WalletType.DEBIT,
        credit_limit=None,
    )
    db.add_all([wallet_z, wallet_a])
    await db_session.commit()

    await groups_service.attach_wallet_to_group(db_session, test_user, group.id, wallet_z.id)
    await groups_service.attach_wallet_to_group(db_session, test_user, group.id, wallet_a.id)

    result = await groups_service.get_user_group_wallets(db_session, test_user, group.id)

    assert [w.name for w in result] == ["Alpha", "zeta"]


async def test_get_user_group_wallets_empty(
    db_session: AsyncSession, test_user: User, group: Group
):
    assert await groups_service.get_user_group_wallets(db_session, test_user, group.id) == []


async def test_get_user_group_wallets_group_not_found(db_session: AsyncSession, test_user: User):
    with pytest.raises(HTTPException) as exc:
        await groups_service.get_user_group_wallets(db_session, test_user, 777)

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Расчёт балансов
# ---------------------------------------------------------------------------


async def test_calculate_wallet_effective_balance_rub_no_api_call(rub_wallet: Wallet, monkeypatch):
    """Для рублей курс не запрашивается — берётся эффективный баланс кошелька."""

    def fail(*args, **kwargs):  # noqa: ARG001 - защита от сетевого вызова
        raise AssertionError("Для RUB обращаться к курсовому API нельзя")

    monkeypatch.setattr("app.service.exchange_service.get_exchange_rate", fail)

    assert await groups_service.calculate_wallet_effective_balance(rub_wallet) == Decimal("500")


async def test_calculate_wallet_effective_balance_credit_wallet(credit_wallet: Wallet, stub_rate):
    """Кредитный кошелек: эффективный баланс = balance - credit_limit, затем курс."""
    stub_rate(Decimal("2"))
    # credit_wallet в RUB (effective = 2000 - 50000), курс не вызывается
    assert await groups_service.calculate_wallet_effective_balance(credit_wallet) == Decimal(
        "2000"
    ) - Decimal("50000")


async def test_calculate_wallet_effective_balance_foreign_currency(debit_wallet: Wallet, stub_rate):
    """Валютный кошелек конвертируется по курсу в рубли."""
    stub_rate(Decimal("95"))

    result = await groups_service.calculate_wallet_effective_balance(debit_wallet)

    assert result == Decimal("95") * Decimal("1000")


async def test_calculate_group_balance_sums_all_members(
    db_session: AsyncSession,
    test_user: User,
    second_user: User,
    group: Group,
    rub_wallet: Wallet,
    second_user_rub_wallet: Wallet,
):
    await groups_service.attach_wallet_to_group(db_session, test_user, group.id, rub_wallet.id)
    await groups_service.attach_wallet_to_group(
        db_session, second_user, group.id, second_user_rub_wallet.id
    )

    assert await groups_service.calculate_group_balance(db_session, group.id) == Decimal("800")


async def test_calculate_group_balance_empty_group(db_session: AsyncSession, group: Group):
    assert await groups_service.calculate_group_balance(db_session, group.id) == Decimal("0")


async def test_calculate_group_balance_with_conversion(
    db_session: AsyncSession, test_user: User, group: Group, debit_wallet: Wallet, stub_rate
):
    """Валютный кошелек учитывается в рублях."""
    stub_rate(Decimal("10"))
    await groups_service.attach_wallet_to_group(db_session, test_user, group.id, debit_wallet.id)

    assert await groups_service.calculate_group_balance(db_session, group.id) == Decimal("10000")


async def test_calculate_member_balances_groups_by_login(
    db_session: AsyncSession,
    test_user: User,
    second_user: User,
    group: Group,
    rub_wallet: Wallet,
    second_user_rub_wallet: Wallet,
):
    await groups_service.attach_wallet_to_group(db_session, test_user, group.id, rub_wallet.id)
    await groups_service.attach_wallet_to_group(
        db_session, second_user, group.id, second_user_rub_wallet.id
    )

    result = await groups_service.calculate_member_balances(db_session, group.id)

    assert {m.login: m.effective_balance for m in result} == {
        test_user.login: Decimal("500"),
        second_user.login: Decimal("300"),
    }


async def test_calculate_member_balances_sums_multiple_wallets_of_one_user(
    db_session: AsyncSession, test_user: User, group: Group, rub_wallet: Wallet, db
):
    """Несколько кошельков одного участника суммируются в одну запись."""
    second = Wallet(
        name="extra_wallet",
        balance=Decimal("250"),
        user_id=test_user.id,
        currency=CurrencyEnum.RUB,
        type=WalletType.DEBIT,
        credit_limit=None,
    )
    db.add(second)
    await db_session.commit()

    await groups_service.attach_wallet_to_group(db_session, test_user, group.id, rub_wallet.id)
    await groups_service.attach_wallet_to_group(db_session, test_user, group.id, second.id)

    result = await groups_service.calculate_member_balances(db_session, group.id)

    assert len(result) == 1
    assert result[0].login == test_user.login
    assert result[0].effective_balance == Decimal("750")


async def test_calculate_member_balances_empty_group(db_session: AsyncSession, group: Group):
    assert await groups_service.calculate_member_balances(db_session, group.id) == []


# ---------------------------------------------------------------------------
# attach_wallet_to_group
# ---------------------------------------------------------------------------


async def test_attach_wallet_to_group_success(
    db_session: AsyncSession, test_user: User, group: Group, rub_wallet: Wallet
):
    updated = await groups_service.attach_wallet_to_group(
        db_session, test_user, group.id, rub_wallet.id
    )

    assert updated is not None
    # Проверяем через отдельный запрос, чтобы relationship обновился
    await db_session.refresh(updated, ["wallets"])
    assert [w.id for w in updated.wallets] == [rub_wallet.id]


async def test_attach_wallet_group_not_found(
    db_session: AsyncSession, test_user: User, rub_wallet: Wallet
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.attach_wallet_to_group(db_session, test_user, 321, rub_wallet.id)

    assert exc.value.status_code == 404


async def test_attach_wallet_not_a_member(
    db_session: AsyncSession, group: Group, third_user: User, rub_wallet: Wallet
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.attach_wallet_to_group(db_session, third_user, group.id, rub_wallet.id)

    assert exc.value.status_code == 403


async def test_attach_wallet_not_owned_by_user(
    db_session: AsyncSession, test_user: User, group: Group, second_user_rub_wallet: Wallet
):
    """Чужой кошелек прикрепить нельзя."""
    with pytest.raises(HTTPException) as exc:
        await groups_service.attach_wallet_to_group(
            db_session, test_user, group.id, second_user_rub_wallet.id
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "У вас нет такого кошелька"


async def test_attach_wallet_already_attached(
    db_session: AsyncSession, test_user: User, group: Group, rub_wallet: Wallet
):
    await groups_service.attach_wallet_to_group(db_session, test_user, group.id, rub_wallet.id)

    with pytest.raises(HTTPException) as exc:
        await groups_service.attach_wallet_to_group(db_session, test_user, group.id, rub_wallet.id)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Кошелек уже прикреплен к группе"


# ---------------------------------------------------------------------------
# detach_wallet_from_group
# ---------------------------------------------------------------------------


async def test_detach_wallet_from_group_success(
    db_session: AsyncSession, test_user: User, group: Group, rub_wallet: Wallet
):
    await groups_service.attach_wallet_to_group(db_session, test_user, group.id, rub_wallet.id)

    updated = await groups_service.detach_wallet_from_group(
        db_session, test_user, group.id, rub_wallet.id
    )

    assert updated is not None
    assert updated.wallets == []


async def test_detach_wallet_group_not_found(
    db_session: AsyncSession, test_user: User, rub_wallet: Wallet
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.detach_wallet_from_group(db_session, test_user, 55, rub_wallet.id)

    assert exc.value.status_code == 404


async def test_detach_wallet_not_a_member(
    db_session: AsyncSession, group: Group, third_user: User, rub_wallet: Wallet
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.detach_wallet_from_group(
            db_session, third_user, group.id, rub_wallet.id
        )

    assert exc.value.status_code == 403


async def test_detach_wallet_not_owned(
    db_session: AsyncSession, test_user: User, group: Group, second_user_rub_wallet: Wallet
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.detach_wallet_from_group(
            db_session, test_user, group.id, second_user_rub_wallet.id
        )

    assert exc.value.status_code == 404


async def test_detach_wallet_not_attached(
    db_session: AsyncSession, test_user: User, group: Group, rub_wallet: Wallet
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.detach_wallet_from_group(
            db_session, test_user, group.id, rub_wallet.id
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Кошелек не прикреплен к группе"


# ---------------------------------------------------------------------------
# leave_group
# ---------------------------------------------------------------------------


async def test_leave_group_by_creator_deletes_whole_group(
    db_session: AsyncSession, test_user: User, group: Group
):
    """Выход создателя удаляет группу целиком."""
    await groups_service.leave_group(db_session, test_user, group.id)

    assert await db_session.get(Group, group.id) is None


async def test_leave_group_by_member_detaches_wallets(
    db_session: AsyncSession,
    test_user: User,
    second_user: User,
    group: Group,
    second_user_rub_wallet: Wallet,
):
    """Участник выходит: его кошельки открепляются, группа остаётся."""
    await groups_service.attach_wallet_to_group(
        db_session, second_user, group.id, second_user_rub_wallet.id
    )

    await groups_service.leave_group(db_session, second_user, group.id)

    refreshed = await db_session.get(Group, group.id)
    assert refreshed is not None
    await db_session.refresh(refreshed, ["members", "wallets"])
    assert [m.login for m in refreshed.members] == [test_user.login]
    assert refreshed.wallets == []


async def test_leave_group_not_a_member(db_session: AsyncSession, group: Group, third_user: User):
    with pytest.raises(HTTPException) as exc:
        await groups_service.leave_group(db_session, third_user, group.id)

    assert exc.value.status_code == 403


async def test_leave_group_not_found(db_session: AsyncSession, test_user: User):
    with pytest.raises(HTTPException) as exc:
        await groups_service.leave_group(db_session, test_user, 9876)

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# add_user_to_group
# ---------------------------------------------------------------------------


async def test_add_user_to_group_success(
    db_session: AsyncSession, test_user: User, second_user: User, group: Group, third_user: User
):
    await groups_service.add_user_to_group(db_session, test_user, group.id, third_user.id)

    refreshed = await db_session.get(Group, group.id)
    assert refreshed is not None
    await db_session.refresh(refreshed, ["members"])
    assert {m.login for m in refreshed.members} == {
        test_user.login,
        second_user.login,
        third_user.login,
    }


async def test_add_user_to_group_group_not_found(
    db_session: AsyncSession, test_user: User, third_user: User
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.add_user_to_group(db_session, test_user, 4321, third_user.id)

    assert exc.value.status_code == 404


async def test_add_user_to_group_not_creator(
    db_session: AsyncSession, second_user: User, group: Group, third_user: User
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.add_user_to_group(db_session, second_user, group.id, third_user.id)

    assert exc.value.status_code == 403


async def test_add_user_to_group_user_not_found(
    db_session: AsyncSession, test_user: User, group: Group
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.add_user_to_group(db_session, test_user, group.id, 99999)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Пользователь не найден"


async def test_add_user_to_group_self(db_session: AsyncSession, test_user: User, group: Group):
    with pytest.raises(HTTPException) as exc:
        await groups_service.add_user_to_group(db_session, test_user, group.id, test_user.id)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Нельзя добавить самого себя"


async def test_add_user_to_group_already_member(
    db_session: AsyncSession, test_user: User, group: Group, second_user: User
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.add_user_to_group(db_session, test_user, group.id, second_user.id)

    assert exc.value.status_code == 400
    assert "уже является участником" in exc.value.detail


# ---------------------------------------------------------------------------
# add_users_to_group
# ---------------------------------------------------------------------------


async def test_add_users_to_group_success(
    db_session: AsyncSession,
    test_user: User,
    group: Group,
    third_user: User,
    other_group_creator: User,
):
    result = await groups_service.add_users_to_group(
        db_session, test_user, group.id, [third_user.id, other_group_creator.id]
    )

    assert result["added"] == sorted([third_user.login, other_group_creator.login]) or set(
        result["added"]
    ) == {third_user.login, other_group_creator.login}
    assert result["skipped"] == []
    assert result["not_found"] == []
    assert "Добавлено: 2" in result["message"]


async def test_add_users_to_group_mixed_outcomes(
    db_session: AsyncSession, test_user: User, group: Group, second_user: User, third_user: User
):
    """Одновременно: новый участник, уже состоящий, несуществующий."""
    result = await groups_service.add_users_to_group(
        db_session, test_user, group.id, [third_user.id, second_user.id, 123456]
    )

    assert result["added"] == [third_user.login]
    assert result["skipped"] == [second_user.login]
    assert result["not_found"] == [123456]
    assert "пропущено: 1" in result["message"]
    assert "не найдено: 1" in result["message"]


async def test_add_users_to_group_ignores_creator_and_duplicates(
    db_session: AsyncSession, test_user: User, group: Group, third_user: User
):
    """Создатель и дубликаты в запросе не ломают операцию."""
    result = await groups_service.add_users_to_group(
        db_session, test_user, group.id, [test_user.id, third_user.id, third_user.id]
    )

    assert result["added"] == [third_user.login]
    assert result["not_found"] == []


async def test_add_users_to_group_empty_list(
    db_session: AsyncSession, test_user: User, group: Group
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.add_users_to_group(db_session, test_user, group.id, [])

    assert exc.value.status_code == 400
    assert "Добавьте хотя бы одного пользователя" in exc.value.detail


async def test_add_users_to_group_only_self(
    db_session: AsyncSession, test_user: User, group: Group
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.add_users_to_group(db_session, test_user, group.id, [test_user.id])

    assert exc.value.status_code == 400
    assert "помимо себя" in exc.value.detail


async def test_add_users_to_group_not_creator(
    db_session: AsyncSession, second_user: User, group: Group, third_user: User
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.add_users_to_group(db_session, second_user, group.id, [third_user.id])

    assert exc.value.status_code == 403


async def test_add_users_to_group_group_not_found(
    db_session: AsyncSession, test_user: User, third_user: User
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.add_users_to_group(db_session, test_user, 3131, [third_user.id])

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# remove_user_from_group
# ---------------------------------------------------------------------------


async def test_remove_user_from_group_success(
    db_session: AsyncSession,
    test_user: User,
    second_user: User,
    group: Group,
    second_user_rub_wallet: Wallet,
):
    await groups_service.attach_wallet_to_group(
        db_session, second_user, group.id, second_user_rub_wallet.id
    )

    await groups_service.remove_user_from_group(db_session, test_user, group.id, second_user.id)

    refreshed = await db_session.get(Group, group.id)
    assert refreshed is not None
    await db_session.refresh(refreshed, ["members", "wallets"])
    assert [m.login for m in refreshed.members] == [test_user.login]
    assert refreshed.wallets == []


async def test_remove_user_from_group_group_not_found(
    db_session: AsyncSession, test_user: User, second_user: User
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.remove_user_from_group(db_session, test_user, 6060, second_user.id)

    assert exc.value.status_code == 404


async def test_remove_user_from_group_not_creator(
    db_session: AsyncSession, second_user: User, group: Group, third_user: User
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.remove_user_from_group(
            db_session, second_user, group.id, third_user.id
        )

    assert exc.value.status_code == 403


async def test_remove_user_from_group_self(db_session: AsyncSession, test_user: User, group: Group):
    with pytest.raises(HTTPException) as exc:
        await groups_service.remove_user_from_group(db_session, test_user, group.id, test_user.id)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Нельзя удалить самого себя"


async def test_remove_user_from_group_not_a_member(
    db_session: AsyncSession, test_user: User, group: Group, third_user: User
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.remove_user_from_group(db_session, test_user, group.id, third_user.id)

    assert exc.value.status_code == 404
    assert "не является участником" in exc.value.detail


# ---------------------------------------------------------------------------
# remove_users_from_group
# ---------------------------------------------------------------------------


async def test_remove_users_from_group_success(
    db_session: AsyncSession,
    test_user: User,
    second_user: User,
    group: Group,
    third_user: User,
):
    await groups_service.add_user_to_group(db_session, test_user, group.id, third_user.id)

    result = await groups_service.remove_users_from_group(
        db_session, test_user, group.id, [second_user.id, third_user.id]
    )

    assert set(result["removed"]) == {second_user.login, third_user.login}
    assert result["skipped"] == []
    assert result["not_found"] == []
    assert "Удалено: 2" in result["message"]


async def test_remove_users_from_group_mixed_outcomes(
    db_session: AsyncSession, test_user: User, group: Group, second_user: User, third_user: User
):
    """Одновременно: состоящий участник, посторонний, несуществующий id."""
    result = await groups_service.remove_users_from_group(
        db_session, test_user, group.id, [second_user.id, third_user.id, 987654]
    )

    assert result["removed"] == [second_user.login]
    assert result["skipped"] == [third_user.login]
    assert result["not_found"] == [987654]
    assert "пропущено: 1" in result["message"]


async def test_remove_users_from_group_empty_list(
    db_session: AsyncSession, test_user: User, group: Group
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.remove_users_from_group(db_session, test_user, group.id, [])

    assert exc.value.status_code == 400
    assert "Выберите хотя бы одного пользователя" in exc.value.detail


async def test_remove_users_from_group_includes_self(
    db_session: AsyncSession, test_user: User, group: Group, second_user: User
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.remove_users_from_group(
            db_session, test_user, group.id, [test_user.id, second_user.id]
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Нельзя удалить самого себя"


async def test_remove_users_from_group_not_creator(
    db_session: AsyncSession, second_user: User, group: Group, third_user: User
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.remove_users_from_group(
            db_session, second_user, group.id, [third_user.id]
        )

    assert exc.value.status_code == 403


async def test_remove_users_from_group_group_not_found(
    db_session: AsyncSession, test_user: User, second_user: User
):
    with pytest.raises(HTTPException) as exc:
        await groups_service.remove_users_from_group(db_session, test_user, 1010, [second_user.id])

    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Реальный путь через exchange_service
# ---------------------------------------------------------------------------
# aioresponses 0.7.9 несовместим с aiohttp>=3.14 (ClientResponse требует
# keyword-only `stream_writer`), поэтому мок ставится на уровень
# aiohttp.ClientSession.get - это не зависит от внутренностей aiohttp.


class _FakeResponse:
    """Минимальная замена aiohttp.ClientResponse для контекст-менеджа."""

    def __init__(self, payload, status=200):
        self._payload = payload
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise aiohttp.ClientConnectionError(f"HTTP {self.status}")

    async def json(self):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


def _patch_exchange_api(monkeypatch, payload=None, status=200):
    """Заставляет exchange_service получить указанный JSON вместо реального API."""

    def fake_get(self, url, **kwargs):  # noqa: ARG001
        return _FakeResponse(payload=payload, status=status)

    monkeypatch.setattr(aiohttp.ClientSession, "get", fake_get)


async def test_effective_balance_uses_real_exchange_service(debit_wallet: Wallet, monkeypatch):
    """USD-кошелек: курс читается из ответа API, код exchange_service выполняется целиком."""
    _patch_exchange_api(monkeypatch, payload={"date": "2025-01-01", "usd": {"rub": 77.0}})

    result = await groups_service.calculate_wallet_effective_balance(debit_wallet)

    # 77.0 приходит из ответа API, а не из FALLBACK_RATES (там 95.0)
    assert result == Decimal("77000")


async def test_effective_balance_falls_back_when_api_unavailable(debit_wallet: Wallet, monkeypatch):
    """При ошибке API groups получает резервный курс, а не падает."""
    _patch_exchange_api(monkeypatch, payload=None, status=500)

    result = await groups_service.calculate_wallet_effective_balance(debit_wallet)

    # FALLBACK_RATES[(USD, RUB)] = 95.0
    assert result == Decimal("95000")


async def test_effective_balance_falls_back_on_non_numeric_rate(debit_wallet: Wallet, monkeypatch):
    """Нечисловой курс в ответе API трактуется как отсутствие курса -> резерв."""
    _patch_exchange_api(monkeypatch, payload={"date": "2025-01-01", "usd": {"rub": "88.5"}})

    result = await groups_service.calculate_wallet_effective_balance(debit_wallet)

    assert result == Decimal("95000")


async def test_group_balance_mixes_rub_and_api_currency(
    db_session: AsyncSession, test_user: User, group: Group, monkeypatch
):
    """RUB считается напрямую, USD — через курс из API (обе ветки за один тест)."""
    _patch_exchange_api(monkeypatch, payload={"date": "2025-01-01", "usd": {"rub": 80.0}})

    rub = Wallet(
        name="rub_real",
        balance=Decimal("500"),
        user_id=test_user.id,
        currency=CurrencyEnum.RUB,
        type=WalletType.DEBIT,
        credit_limit=None,
    )
    usd = Wallet(
        name="usd_real",
        balance=Decimal("100"),
        user_id=test_user.id,
        currency=CurrencyEnum.USD,
        type=WalletType.DEBIT,
        credit_limit=None,
    )
    db_session.add_all([rub, usd])
    await db_session.commit()

    await groups_service.attach_wallet_to_group(db_session, test_user, group.id, rub.id)
    await groups_service.attach_wallet_to_group(db_session, test_user, group.id, usd.id)

    total = await groups_service.calculate_group_balance(db_session, group.id)

    # 500 (RUB без конвертации) + 100 * 80.0 (курс из API)
    assert total == Decimal("8500")
