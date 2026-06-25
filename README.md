# Cost Accounting :1234::pen:
Система по учету личных доходов и расходов пользователя

## Технологии
Основной стек проекта, все зависимости управляются через Poetry

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688.svg)](https://fastapi.tiangolo.com)
[![Uvicorn](https://img.shields.io/badge/Uvicorn-0.42+-4B8BBE.svg)](https://www.uvicorn.org)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg)](https://www.sqlalchemy.org)
[![HTTPX](https://img.shields.io/badge/HTTPX-0.28+-5A29E4.svg)](https://www.python-httpx.org)
[![Aiohttp](https://img.shields.io/badge/Aiohttp-3.13+-2C5BB4.svg)](https://docs.aiohttp.org)
[![Poetry](https://img.shields.io/badge/Poetry-2.0+-1A1A1A.svg)](https://python-poetry.org)
[![Pytest](https://img.shields.io/badge/Pytest-9.0+-0A9EDC.svg)](https://docs.pytest.org)
[![Mypy](https://img.shields.io/badge/Mypy-1.19+-2F4858.svg)](https://mypy-lang.org)

## Быстрый старт

1. Клонируйте репозиторий

```bash
git clone https://github.com/ivxmirov/cost_accounting.git
```

2. Установите зависимости (включая dev и test-зависимости)

```bash
poetry install --with test,dev
```

3. Активируйте виртуальное окружение

```bash
poetry shell
```

4. Настройте переменные окружения

```bash
cp .env.example .env
```
Отредактируйте .env и .env.test под свои настройки

5. Примените миграции базы данных

```bash
alembic upgrade head
```

6. Запустите сервер для разработки

```bash
uvicorn app.main:app --reload
```

**Готово! API доступно по адресу:**
- Web UI: http://localhost:8000/static/index.html
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Структура

```text
cost_accounting
├─ .pre-commit-config.yaml
├─ alembic
│  ├─ env.py
│  ├─ README
│  ├─ script.py.mako
│  └─ versions
│     └─ af914c1abcba_initial.py
├─ alembic.ini
├─ app
│  ├─ api
│  │  ├─ v1
│  │  │  ├─ operations.py
│  │  │  ├─ users.py
│  │  │  ├─ wallets.py
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  ├─ database.py
│  ├─ dependency.py
│  ├─ enum.py
│  ├─ models.py
│  ├─ repository
│  │  ├─ operations.py
│  │  ├─ users.py
│  │  ├─ wallets.py
│  │  └─ __init__.py
│  ├─ schemas.py
│  ├─ service
│  │  ├─ exchange_service.py
│  │  ├─ operations.py
│  │  ├─ users.py
│  │  ├─ wallets.py
│  │  └─ __init__.py
│  ├─ static
│  │  ├─ css
│  │  │  ├─ bootstrap.min.css
│  │  │  └─ style.css
│  │  ├─ index.html
│  │  └─ js
│  │     ├─ app.js
│  │     └─ bootstrap.bundle.min.js
│  └─ __init__.py
├─ main.py
├─ poetry.lock
├─ pyproject.toml
├─ README.md
├─ test-reports
└─ tests
   ├─ conftest.py
   ├─ test_api
   │  └─ test_operations.py
   └─ __init__.py
```

## Некоторые примеры запросов к API

**Создать пользователя** - доступно всем пользователям

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/v1/users' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "login": "user_example"
}'
```

Response (201 Created):
```
{
  "login": "user_example",
  "id": 1
}
```

**Создать кошелек** - требуется авторизация

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/v1/wallets' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer your_login' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "wallet_example",
  "initial_balance": 500,
  "currency": "rub"
}'
```

Response (201 Created):
```
{
  "id": 1,
  "name": "wallet_example",
  "balance": "500.0000000000",
  "currency": "rub"
}
```

**Пополнить баланс кошелька** - требуется авторизация

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/v1/operations/income' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer your_login' \
  -H 'Content-Type: application/json' \
  -d '{
  "wallet_name": "wallet_example",
  "amount": 25000,
  "description": "gift"
}'
```

Response (201 Created):
```
{
  "id": 1,
  "wallet_id": 1,
  "type": "income",
  "amount": "25000.0000000000",
  "currency": "rub",
  "category": "gift",
  "subcategory": null,
  "created_at": "2026-06-25T13:34:27.526417"
}
```

**Перевести деньги между кошельками** - требуется авторизация
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/v1/operations/transfer' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer your_login' \
  -H 'Content-Type: application/json' \
  -d '{
  "from_wallet_id": 1,
  "to_wallet_id": 2,
  "amount": 30
}'
```

Response (201 Created):
```
{
  "id": 1,
  "wallet_id": 1,
  "type": "transfer",
  "amount": "0.4000000000",
  "currency": "usd",
  "category": "transfer",
  "subcategory": null,
  "created_at": "2026-06-25T13:42:47.696518"
}
```

## Автор
ivxmirov - [GitHub](https://github.com/ivxmirov)
