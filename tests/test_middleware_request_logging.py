import logging


def test_request_logged(client, caplog):
    with caplog.at_level(logging.INFO):
        response = client.get("/api/v1/operations?wallet_id=1")
        assert response.status_code in [200, 403, 401]

    log_records = [record for record in caplog.records if "GET" in record.message]
    assert len(log_records) > 0
    log_message = log_records[0].message
    assert "GET" in log_message
    assert "/api/v1/operations" in log_message
    assert "query=" in log_message
    assert "request_id=" in log_message
    assert "time=" in log_message


def test_post_request_logged(client, caplog):
    with caplog.at_level(logging.INFO):
        response = client.post("/api/v1/users", json={"login": "testuser123", "password": "password123"})
        assert response.status_code in [201, 400, 422]

    log_records = [record for record in caplog.records if "POST" in record.message]
    assert len(log_records) > 0
    log_message = log_records[0].message
    assert "POST" in log_message
    assert "/api/v1/users" in log_message
    assert "request_id=" in log_message
    assert "time=" in log_message


def test_request_id_in_log(client, caplog):
    import uuid

    custom_request_id = str(uuid.uuid4())
    with caplog.at_level(logging.INFO):
        client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer testuser", "X-Request-ID": custom_request_id},
        )

    log_records = [record for record in caplog.records if "GET" in record.message]
    assert len(log_records) > 0
    log_message = log_records[0].message
    assert f"request_id={custom_request_id}" in log_message


def test_logging_timing(client, caplog):
    with caplog.at_level(logging.INFO):
        client.get("/api/v1/users/me", headers={"Authorization": "Bearer testuser"})

    log_records = [record for record in caplog.records if "GET" in record.message]
    assert len(log_records) > 0
    log_message = log_records[0].message
    assert "time=" in log_message
    time_part = log_message.split("time=")[1]
    assert "ms" in time_part

