import asyncio
import json
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import aio_pika

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.task import TaskStatusEnum
from app.repositories.task_repository import TaskRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskWorker:
    def __init__(self, concurrency: int = 3):
        self.concurrency = concurrency
        self.repository = TaskRepository()

    async def process_task(self, task_id: int, db: AsyncSession):
        """Обработка одной задачи"""
        try:
            task = await self.repository.get_by_id(db, task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            if task.status != TaskStatusEnum.PENDING:
                logger.warning(f"Task {task_id} is not in PENDING status")
                return

            logger.info(f"Processing task {task_id}: {task.title}")

            task.status = TaskStatusEnum.IN_PROGRESS
            task.started_at = datetime.utcnow()
            await self.repository.update(db, task)

            # Симуляция работы (можно заменить на реальную логику)
            await asyncio.sleep(5)

            task.status = TaskStatusEnum.COMPLETED
            task.completed_at = datetime.utcnow()
            task.result = f"Task {task.title} completed successfully"
            await self.repository.update(db, task)

            logger.info(f"Task {task_id} completed")

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            try:
                task = await self.repository.get_by_id(db, task_id)
                if task:
                    task.status = TaskStatusEnum.FAILED
                    task.completed_at = datetime.utcnow()
                    task.error = str(e)
                    await self.repository.update(db, task)
            except Exception as update_error:
                logger.error(f"Failed to update task status: {update_error}")

    async def handle_message(self, message: aio_pika.IncomingMessage):
        """Обработка сообщения из очереди"""
        async with message.process():
            try:
                data = json.loads(message.body.decode())
                task_id = data.get("task_id")

                async with AsyncSessionLocal() as db:
                    await self.process_task(task_id, db)

            except Exception as e:
                logger.error(f"Error handling message: {e}")

    async def start(self):
        """Запуск worker'а"""
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=self.concurrency)

        queue = await channel.declare_queue(
            settings.rabbitmq_queue,
            durable=True,
            arguments={"x-max-priority": 10}
        )

        logger.info(f"Worker started with concurrency={self.concurrency}")
        await queue.consume(self.handle_message)

        try:
            await asyncio.Future()
        finally:
            await connection.close()


async def main():
    worker = TaskWorker(concurrency=3)
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())