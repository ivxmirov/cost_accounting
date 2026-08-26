def test_create_user_success(client):

    response = client.post("/api/v1/users", json={"login": "test", "password": "password123"})

    assert response.status_code == 201

    assert response.json()["login"] == "test"

    assert response.json()["id"] == 1


def test_create_user_exists(client, current_user):

    response = client.post(
        "/api/v1/users", json={"login": current_user.login, "password": "password123"},
    )

    assert response.status_code == 400


def test_get_me_success(client, auth_headers, current_user):

    response = client.get("/api/v1/users/me", headers=auth_headers)

    assert response.status_code == 200

    assert response.json()["login"] == current_user.login

    assert response.json()["id"] == current_user.id


def test_get_me_unauthorized(client):

    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
