FROM python:3.11 AS builder
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Установка uv
RUN pip install --no-cache-dir uv

# Файлы зависимостей
COPY pyproject.toml uv.lock* ./

# Зависимости
RUN uv sync --frozen --no-dev

FROM python:3.11 AS final

WORKDIR /app

# Виртуальное окружение из builder
COPY --from=builder /app/.venv /app/.venv

# Копируем код приложения
COPY . .

# Создание директории для логов
RUN mkdir -p /app/logs

# Создание пользователя без root прав
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]