from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    project_name: str = "Task Service"
    version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"

    # Logging
    log_level: str = "INFO"

    # PostgreSQL
    postgres_user: str
    postgres_password: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str

    # PostgreSQL pool settings
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600

    # RabbitMQ
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str
    rabbitmq_password: str
    rabbitmq_queue: str = "tasks"

    # Worker settings
    worker_concurrency: int = 3
    worker_max_retries: int = 3

    # CORS
    cors_origins: list[str] = ["*"]

    # Features
    enable_metrics: bool = True

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def rabbitmq_url(self) -> str:
        return f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_port}/"


settings = Settings()
