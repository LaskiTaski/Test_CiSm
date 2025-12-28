import pytest
from app.models.task import TaskStatusEnum, TaskPriorityEnum
from app.schemas.task import TaskCreate
from app.services.task_service import TaskService


@pytest.mark.asyncio
class TestTaskService:
    """Тесты для TaskService"""

    async def test_create_task(self, async_session, mock_queue_service):
        """Тест создания задачи через сервис"""
        service = TaskService(queue_service=mock_queue_service)

        task_in = TaskCreate(
            title="Service Test Task",
            description="Testing service layer",
            priority="MEDIUM"
        )

        task = await service.create_task(async_session, task_in)

        assert task.id is not None
        assert task.title == "Service Test Task"
        assert task.status == TaskStatusEnum.PENDING
        assert len(mock_queue_service.published_tasks) == 1

    async def test_get_task(self, async_session, mock_queue_service):
        """Тест получения задачи"""
        service = TaskService(queue_service=mock_queue_service)

        # Создание задачи
        task_in = TaskCreate(title="Test", priority="LOW")
        created_task = await service.create_task(async_session, task_in)

        # Получение задачи
        retrieved_task = await service.get_task(async_session, created_task.id)

        assert retrieved_task is not None
        assert retrieved_task.id == created_task.id
        assert retrieved_task.title == "Test"

    async def test_get_nonexistent_task(self, async_session, mock_queue_service):
        """Тест получения несуществующей задачи"""
        service = TaskService(queue_service=mock_queue_service)

        task = await service.get_task(async_session, 99999)

        assert task is None

    async def test_cancel_task(self, async_session, mock_queue_service):
        """Тест отмены задачи"""
        service = TaskService(queue_service=mock_queue_service)

        # Создание задачи
        task_in = TaskCreate(title="To Cancel", priority="HIGH")
        created_task = await service.create_task(async_session, task_in)

        # Отмена задачи
        success = await service.cancel_task(async_session, created_task.id)

        assert success is True

        # Проверка статуса
        cancelled_task = await service.get_task(async_session, created_task.id)
        assert cancelled_task.status == TaskStatusEnum.CANCELLED

    async def test_list_tasks_with_filters(self, async_session, mock_queue_service):
        """Тест получения списка с фильтрами"""
        service = TaskService(queue_service=mock_queue_service)

        # Создание задачи
        await service.create_task(async_session, TaskCreate(title="High1", priority="HIGH"))
        await service.create_task(async_session, TaskCreate(title="High2", priority="HIGH"))
        await service.create_task(async_session, TaskCreate(title="Low", priority="LOW"))

        # Получаем задачи с фильтром HIGH
        tasks, total = await service.list_tasks(
            async_session,
            page=1,
            page_size=10,
            priority="HIGH"
        )

        assert total == 2
        assert len(tasks) == 2
        assert all(task.priority == TaskPriorityEnum.HIGH for task in tasks)
