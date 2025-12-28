from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps

# Метрики для задач
tasks_created_total = Counter(
    'tasks_created_total',
    'Total number of tasks created',
    ['priority']
)

tasks_completed_total = Counter(
    'tasks_completed_total',
    'Total number of tasks completed successfully'
)

tasks_failed_total = Counter(
    'tasks_failed_total',
    'Total number of tasks failed'
)

tasks_cancelled_total = Counter(
    'tasks_cancelled_total',
    'Total number of tasks cancelled'
)

# Время обработки задач
task_processing_duration_seconds = Histogram(
    'task_processing_duration_seconds',
    'Time spent processing tasks',
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300]
)

# Активные задачи в данный момент
active_tasks_gauge = Gauge(
    'active_tasks',
    'Number of tasks currently being processed'
)

# Метрики RabbitMQ
rabbitmq_messages_published = Counter(
    'rabbitmq_messages_published_total',
    'Total messages published to RabbitMQ'
)

rabbitmq_messages_consumed = Counter(
    'rabbitmq_messages_consumed_total',
    'Total messages consumed from RabbitMQ'
)


def track_task_processing():
    """Отслеживание времени обработки задачи"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            active_tasks_gauge.inc()
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                tasks_completed_total.inc()
                return result
            except Exception as e:
                tasks_failed_total.inc()
                raise
            finally:
                duration = time.time() - start_time
                task_processing_duration_seconds.observe(duration)
                active_tasks_gauge.dec()

        return wrapper

    return decorator
