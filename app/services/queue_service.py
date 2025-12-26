import json
import logging
from typing import Optional
import aio_pika
from aio_pika import Message, DeliveryMode, connect_robust
from aio_pika.abc import AbstractChannel, AbstractConnection

from app.core.config import settings

logger = logging.getLogger(__name__)


class QueueService:
    def __init__(self):
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.queue_name = settings.rabbitmq_queue

    async def connect(self):
        """Подключение к RabbitMQ"""
        try:
            self.connection = await connect_robust(settings.rabbitmq_url)
            self.channel = await self.connection.channel()
            await self.channel.declare_queue(
                self.queue_name,
                durable=True,
                arguments={"x-max-priority": 10}
            )
            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self):
        """Отключение от RabbitMQ"""
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()
        logger.info("Disconnected from RabbitMQ")

    async def publish_task(self, task_id: int, priority: str):
        """Публикация задачи в очередь"""
        if not self.channel:
            await self.connect()

        priority_map = {"LOW": 1, "MEDIUM": 5, "HIGH": 10}
        priority_value = priority_map.get(priority, 5)

        message_body = json.dumps({"task_id": task_id})
        message = Message(
            body=message_body.encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            priority=priority_value,
        )

        await self.channel.default_exchange.publish(
            message,
            routing_key=self.queue_name,
        )
        logger.info(f"Published task {task_id} with priority {priority}")