FROM python:3.10-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
COPY uv.lock* ./

RUN uv sync --no-dev

COPY . .

ENV PYTHONPATH=/app

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]