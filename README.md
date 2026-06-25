# Cost Accounting :1234:
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
```
cost_accounting
├─ .pre-commit-config.yaml
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

## Разработка

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
  "id": 0
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
  "id": 0,
  "name": "wallet_example",
  "balance": "500.0000000000",
  "currency": "rub"
}
```

#### Добавить рецепт в список покупок
Доступно только авторизованным пользователям

__POST__ http://localhost/api/recipes/{id}/shopping_cart/

Response:
```
{
  "id": 0,
  "name": "string",
  "image": "http://python_django_practice.example.org/media/recipes/images/image.png",
  "cooking_time": 1
}
```

#### Добавить рецепт в избранное
Доступно только авторизованному пользователю

__POST__ http://localhost/api/recipes/{id}/favorite/

Response:
```
{
  "id": 0,
  "name": "string",
  "image": "http://python_django_practice.example.org/media/recipes/images/image.png",
  "cooking_time": 1
}
```

#### Подписаться на пользователя
Доступно только авторизованным пользователям

__POST__ http://localhost/api/users/{id}/subscribe/

Response:
```
{
  "email": "user@example.com",
  "id": 0,
  "username": "string",
  "first_name": "Вася",
  "last_name": "Иванов",
  "is_subscribed": true,
  "recipes": [
    {
      "id": 0,
      "name": "string",
      "image": "http://python_django_practice.example.org/media/recipes/images/image.png",
      "cooking_time": 1
    }
  ],
  "recipes_count": 0,
  "avatar": "http://python_django_practice.example.org/media/users/image.png"
}
```

## Автор
Илья Хмыров - [GitHub](https://github.com/ivxmirov)
