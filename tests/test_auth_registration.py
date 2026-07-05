def test_registration_success(client):
    """Успешная регистрация пользователя с валидными данными."""
    response = client.post(
        "/api/v1/users",
        json={"login": "validuser", "password": "validpassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["login"] == "validuser"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_registration_duplicate_login(client, test_user):
    """Регистрация с уже существующим логином должна возвращать 400."""
    response = client.post(
        "/api/v1/users",
        json={"login": test_user.login, "password": "somepassword"},
    )
    assert response.status_code == 400
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert data["code"] == "400"
    assert "уже существует" in data["message"]


def test_registration_short_password(client):
    """Регистрация с слишком коротким паролем (< 6 символов) должна возвращать 422."""
    response = client.post(
        "/api/v1/users",
        json={"login": "testuser", "password": "12345"},
    )
    assert response.status_code == 422
    data = response.json()
    assert "code" in data
    assert data["code"] == "422"


def test_registration_missing_password(client):
    """Регистрация без пароля должна возвращать 422."""
    response = client.post(
        "/api/v1/users",
        json={"login": "testuser"},
    )
    assert response.status_code == 422
    data = response.json()
    assert "code" in data
    assert data["code"] == "422"


def test_registration_short_login(client):
    """Регистрация с слишком коротким логином (< 3 символов) должна возвращать 422."""
    response = client.post(
        "/api/v1/users",
        json={"login": "ab", "password": "password123"},
    )
    assert response.status_code == 422


def test_registration_invalid_login_characters(client):
    """Регистрация с недопустимыми символами в логине должна возвращать 422."""
    response = client.post(
        "/api/v1/users",
        json={"login": "user@#$", "password": "password123"},
    )
    assert response.status_code == 422


def test_registration_missing_login(client):
    """Регистрация без логина должна возвращать 422."""
    response = client.post(
        "/api/v1/users",
        json={"password": "password123"},
    )
    assert response.status_code == 422
    data = response.json()
    assert "code" in data
    assert data["code"] == "422"


def test_registration_empty_payload(client):
    """Регистрация с пустым payload должна возвращать 422."""
    response = client.post("/api/v1/users", json={})
    assert response.status_code == 422
    data = response.json()
    assert "code" in data
    assert data["code"] == "422"


def test_registration_password_not_returned(client):
    """Убедиться, что пароль не возвращается в ответе регистрации."""
    response = client.post(
        "/api/v1/users",
        json={"login": "secureuser", "password": "securepassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "password" not in data
    assert "password_hash" not in data
    assert data["login"] == "secureuser"


def test_registration_and_login_with_correct_password(client):
    """После регистрации должна быть возможность войти с тем же паролем."""
    registration_response = client.post(
        "/api/v1/users",
        json={"login": "testlogin", "password": "testpassword123"},
    )
    assert registration_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"login": "testlogin", "password": "testpassword123"},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens


def test_registration_and_login_with_wrong_password(client):
    """После регистрации попытка входа с неверным паролем должна быть отклонена."""
    registration_response = client.post(
        "/api/v1/users",
        json={"login": "anotheruser", "password": "correctpassword"},
    )
    assert registration_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"login": "anotheruser", "password": "wrongpassword"},
    )
    assert login_response.status_code == 401
    data = login_response.json()
    assert "message" in data
    assert "Неверный логин или пароль" in data["message"]
