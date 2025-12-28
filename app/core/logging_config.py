import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Настройка логирования для приложения"""

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    handlers = [
        logging.StreamHandler(sys.stdout)
    ]

    if log_file:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # Основной лог файл
        handlers.append(
            logging.FileHandler(log_dir / log_file, mode='a')
        )

        # Файл для ошибок
        error_handler = logging.FileHandler(log_dir / "errors.log", mode='a')
        error_handler.setLevel(logging.ERROR)
        handlers.append(error_handler)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
        force=True
    )

    # Отключение лишних логов
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("aio_pika").setLevel(logging.WARNING)
    logging.getLogger("aiormq").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")
