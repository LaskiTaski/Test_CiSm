from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.v1.router import api_router
from app.services.queue_service import QueueService

# Настройка логирования
setup_logging(log_level=settings.log_level, log_file="api.log")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запуск
    logger.info("Starting application...")
    queue_service = QueueService()
    await queue_service.connect()
    app.state.queue_service = queue_service
    logger.info("Application started successfully")

    yield

    # Завершение / Выключение
    logger.info("Shutting down application...")
    await queue_service.disconnect()
    logger.info("Application shut down successfully")


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="""
    ## Асинхронный сервис управления задачами

    ### Возможности:
    * **Создание задач** через REST API
    * **Асинхронная обработка** в фоновом режиме
    * **Приоритеты**: LOW, MEDIUM, HIGH
    * **Статусы**: NEW → PENDING → IN_PROGRESS → COMPLETED/FAILED/CANCELLED

    ### Архитектура:
    - FastAPI для REST API
    - PostgreSQL для хранения задач
    - RabbitMQ для очереди задач
    - 2 Worker'а с concurrency=3 (до 6 задач параллельно)
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "tasks",
            "description": "Операции с задачами",
        },
        {
            "name": "health",
            "description": "Health checks и метрики",
        }
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.project_name,
        "version": settings.version
    }


@app.get("/metrics", tags=["health"])
async def metrics():
    """Prometheus metrics endpoint"""
    if not settings.enable_metrics:
        return {"error": "Metrics disabled"}
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
