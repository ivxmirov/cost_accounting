# ---------- Этап 1: сборка зависимостей через uv ----------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Отключаем создание .pyc и включаем небуферизованный вывод
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Сначала копируем только файлы зависимостей — для лучшего кэширования слоёв
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости в виртуальное окружение .venv
# --frozen гарантирует, что версии будут строго из uv.lock
# --no-install-project ставит только зависимости, без самого проекта (код еще не скопирован)
RUN uv sync --frozen --no-install-project --no-dev

# Копируем исходный код проекта
COPY . .

# Доустанавливаем сам проект (если он оформлен как пакет в pyproject.toml)
RUN uv sync --frozen --no-dev --no-editable

# ---------- Этап 2: финальный лёгкий образ ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Копируем готовое виртуальное окружение и код из builder'а
COPY --from=builder /app /app

EXPOSE 8000

# Запуск приложения
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
