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
### Установка и запуск

1. Клонируйте репозиторий
```
git clone https://github.com/ivxmirov/cost_accounting.git
```

2. Установите зависимости (включая dev и test-зависимости)
```
poetry install --with test,dev
```

3. Активируйте виртуальное окружение
```
poetry shell
```

4. Настройте переменные окружения
cp .env.example .env
Отредактируйте .env под свои настройки

5. Примените миграции базы данных
alembic upgrade head

6. Запустите сервер для разработки
uvicorn app.main:app --reload

Готово! API доступно по адресу:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Конфигурация

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
## API-документация. Примеры запросов
