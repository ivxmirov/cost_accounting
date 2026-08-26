import uuid

from app.models import Wallet


async def test_e2e_basic_user_flow_registration_to_expense(client, db, mock_currency_api):
    """E2E тест: Базовый пользовательский флоу от регистрации до траты.

    Ожидаемый флоу:
    1. Регистрация нового пользователя через POST /api/v1/users с логином "e2e_user_1"
       - Ожидаемый статус: 201
       - Сохранить login и id из ответа для дальнейших запросов
    2. Создание кошелька через POST /api/v1/wallets с именем "Main Wallet",
       валютой "USD", балансом 0.0
       - Использовать Authorization заголовок: Bearer {user_login}
       - Ожидаемый статус: 201
       - Проверить, что баланс кошелька равен 0.0
       - Сохранить wallet_id из ответа
    3. Пополнение кошелька через POST /api/v1/operations/income
       - Передать wallet_id, amount: 100.0, description: "Salary"
       - Использовать Authorization заголовок
       - Ожидаемый статус: 201
       - Проверить, что type == "income" и amount == 100.0
    4. Проверка баланса через GET /api/v1/wallets
       - Ожидаемый статус: 200
       - Найти кошелек по wallet_id в списке
       - Проверить, что wallet.balance == 100.0
    5. Создание расхода через POST /api/v1/operations/expense
       - Передать wallet_id, amount: 50.0, category: "Food", description: "Lunch"
       - Ожидаемый статус: 201
       - Проверить, что type == "expense" и amount == 50.0
    6. Проверка финального баланса через GET /api/v1/wallets
       - Ожидаемый статус: 200
       - Найти кошелек по wallet_id в списке
       - Проверить, что wallet.balance == 50.0
    7. Проверка баланса в базе данных через db.get(Wallet, wallet_id)
       - Проверить, что wallet.balance == 50.0

    Полезные ссылки:
    - pytest async support: https://docs.pytest.org/en/stable/how-to/asyncio.html
    - FastAPI TestClient: https://fastapi.tiangolo.com/tutorial/testing/
    """

    response = client.post("/api/v1/users", json={"login": "e2e_user_1", "password": "password123"})
    assert response.status_code == 201
    user_data = response.json()
    user_data["id"]
    user_data["login"]

    login_response = client.post(
        "/api/v1/auth/login", json={"login": "e2e_user_1", "password": "password123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    wallet_name = "Main Wallet"
    wallet_response = client.post(
        "/api/v1/wallets",
        json={"name": wallet_name, "initial_balance": 0.0, "currency": "usd"},
        headers=headers,
    )
    assert wallet_response.status_code == 201
    wallet_data = wallet_response.json()
    wallet_id = wallet_data["id"]
    assert float(wallet_data["balance"]) == 0.0

    income_response = client.put(
        "/api/v1/operations/income",
        json={
            "transaction_id": str(uuid.uuid4()),
            "wallet_name": wallet_name,
            "amount": 100.0,
            "description": "Salary",
        },
        headers=headers,
    )
    assert income_response.status_code == 201
    income_data = income_response.json()
    assert income_data["type"] == "income"
    assert float(income_data["amount"]) == 100.0

    wallets_response = client.get("/api/v1/wallets", headers=headers)
    assert wallets_response.status_code == 200
    wallets_data = wallets_response.json()
    wallet_after_income = next(w for w in wallets_data if w["id"] == wallet_id)
    assert float(wallet_after_income["balance"]) == 100.0

    expense_response = client.put(
        "/api/v1/operations/expense",
        json={
            "transaction_id": str(uuid.uuid4()),
            "wallet_name": wallet_name,
            "amount": 50.0,
            "description": "Lunch",
        },
        headers=headers,
    )
    assert expense_response.status_code == 201
    expense_data = expense_response.json()
    assert expense_data["type"] == "expense"
    assert float(expense_data["amount"]) == 50.0

    wallets_final_response = client.get("/api/v1/wallets", headers=headers)
    assert wallets_final_response.status_code == 200
    wallets_final_data = wallets_final_response.json()
    wallet_final = next(w for w in wallets_final_data if w["id"] == wallet_id)
    assert float(wallet_final["balance"]) == 50.0

    wallet_in_db = await db.get(Wallet, wallet_id)
    assert wallet_in_db is not None
    assert float(wallet_in_db.balance) == 50.0


async def test_e2e_multi_wallet_flow_with_transfer(client, db, mock_currency_api):
    """E2E тест: Флоу с несколькими кошельками и переводом между ними.

    Ожидаемый флоу:
    1. Регистрация нового пользователя через POST /api/v1/users с логином "e2e_user_2"
       - Ожидаемый статус: 201
       - Сохранить login из ответа
    2. Создание первого кошелька через POST /api/v1/wallets
       - Имя: "USD Wallet", валюта: "USD", баланс: 500.0
       - Использовать Authorization заголовок
       - Ожидаемый статус: 201
       - Сохранить wallet1_id
    3. Создание второго кошелька через POST /api/v1/wallets
       - Имя: "EUR Wallet", валюта: "EUR", баланс: 0.0
       - Ожидаемый статус: 201
       - Сохранить wallet2_id
    4. Получение списка кошельков через GET /api/v1/wallets
       - Ожидаемый статус: 200
       - Проверить, что количество кошельков == 2
    5. Пополнение первого кошелька через POST /api/v1/operations/income
       - wallet_id: wallet1_id, amount: 200.0, description: "Bonus"
       - Ожидаемый статус: 201
    6. Перевод средств через POST /api/v1/operations/transfer
       - from_wallet_id: wallet1_id, to_wallet_id: wallet2_id, amount: 100.0
       - Ожидаемый статус: 200
       - Проверить, что success == True
    7. Проверка общего баланса через GET /api/v1/balance
       - Ожидаемый статус: 200
       - Проверить наличие поля total_balance
    8. Получение финального списка кошельков через GET /api/v1/wallets
       - Ожидаемый статус: 200
       - Найти кошельки по id и проверить балансы
       - wallet1_final.balance == 600.0 (500 + 200 - 100)
       - wallet2_final.balance > 0.0 (конвертированная сумма)

    Полезные ссылки:
    - pytest fixtures: https://docs.pytest.org/en/stable/fixture.html
    - async test patterns: https://docs.pytest.org/en/stable/how-to/asyncio.html#async-fixtures
    """

    response = client.post("/api/v1/users", json={"login": "e2e_user_2", "password": "password123"})
    assert response.status_code == 201
    user_data = response.json()
    user_data["login"]

    login_response = client.post(
        "/api/v1/auth/login", json={"login": "e2e_user_2", "password": "password123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    wallet1_name = "USD Wallet"
    wallet1_response = client.post(
        "/api/v1/wallets",
        json={"name": wallet1_name, "initial_balance": 500.0, "currency": "usd"},
        headers=headers,
    )
    assert wallet1_response.status_code == 201
    wallet1_data = wallet1_response.json()
    wallet1_id = wallet1_data["id"]

    wallet2_name = "EUR Wallet"
    wallet2_response = client.post(
        "/api/v1/wallets",
        json={"name": wallet2_name, "initial_balance": 0.0, "currency": "eur"},
        headers=headers,
    )
    assert wallet2_response.status_code == 201
    wallet2_data = wallet2_response.json()
    wallet2_id = wallet2_data["id"]

    wallets_response = client.get("/api/v1/wallets", headers=headers)
    assert wallets_response.status_code == 200
    wallets_data = wallets_response.json()
    assert len(wallets_data) == 2

    income_response = client.put(
        "/api/v1/operations/income",
        json={
            "transaction_id": str(uuid.uuid4()),
            "wallet_name": wallet1_name,
            "amount": 200.0,
            "description": "Bonus",
        },
        headers=headers,
    )
    assert income_response.status_code == 201

    transfer_response = client.put(
        "/api/v1/operations/transfer",
        json={
            "transaction_id": str(uuid.uuid4()),
            "from_wallet_id": wallet1_id,
            "to_wallet_id": wallet2_id,
            "amount": 100.0,
        },
        headers=headers,
    )
    assert transfer_response.status_code == 201
    transfer_data = transfer_response.json()
    assert transfer_data["type"] == "transfer"

    balance_response = client.get("/api/v1/balance", headers=headers)
    assert balance_response.status_code == 200
    balance_data = balance_response.json()
    assert "total_balance" in balance_data

    wallets_final_response = client.get("/api/v1/wallets", headers=headers)
    assert wallets_final_response.status_code == 200
    wallets_final_data = wallets_final_response.json()
    wallet1_final = next(w for w in wallets_final_data if w["id"] == wallet1_id)
    wallet2_final = next(w for w in wallets_final_data if w["id"] == wallet2_id)
    assert float(wallet1_final["balance"]) == 600.0
    assert float(wallet2_final["balance"]) > 0.0


async def test_e2e_operations_history_and_report(client, db, mock_currency_api):
    """E2E тест: Флоу с историей операций.

    Ожидаемый флоу:
    1. Регистрация нового пользователя через POST /api/v1/users с логином "e2e_user_3"
       - Ожидаемый статус: 201
       - Сохранить login
    2. Создание кошелька через POST /api/v1/wallets
       - Имя: "RUB Wallet", валюта: "RUB", баланс: 0.0
       - Ожидаемый статус: 201
       - Сохранить wallet_id
    3. Первое пополнение через POST /api/v1/operations/income
       - wallet_id, amount: 1000.0, description: "Salary"
       - Ожидаемый статус: 201
    4. Второе пополнение через POST /api/v1/operations/income
       - wallet_id, amount: 500.0, description: "Bonus"
       - Ожидаемый статус: 201
    5. Первый расход через POST /api/v1/operations/expense
       - wallet_id, amount: 300.0, category: "Food", description: "Groceries"
       - Ожидаемый статус: 201
    6. Второй расход через POST /api/v1/operations/expense
       - wallet_id, amount: 200.0, category: "Transport", description: "Taxi"
       - Ожидаемый статус: 201
    7. Получение всех операций через GET /api/v1/operations
       - Ожидаемый статус: 200
       - Проверить, что количество операций == 4
    8. Получение операций по кошельку через GET /api/v1/operations?wallet_id={wallet_id}
       - Ожидаемый статус: 200
       - Проверить, что количество операций == 4
       - Проверить, что все операции принадлежат указанному кошельку
    9. Проверка баланса через GET /api/v1/wallets
       - Ожидаемый статус: 200
       - Найти кошелек по wallet_id в списке
       - Проверить, что wallet.balance == 1000.0
    10. Проверка баланса в базе данных через db.get(Wallet, wallet_id)
        - Проверить, что wallet.balance == 1000.0

    Полезные ссылки:
    - pytest assertions: https://docs.pytest.org/en/stable/how-to/assert.html
    - test organization: https://docs.pytest.org/en/stable/explanation/goodpractices.html
    """

    response = client.post("/api/v1/users", json={"login": "e2e_user_3", "password": "password123"})
    assert response.status_code == 201
    user_data = response.json()
    user_data["login"]

    login_response = client.post(
        "/api/v1/auth/login", json={"login": "e2e_user_3", "password": "password123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    wallet_name = "RUB Wallet"
    wallet_response = client.post(
        "/api/v1/wallets",
        json={"name": wallet_name, "initial_balance": 0.0, "currency": "rub"},
        headers=headers,
    )
    assert wallet_response.status_code == 201
    wallet_data = wallet_response.json()
    wallet_id = wallet_data["id"]

    income1_response = client.put(
        "/api/v1/operations/income",
        json={
            "transaction_id": str(uuid.uuid4()),
            "wallet_name": wallet_name,
            "amount": 1000.0,
            "description": "Salary",
        },
        headers=headers,
    )
    assert income1_response.status_code == 201

    income2_response = client.put(
        "/api/v1/operations/income",
        json={
            "transaction_id": str(uuid.uuid4()),
            "wallet_name": wallet_name,
            "amount": 500.0,
            "description": "Bonus",
        },
        headers=headers,
    )
    assert income2_response.status_code == 201

    expense1_response = client.put(
        "/api/v1/operations/expense",
        json={
            "transaction_id": str(uuid.uuid4()),
            "wallet_name": wallet_name,
            "amount": 300.0,
            "description": "Groceries",
        },
        headers=headers,
    )
    assert expense1_response.status_code == 201

    expense2_response = client.put(
        "/api/v1/operations/expense",
        json={
            "transaction_id": str(uuid.uuid4()),
            "wallet_name": wallet_name,
            "amount": 200.0,
            "description": "Taxi",
        },
        headers=headers,
    )
    assert expense2_response.status_code == 201

    operations_response = client.get("/api/v1/operations", headers=headers)
    assert operations_response.status_code == 200
    operations_data = operations_response.json()
    assert len(operations_data) == 4

    operations_by_wallet_response = client.get(
        f"/api/v1/operations?wallet_id={wallet_id}", headers=headers,
    )
    assert operations_by_wallet_response.status_code == 200
    operations_by_wallet_data = operations_by_wallet_response.json()
    assert len(operations_by_wallet_data) == 4
    for operation in operations_by_wallet_data:
        assert operation["wallet_id"] == wallet_id

    wallets_response = client.get("/api/v1/wallets", headers=headers)
    assert wallets_response.status_code == 200
    wallets_data = wallets_response.json()
    wallet_final = next(w for w in wallets_data if w["id"] == wallet_id)
    assert float(wallet_final["balance"]) == 1000.0

    wallet_in_db = await db.get(Wallet, wallet_id)
    assert wallet_in_db is not None
    assert float(wallet_in_db.balance) == 1000.0


async def test_e2e_insufficient_funds_after_income(client, db, mock_currency_api):
    """E2E тест: Ошибка недостатка средств после пополнения.

    Ожидаемый флоу:
    1. Регистрация нового пользователя через POST /api/v1/users с логином "e2e_user_4"
       - Ожидаемый статус: 201
       - Сохранить login
    2. Создание кошелька через POST /api/v1/wallets
       - Имя: "USD Wallet", валюта: "USD", баланс: 0.0
       - Ожидаемый статус: 201
       - Сохранить wallet_id
    3. Пополнение кошелька через POST /api/v1/operations/income
       - wallet_id, amount: 100.0, description: "Salary"
       - Ожидаемый статус: 201
    4. Проверка баланса через GET /api/v1/wallets
       - Ожидаемый статус: 200
       - Найти кошелек по wallet_id в списке
       - Проверить, что wallet.balance == 100.0
    5. Попытка создать расход через POST /api/v1/operations/expense
       - wallet_id, amount: 240.0, category: "Shopping", description: "Expensive item"
       - Ожидаемый статус: 400 (недостаточно средств)
       - Проверить, что в ответе есть сообщение "Недостаточно средств"
    6. Проверка баланса после неудачной операции через GET /api/v1/wallets
       - Ожидаемый статус: 200
       - Найти кошелек по wallet_id в списке
       - Проверить, что wallet.balance всё ещё == 100.0 (баланс не изменился)
    7. Проверка баланса в базе данных через db.get(Wallet, wallet_id)
       - Проверить, что wallet.balance == 100.0

    Полезные ссылки:
    - pytest.raises для проверки исключений: https://docs.pytest.org/en/stable/reference/reference.html#pytest.raises
    - error handling tests: https://docs.pytest.org/en/stable/how-to/assert.html#assertions-about-expected-exceptions
    """

    response = client.post("/api/v1/users", json={"login": "e2e_user_4", "password": "password123"})
    assert response.status_code == 201
    user_data = response.json()
    user_data["login"]

    login_response = client.post(
        "/api/v1/auth/login", json={"login": "e2e_user_4", "password": "password123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    wallet_name = "USD Wallet"
    wallet_response = client.post(
        "/api/v1/wallets",
        json={"name": wallet_name, "initial_balance": 0.0, "currency": "usd"},
        headers=headers,
    )
    assert wallet_response.status_code == 201
    wallet_data = wallet_response.json()
    wallet_id = wallet_data["id"]

    income_response = client.put(
        "/api/v1/operations/income",
        json={
            "transaction_id": str(uuid.uuid4()),
            "wallet_name": wallet_name,
            "amount": 100.0,
            "description": "Salary",
        },
        headers=headers,
    )
    assert income_response.status_code == 201

    wallets_response = client.get("/api/v1/wallets", headers=headers)
    assert wallets_response.status_code == 200
    wallets_data = wallets_response.json()
    wallet_after_income = next(w for w in wallets_data if w["id"] == wallet_id)
    assert float(wallet_after_income["balance"]) == 100.0

    expense_response = client.put(
        "/api/v1/operations/expense",
        json={
            "transaction_id": str(uuid.uuid4()),
            "wallet_name": wallet_name,
            "amount": 240.0,
            "description": "Expensive item",
        },
        headers=headers,
    )
    assert expense_response.status_code == 400
    error_data = expense_response.json()
    assert "Insufficient funds" in error_data["message"]

    wallets_final_response = client.get("/api/v1/wallets", headers=headers)
    assert wallets_final_response.status_code == 200
    wallets_final_data = wallets_final_response.json()
    wallet_final = next(w for w in wallets_final_data if w["id"] == wallet_id)
    assert float(wallet_final["balance"]) == 100.0

    wallet_in_db = await db.get(Wallet, wallet_id)
    assert wallet_in_db is not None
    assert float(wallet_in_db.balance) == 100.0


async def test_e2e_expense_without_income(client, db, mock_currency_api):
    """E2E тест: Ошибка траты без предварительного пополнения.

    Ожидаемый флоу:
    1. Регистрация нового пользователя через POST /api/v1/users с логином "e2e_user_5"
       - Ожидаемый статус: 201
       - Сохранить login
    2. Создание кошелька через POST /api/v1/wallets
       - Имя: "USD Wallet", валюта: "USD", баланс: 0.0
       - Ожидаемый статус: 201
       - Сохранить wallet_id
    3. Проверка начального баланса через GET /api/v1/wallets
       - Ожидаемый статус: 200
       - Найти кошелек по wallet_id в списке
       - Проверить, что wallet.balance == 0.0
    4. Попытка создать расход через POST /api/v1/operations/expense
       - wallet_id, amount: 50.0, category: "Food", description: "Lunch"
       - Ожидаемый статус: 400 (недостаточно средств)
       - Проверить, что в ответе есть сообщение "Недостаточно средств"
    5. Проверка баланса после неудачной операции через GET /api/v1/wallets
       - Ожидаемый статус: 200
       - Найти кошелек по wallet_id в списке
       - Проверить, что wallet.balance == 0.0
    6. Проверка баланса в базе данных через db.get(Wallet, wallet_id)
       - Проверить, что wallet.balance == 0.0
    7. Получение списка операций через GET /api/v1/operations
       - Ожидаемый статус: 200
       - Проверить, что количество операций == 0 (операция не была создана)

    Полезные ссылки:
    - test isolation: https://docs.pytest.org/en/stable/explanation/fixtures.html#fixture-scopes
    - database testing: https://docs.pytest.org/en/stable/how-to/fixtures.html#fixtures-can-request-other-fixtures
    """

    response = client.post("/api/v1/users", json={"login": "e2e_user_5", "password": "password123"})
    assert response.status_code == 201
    user_data = response.json()
    user_data["login"]

    login_response = client.post(
        "/api/v1/auth/login", json={"login": "e2e_user_5", "password": "password123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    wallet_name = "USD Wallet"
    wallet_response = client.post(
        "/api/v1/wallets",
        json={"name": wallet_name, "initial_balance": 0.0, "currency": "usd"},
        headers=headers,
    )
    assert wallet_response.status_code == 201
    wallet_data = wallet_response.json()
    wallet_id = wallet_data["id"]

    wallets_response = client.get("/api/v1/wallets", headers=headers)
    assert wallets_response.status_code == 200
    wallets_data = wallets_response.json()
    wallet_initial = next(w for w in wallets_data if w["id"] == wallet_id)
    assert float(wallet_initial["balance"]) == 0.0

    expense_response = client.put(
        "/api/v1/operations/expense",
        json={
            "transaction_id": str(uuid.uuid4()),
            "wallet_name": wallet_name,
            "amount": 50.0,
            "description": "Lunch",
        },
        headers=headers,
    )
    assert expense_response.status_code == 400
    error_data = expense_response.json()
    assert "Insufficient funds" in error_data["message"]

    wallets_final_response = client.get("/api/v1/wallets", headers=headers)
    assert wallets_final_response.status_code == 200
    wallets_final_data = wallets_final_response.json()
    wallet_final = next(w for w in wallets_final_data if w["id"] == wallet_id)
    assert float(wallet_final["balance"]) == 0.0

    wallet_in_db = await db.get(Wallet, wallet_id)
    assert wallet_in_db is not None
    assert float(wallet_in_db.balance) == 0.0

    operations_response = client.get("/api/v1/operations", headers=headers)
    assert operations_response.status_code == 200
    operations_data = operations_response.json()
    assert len(operations_data) == 0


async def test_e2e_transfer_insufficient_funds(client, db, mock_currency_api):
    """E2E тест: Ошибка перевода при недостатке средств.

    Ожидаемый флоу:
    1. Регистрация нового пользователя через POST /api/v1/users с логином "e2e_user_6"
       - Ожидаемый статус: 201
       - Сохранить login
    2. Создание первого кошелька через POST /api/v1/wallets
       - Имя: "USD Wallet", валюта: "USD", баланс: 100.0
       - Ожидаемый статус: 201
       - Сохранить wallet1_id
    3. Создание второго кошелька через POST /api/v1/wallets
       - Имя: "EUR Wallet", валюта: "EUR", баланс: 0.0
       - Ожидаемый статус: 201
       - Сохранить wallet2_id
    4. Пополнение первого кошелька через POST /api/v1/operations/income
       - wallet_id: wallet1_id, amount: 50.0, description: "Bonus"
       - Ожидаемый статус: 201
       - Итоговый баланс wallet1 должен быть 150.0 (100 + 50)
    5. Попытка перевода через POST /api/v1/operations/transfer
       - from_wallet_id: wallet1_id, to_wallet_id: wallet2_id, amount: 200.0
       - Ожидаемый статус: 400 (недостаточно средств)
       - Проверить, что в ответе есть сообщение "Недостаточно средств"
    6. Получение списка кошельков через GET /api/v1/wallets
       - Ожидаемый статус: 200
       - Найти кошельки по id
       - Проверить, что wallet1_final.balance == 150.0 (не изменился)
       - Проверить, что wallet2_final.balance == 0.0 (не изменился)

    Полезные ссылки:
    - pytest parametrization: https://docs.pytest.org/en/stable/how-to/parametrize.html
    - test data management: https://docs.pytest.org/en/stable/how-to/fixtures.html
    """

    response = client.post("/api/v1/users", json={"login": "e2e_user_6", "password": "password123"})
    assert response.status_code == 201
    user_data = response.json()
    user_data["login"]

    login_response = client.post(
        "/api/v1/auth/login", json={"login": "e2e_user_6", "password": "password123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    wallet1_name = "USD Wallet"
    wallet1_response = client.post(
        "/api/v1/wallets",
        json={"name": wallet1_name, "initial_balance": 100.0, "currency": "usd"},
        headers=headers,
    )
    assert wallet1_response.status_code == 201
    wallet1_data = wallet1_response.json()
    wallet1_id = wallet1_data["id"]

    wallet2_name = "EUR Wallet"
    wallet2_response = client.post(
        "/api/v1/wallets",
        json={"name": wallet2_name, "initial_balance": 0.0, "currency": "eur"},
        headers=headers,
    )
    assert wallet2_response.status_code == 201
    wallet2_data = wallet2_response.json()
    wallet2_id = wallet2_data["id"]

    income_response = client.put(
        "/api/v1/operations/income",
        json={
            "transaction_id": str(uuid.uuid4()),
            "wallet_name": wallet1_name,
            "amount": 50.0,
            "description": "Bonus",
        },
        headers=headers,
    )
    assert income_response.status_code == 201

    transfer_response = client.put(
        "/api/v1/operations/transfer",
        json={
            "transaction_id": str(uuid.uuid4()),
            "from_wallet_id": wallet1_id,
            "to_wallet_id": wallet2_id,
            "amount": 200.0,
        },
        headers=headers,
    )
    assert transfer_response.status_code == 400
    error_data = transfer_response.json()
    assert "Not enough money" in error_data["message"]

    wallets_response = client.get("/api/v1/wallets", headers=headers)
    assert wallets_response.status_code == 200
    wallets_data = wallets_response.json()
    wallet1_final = next(w for w in wallets_data if w["id"] == wallet1_id)
    wallet2_final = next(w for w in wallets_data if w["id"] == wallet2_id)
    assert float(wallet1_final["balance"]) == 150.0
    assert float(wallet2_final["balance"]) == 0.0
