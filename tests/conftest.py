import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.deps import get_db
from app.db.base import Base
from app.services.queue_service import QueueService

# Тестовая БД
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_taskdb"


@pytest_asyncio.fixture
async def async_engine():
    """Тестовый движок БД"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    # Создание таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Удаление таблиц после тестов
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine):
    """Создание тестовой сессии БД"""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def mock_queue_service():
    """Mock для QueueService (нет подключения к реальному RabbitMQ)"""

    class MockQueueService(QueueService):
        def __init__(self):
            super().__init__()
            self.published_tasks = []

        async def connect(self):
            """Фейковое подключение"""
            pass

        async def disconnect(self):
            """Фейковое отключение"""
            pass

        async def publish_task(self, task_id: int, priority: str):
            """Сохранение вместо отправки в RabbitMQ"""
            self.published_tasks.append({"task_id": task_id, "priority": priority})

    return MockQueueService()


@pytest_asyncio.fixture
async def client(async_session, mock_queue_service):
    """HTTP клиент для тестирования API"""

    # Переопределение зависимостей
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db
    app.state.queue_service = mock_queue_service

    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
    ) as ac:
        yield ac

    # Чистим переопределения
    app.dependency_overrides.clear()


@pytest.fixture
def sample_task_data():
    """Пример данных для создания задачи"""
    return {
        "title": "Test Task",
        "description": "This is a test task",
        "priority": "HIGH"
    }
