from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskPriority, TaskStatus


class TaskRepository:
    @staticmethod
    async def create(db: AsyncSession, task: Task) -> Task:
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    async def get_by_id(db: AsyncSession, task_id: int) -> Optional[Task]:
        result = await db.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update(db: AsyncSession, task: Task) -> Task:
        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    async def list_with_filters(
            db: AsyncSession,
            page: int,
            page_size: int,
            status: Optional[TaskStatus] = None,
            priority: Optional[TaskPriority] = None,
    ) -> tuple[list[Task], int]:
        query = select(Task)

        if status:
            query = query.where(Task.status == status)
        if priority:
            query = query.where(Task.priority == priority)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        query = query.order_by(Task.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        tasks = result.scalars().all()

        return list(tasks), total
