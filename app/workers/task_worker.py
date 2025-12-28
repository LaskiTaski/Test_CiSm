import asyncio
import logging
from datetime import datetime
from typing import Set
from sqlalchemy.ext.asyncio import AsyncSession
import aio_pika

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.metrics import (
    tasks_failed_total,
    track_task_processing
)
from app.models.task import TaskStatusEnum
from app.repositories.task_repository import TaskRepository

# Настройка логирования для worker
setup_logging(log_level=settings.log_level, log_file="worker.log")
logger = logging.getLogger(__name__)


class TaskWorker:
    def __init__(self, concurrency: int = None):
        self.concurrency = concurrency or settings.worker_concurrency
        self.max_retries = settings.worker_max_retries
        self.repository = TaskRepository()
        self.shutdown_event = asyncio.Event()
        self.active_tasks: Set[asyncio.Task] = set()
        self.connection = None
        self.channel = None

    @track_task_processing()
    async def process_task(self, task_id: int, db: AsyncSession):
        """Обработка одной задачи"""
        try:
            task = await self.repository.get_by_id(db, task_id)
            if not task:
                logger.error(f"Task {task_id} not found in database")
                return

            if task.status != TaskStatusEnum.PENDING:
                logger.warning(f"Task {task_id} is in '{task.status}' status, expected PENDING")
                return

            logger.info(f"Processing task {task_id}: '{task.title}' (priority: {task.priority})")

            # Устанавливаем статус IN_PROGRESS
            task.status = TaskStatusEnum.IN_PROGRESS
            task.started_at = datetime.utcnow()
            await self.repository.update(db, task)

            # Симуляция работы (Можно заменить на реальную бизнес-логику)
            await asyncio.sleep(5)

            # Успешное завершение
            task.status = TaskStatusEnum.COMPLETED
            task.completed_at = datetime.utcnow()
            task.result = f"Task '{task.title}' completed successfully"
            await self.repository.update(db, task)

            logger.info(f"Task {task_id} completed successfully")

        except asyncio.CancelledError:
            logger.warning(f"Task {task_id} processing was cancelled")
            raise
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)

            # Обновляем статус на FAILED
            try:
                task = await self.repository.get_by_id(db, task_id)
                if task:
                    task.status = TaskStatusEnum.FAILED
                    task.completed_at = datetime.utcnow()
                    task.error = str(e)
                    await self.repository.update(db, task)
                    tasks_failed_total.inc()
            except Exception as update_error:
                logger.error(f"Failed to update task {task_id} status to FAILED: {update_error}")
            raise

    async def handle_message(self, message: aio_pika.IncomingMessage):
        """Обработка сообщения из очереди с retry логикой"""
        retry_count = message
