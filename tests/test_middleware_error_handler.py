from fastapi import HTTPException

from app.service import users as user_service


def test_http_exception_format(client, test_user):
    response = client.post(
        "/api/v1/users", json={"login": test_user.login, "password": "password123"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data == {
        "code": "400",
        "message": "Пользователь с таким логином уже существует",
        "details": None,
    }


def test_http_exception_with_dict_detail(client, monkeypatch):
    async def failing_create_user(*args, **kwargs):
        raise HTTPException(
            status_code=400, detail={"message": "Custom message", "reason": "duplicate"},
        )

    monkeypatch.setattr(user_service, "create_user", failing_create_user)

    response = client.post("/api/v1/users", json={"login": "dict", "password": "password123"})
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "400"
    assert data["message"] == "Custom message"
    assert data["details"] == {"reason": "duplicate"}


def test_validation_error_format(client):
    response = client.post("/api/v1/users", json={"login": "ab", "password": "password123"})
    assert response.status_code == 422
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "details" in data
    assert data["code"] == "422"
    assert data["message"] == "Validation error"
    assert isinstance(data["details"], list)


def test_generic_exception_format(client, monkeypatch):
    async def failing_create_user(*args, **kwargs):
        raise ValueError("Test internal error")

    monkeypatch.setattr(user_service, "create_user", failing_create_user)

    response = client.post("/api/v1/users", json={"login": "testuser", "password": "password123"})
    assert response.status_code == 500
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "details" in data
    assert data["code"] == "500"
    assert data["message"] == "Internal server error"


def test_error_response_structure(client):
    response = client.post("/api/v1/users", json={"login": "ab", "password": "password123"})
    assert response.status_code == 422
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "details" in data
    assert isinstance(data["code"], str)
    assert isinstance(data["message"], str) or data["message"] is None
    assert isinstance(data["details"], (dict, list)) or data["details"] is None
