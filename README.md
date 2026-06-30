# Cost Accounting :1234::pen:
Система по учету личных доходов и расходов пользователя

## Технологии
Основной стек проекта, все зависимости управляются через uv

**Основные:**  
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688.svg)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg)](https://www.sqlalchemy.org)
[![asyncpg](https://img.shields.io/badge/asyncpg-0.31+-2F6790.svg)](https://github.com/MagicStack/asyncpg)

**Инфраструктура:**  
[![uv](https://img.shields.io/badge/uv-0.7+-DE5FE2.svg)](https://docs.astral.sh/uv)
[![Uvicorn](https://img.shields.io/badge/Uvicorn-0.42+-4B8BBE.svg)](https://www.uvicorn.org)
[![HTTPX](https://img.shields.io/badge/HTTPX-0.28+-5A29E4.svg)](https://www.python-httpx.org)
[![Aiohttp](https://img.shields.io/badge/Aiohttp-3.13+-2C5BB4.svg)](https://docs.aiohttp.org)
[![Alembic](https://img.shields.io/badge/Alembic-1.18+-6E4B8B.svg)](https://alembic.sqlalchemy.org)

**Качество кода:**  
[![Ruff](https://img.shields.io/badge/Ruff-0.15+-D7FF64.svg)](https://docs.astral.sh/ruff)
[![Mypy](https://img.shields.io/badge/Mypy-1.20+-2F4858.svg)](https://mypy-lang.org)
[![Pytest](https://img.shields.io/badge/Pytest-8.4+-0A9EDC.svg)](https://docs.pytest.org)
[![Pre-commit](https://img.shields.io/badge/pre--commit-4.6+-FAB040.svg)](https://pre-commit.com)

## Быстрый старт

1. Клонируйте репозиторий

```bash
git clone https://github.com/ivxmirov/cost_accounting.git
```

2. Установите зависимости (включая dev и test-зависимости)

```bash
uv sync --group dev --group test
```

3. Настройте переменные окружения
  
   Скопируйте .env и .env.test и отредактируйте их под свои настройки

```bash
cp .env.example .env
cp .env.test.example .env.test
```

4. Примените миграции базы данных

```bash
uv run alembic upgrade head
```

5. Запустите сервер для разработки

```bash
uv run uvicorn app.main:app --reload
```

6. Запустите тесты

```bash
uv run pytest
```

7. Установите pre-commit хуки (опционально)

```bash
uv run pre-commit install
```

**Готово! API доступно по адресу:**
- Web UI: http://localhost:8000/static/index.html
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Примеры запросов к API

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
  "amount": "0.3000000000",
  "currency": "rub",
  "category": "transfer",
  "subcategory": null,
  "created_at": "2026-06-25T13:42:47.696518"
}
```

## Структура

```text
cost_accounting
├─ .pre-commit-config.yaml
├─ .python-version
├─ alembic
│  ├─ env.py
│  ├─ README
│  ├─ script.py.mako
│  └─ versions
│     ├─ 4e767668dbe0_add_tables.py
│     └─ 7598617a985e_clean_start.py
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
├─ pyproject.toml
├─ README.md
├─ tests
│  ├─ conftest.py
│  ├─ test_api
│  │  └─ test_operations.py
│  └─ __init__.py
└─ uv.lock
```

## Автор
ivxmirov - [GitHub](https://github.com/ivxmirov)
