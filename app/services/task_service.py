from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatusEnum
from app.schemas.task import TaskCreate, TaskPriority, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.services.queue_service import QueueService


class TaskService:
    def __init__(self, queue_service: QueueService):
        self.queue_service = queue_service
        self.repository = TaskRepository()

    async def create_task(self, db: AsyncSession, task_in: TaskCreate) -> Task:
        task = Task(
            title=task_in.title,
            description=task_in.description,
            priority=task_in.priority,
            status=TaskStatusEnum.NEW,
        )
        task = await self.repository.create(db, task)

        task.status = TaskStatusEnum.PENDING
        task = await self.repository.update(db, task)

        await self.queue_service.publish_task(task.id, task.priority.value)
        return task

    async def get_task(self, db: AsyncSession, task_id: int) -> Optional[Task]:
        return await self.repository.get_by_id(db, task_id)

    async def list_tasks(
            self,
            db: AsyncSession,
            page: int = 1,
            page_size: int = 10,
            status: Optional[TaskStatus] = None,
            priority: Optional[TaskPriority] = None,
    ) -> tuple[list[Task], int]:
        return await self.repository.list_with_filters(
            db, page, page_size, status, priority
        )

    async def cancel_task(self, db: AsyncSession, task_id: int) -> bool:
        task = await self.repository.get_by_id(db, task_id)
        if not task:
            return False

        if task.status not in [TaskStatusEnum.NEW, TaskStatusEnum.PENDING]:
            return False

        task.status = TaskStatusEnum.CANCELLED
        await self.repository.update(db, task)
        return True
