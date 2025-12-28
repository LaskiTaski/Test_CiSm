import json
import logging
from typing import Optional
from aio_pika import Message, DeliveryMode, connect_robust
from aio_pika.abc import AbstractChannel, AbstractConnection

from app.core.config import settings
from app.core.metrics import rabbitmq_messages_published

logger = logging.getLogger(__name__)


class QueueService:
    def __init__(self):
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.queue_name = settings.rabbitmq_queue

    async def connect(self):
        """Подключение к RabbitMQ"""
        try:
            logger.info(f"Connecting to RabbitMQ at {settings.rabbitmq_host}:{settings.rabbitmq_port}")
            self.connection = await connect_robust(
                settings.rabbitmq_url,
                timeout=10
            )
            self.channel = await self.connection.channel()

            # Декларируем очередь с приоритетами
            await self.channel.declare_queue(
                self.queue_name,
                durable=True,
                arguments={"x-max-priority": 10}
            )

            logger.info(f"Connected to RabbitMQ, queue '{self.queue_name}' declared")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self):
        """Отключение от RabbitMQ"""
        try:
            if self.channel:
                await self.channel.close()
                logger.info("RabbitMQ channel closed")
            if self.connection:
                await self.connection.close()
                logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")

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

        try:
            await self.channel.default_exchange.publish(
                message,
                routing_key=self.queue_name,
            )
            rabbitmq_messages_published.inc()
            logger.info(f"Published task {task_id} with priority {priority} (value={priority_value})")
        except Exception as e:
            logger.error(f"Failed to publish task {task_id}: {e}")
            raise
