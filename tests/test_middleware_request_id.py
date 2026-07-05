import uuid


def test_request_id_generated(client):
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer testuser"})
    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    assert request_id is not None
    assert len(request_id) > 0
    try:
        uuid.UUID(request_id)
    except ValueError:
        assert False, f"Request ID '{request_id}' is not a valid UUID"


def test_request_id_from_header(client):
    custom_request_id = str(uuid.uuid4())
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer testuser", "X-Request-ID": custom_request_id},
    )
    assert response.headers["X-Request-ID"] == custom_request_id


def test_request_id_in_response_header(client):
    response = client.post("/api/v1/users", json={"login": "newuser", "password": "password123"})
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] is not None
    assert len(response.headers["X-Request-ID"]) > 0


def test_request_id_persists_through_request(client, test_user):
    custom_request_id = "test-request-id-12345"
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {test_user.login}", "X-Request-ID": custom_request_id},
    )
    assert response.headers["X-Request-ID"] == custom_request_id
