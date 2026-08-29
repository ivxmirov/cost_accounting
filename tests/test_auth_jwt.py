def test_login_success(client, test_user):
    """Успешная авторизация с верными учётными данными."""
    response = client.post(
        "/api/v1/auth/login",
        json={"login": test_user.login, "password": "testpassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0
    assert len(data["refresh_token"]) > 0


def test_login_invalid_password(client, test_user):
    """Авторизация с неверным паролем должна возвращать 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"login": test_user.login, "password": "wrongpassword"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "Неверный логин или пароль" in data["message"]


def test_login_non_existent_user(client):
    """Авторизация с несуществующим пользователем должна возвращать 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "nonexistentuser", "password": "somepassword"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "Неверный логин или пароль" in data["message"]


def test_access_protected_endpoint_with_valid_token(client, test_user):
    """Доступ к защищенному эндпоинту с валидным JWT токеном."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"login": test_user.login, "password": "testpassword"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["login"] == test_user.login
    assert data["id"] == test_user.id


def test_access_protected_endpoint_without_token(client):
    """Доступ к защищенному эндпоинту без токена должен вернуть 401."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_access_protected_endpoint_with_invalid_token(client):
    """Доступ к защищенному эндпоинту с невалидным токеном должен вернуть 401."""
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid_token_here"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data


def test_refresh_token_with_valid_refresh_token(client, test_user):
    """Обновление access токена с валидным refresh токеном."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"login": test_user.login, "password": "testpassword"},
    )
    assert login_response.status_code == 200
    refresh_token = login_response.json()["refresh_token"]
    login_response.json()["access_token"]

    refresh_response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0
    assert data["refresh_token"] == refresh_token


def test_refresh_token_with_invalid_refresh_token(client):
    """Обновление токена с невалидным refresh токеном должно вернуть 401."""
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid_refresh_token"})
    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data


def test_refresh_token_with_access_token_should_fail(client, test_user):
    """Попытка обновить токен используя access token вместо refresh должна завершиться ошибкой."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"login": test_user.login, "password": "testpassword"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    refresh_response = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert refresh_response.status_code == 200


def test_registration_and_immediate_login_flow(client):
    """Полный flow: регистрация пользователя и немедленная авторизация."""
    register_response = client.post(
        "/api/v1/users",
        json={"login": "newuser", "password": "newpassword123"},
    )
    assert register_response.status_code == 201
    user_data = register_response.json()
    assert user_data["login"] == "newuser"

    login_response = client.post(
        "/api/v1/auth/login",
        json={"login": "newuser", "password": "newpassword123"},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    me_response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["login"] == "newuser"


def test_multiple_endpoints_with_same_token(client, test_user, test_wallet):
    """Использование одного токена для доступа к разным защищенным эндпоинтам."""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"login": test_user.login, "password": "testpassword"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    me_response = client.get("/api/v1/users/me", headers=headers)
    assert me_response.status_code == 200

    wallets_response = client.get("/api/v1/wallets", headers=headers)
    assert wallets_response.status_code == 200

    operations_response = client.get("/api/v1/operations", headers=headers)
    assert operations_response.status_code == 200
