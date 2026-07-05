from sqlalchemy.orm import Session


from app.repository import users as users_repository


def test_create_user_success(db_session: Session):

    from app.utils.password import hash_password

    password_hash = hash_password("testpassword")
    user = users_repository.create_user(db_session, "test", password_hash)

    assert user.login == "test"

    assert user.id == 1

    assert user.password_hash == password_hash


def test_get_user_success(db_session: Session, current_user):

    expected_user = users_repository.get_user(db_session, current_user.login)

    assert expected_user is not None

    assert current_user.login == expected_user.login

    assert current_user.id == expected_user.id
