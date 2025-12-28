from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatusEnum
from app.schemas.task import TaskCreate, TaskPriority, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.services.queue_service import QueueService
from app.core.metrics import tasks_created_total, tasks_cancelled_total


class TaskService:
    def __init__(self, queue_service: QueueService):
        self.queue_service = queue_service
        self.repository = TaskRepository()

    async def create_task(self, db: AsyncSession, task_in: TaskCreate) -> Task:
        """Создание новой задачи"""
        task = Task(
            title=task_in.title,
            description=task_in.description,
            priority=task_in.priority,
            status=TaskStatusEnum.NEW,
        )
        task = await self.repository.create(db, task)

        # Обновляем статус на PENDING и публикуем в очередь
        task.status = TaskStatusEnum.PENDING
        task = await self.repository.update(db, task)

        # Публикуем в RabbitMQ
        await self.queue_service.publish_task(task.id, task.priority.value)

        # Метрики
        tasks_created_total.labels(priority=task.priority.value).inc()

        return task

    async def get_task(self, db: AsyncSession, task_id: int) -> Optional[Task]:
        """Получение задачи по ID"""
        return await self.repository.get_by_id(db, task_id)

    async def list_tasks(
            self,
            db: AsyncSession,
            page: int = 1,
            page_size: int = 10,
            status: Optional[TaskStatus] = None,
            priority: Optional[TaskPriority] = None,
    ) -> tuple[list[Task], int]:
        """Получение списка задач с фильтрацией и пагинацией"""
        return await self.repository.list_with_filters(
            db, page, page_size, status, priority
        )

    async def cancel_task(self, db: AsyncSession, task_id: int) -> bool:
        """Отмена задачи"""
        task = await self.repository.get_by_id(db, task_id)
        if not task:
            return False

        # Можно отменить только задачи в статусах NEW, PENDING
        if task.status not in [TaskStatusEnum.NEW, TaskStatusEnum.PENDING]:
            return False

        task.status = TaskStatusEnum.CANCELLED
        await self.repository.update(db, task)

        # Метрики
        tasks_cancelled_total.inc()

        return True
