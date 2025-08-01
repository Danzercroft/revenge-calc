"""
Конфигурация логирования для приложения Revenge Calculator
"""
import logging
import logging.handlers
from datetime import datetime, timezone, timedelta
from pathlib import Path


def setup_logging(log_dir: str = "logs", log_level: int = logging.INFO):
    """
    Настраивает логирование с сохранением в файлы

    Args:
        log_dir: Директория для сохранения логов
        log_level: Уровень логирования
    """
    # Создаем директорию для логов если её нет
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Получаем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Очищаем существующие обработчики
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Формат для логов
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # 2. Обработчик для общих логов (все уровни)
    all_logs_file = log_path / "revenge_calc.log"
    file_handler = logging.handlers.RotatingFileHandler(
        all_logs_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # 3. Обработчик для ошибок (только ERROR и CRITICAL)
    error_logs_file = log_path / "errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_logs_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)

    # 4. Обработчик для сбора данных (отдельный файл для data_collection_service)
    data_collection_logger = logging.getLogger('data_collection_service')
    data_collection_file = log_path / "data_collection.log"
    data_collection_handler = logging.handlers.RotatingFileHandler(
        data_collection_file,
        maxBytes=20 * 1024 * 1024,  # 20MB для сбора данных
        backupCount=10,
        encoding='utf-8'
    )
    data_collection_handler.setLevel(logging.DEBUG)
    data_collection_handler.setFormatter(detailed_formatter)
    data_collection_logger.addHandler(data_collection_handler)

    # 5. Обработчик для обменных сервисов
    exchange_logger = logging.getLogger('exchange_service')
    exchange_file = log_path / "exchange.log"
    exchange_handler = logging.handlers.RotatingFileHandler(
        exchange_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    exchange_handler.setLevel(logging.DEBUG)
    exchange_handler.setFormatter(detailed_formatter)
    exchange_logger.addHandler(exchange_handler)

    # 6. Обработчик для API запросов
    api_logger = logging.getLogger('main')
    api_file = log_path / "api.log"
    api_handler = logging.handlers.RotatingFileHandler(
        api_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    api_handler.setLevel(logging.INFO)
    api_handler.setFormatter(detailed_formatter)
    api_logger.addHandler(api_handler)

    # 7. Ежедневные логи (TimedRotatingFileHandler)
    daily_logs_file = log_path / "daily.log"
    daily_handler = logging.handlers.TimedRotatingFileHandler(
        daily_logs_file,
        when='midnight',
        interval=1,
        backupCount=30,  # Храним 30 дней
        encoding='utf-8'
    )
    daily_handler.setLevel(logging.INFO)
    daily_handler.setFormatter(detailed_formatter)
    daily_handler.suffix = "%Y-%m-%d"
    root_logger.addHandler(daily_handler)

    # Логируем успешную настройку
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully. Log directory: %s", log_path.absolute())
    logger.info("Log files created:")
    logger.info("  - General logs: %s", all_logs_file)
    logger.info("  - Error logs: %s", error_logs_file)
    logger.info("  - Data collection logs: %s", data_collection_file)
    logger.info("  - Exchange logs: %s", exchange_file)
    logger.info("  - API logs: %s", api_file)
    logger.info("  - Daily logs: %s", daily_logs_file)


def get_log_files_info(log_dir: str = "logs") -> dict:
    """
    Получает информацию о файлах логов

    Args:
        log_dir: Директория с логами

    Returns:
        dict: Информация о файлах логов
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return {}

    log_files = {}
    for log_file in log_path.glob("*.log*"):
        try:
            stat = log_file.stat()
            log_files[log_file.name] = {
                "path": str(log_file.absolute()),
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "exists": True
            }
        except Exception as e:
            log_files[log_file.name] = {
                "path": str(log_file.absolute()),
                "error": str(e),
                "exists": False
            }

    return log_files


def clean_old_logs(log_dir: str = "logs", days_to_keep: int = 30):
    """
    Очищает старые файлы логов

    Args:
        log_dir: Директория с логами
        days_to_keep: Количество дней для хранения логов
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    logger = logging.getLogger(__name__)

    removed_count = 0
    for log_file in log_path.glob("*.log.*"):  # Только ротированные файлы
        try:
            stat = log_file.stat()
            file_date = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

            if file_date < cutoff_date:
                log_file.unlink()
                removed_count += 1
                logger.info("Removed old log file: %s", log_file.name)
        except Exception as e:
            logger.error("Error removing old log file %s: %s", log_file.name, str(e))

    if removed_count > 0:
        logger.info("Cleaned up %d old log files", removed_count)
