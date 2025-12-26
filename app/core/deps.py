from typing import AsyncGenerator
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.task_service import TaskService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


async def get_task_service(request: Request) -> TaskService:
    queue_service = request.app.state.queue_service
    return TaskService(queue_service=queue_service)