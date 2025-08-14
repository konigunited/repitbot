# -*- coding: utf-8 -*-
"""
Профессиональная система логирования для Telegram бота репетитора.
Включает структурированные логи, ротацию файлов и мониторинг производительности.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional
import functools
import time

class ColoredFormatter(logging.Formatter):
    """Цветной форматтер для консольного вывода"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'ENDC': '\033[0m',      # End color
    }
    
    def format(self, record):
        if hasattr(record, 'user_id'):
            record.msg = f"[User:{record.user_id}] {record.msg}"
            
        log_color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['ENDC']}"
        return super().format(record)

def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> logging.Logger:
    """
    Настраивает профессиональную систему логирования
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Директория для файлов логов
        
    Returns:
        Настроенный logger
    """
    
    # Создаем директорию для логов
    os.makedirs(log_dir, exist_ok=True)
    
    # Основной logger
    logger = logging.getLogger('RepitBot')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Очищаем существующие handlers
    logger.handlers.clear()
    
    # Форматтер для файлов
    file_formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Форматтер для консоли
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Handler для основного лога с ротацией
    main_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'repitbot.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    main_handler.setFormatter(file_formatter)
    main_handler.setLevel(logging.INFO)
    logger.addHandler(main_handler)
    
    # Handler для ошибок
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'errors.log'),
        maxBytes=5*1024*1024,   # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setFormatter(file_formatter)
    error_handler.setLevel(logging.ERROR)
    logger.addHandler(error_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(console_handler)
    
    # Отдельный logger для пользовательских действий
    user_logger = logging.getLogger('RepitBot.UserActions')
    user_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'user_actions.log'),
        maxBytes=5*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    user_handler.setFormatter(file_formatter)
    user_logger.addHandler(user_handler)
    
    # Performance logger
    perf_logger = logging.getLogger('RepitBot.Performance')
    perf_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'performance.log'),
        maxBytes=5*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    perf_handler.setFormatter(file_formatter)
    perf_logger.addHandler(perf_handler)
    
    logger.info("Система логирования инициализирована")
    return logger

def log_user_action(user_id: int, action: str, details: Optional[str] = None):
    """Логирует действия пользователей"""
    user_logger = logging.getLogger('RepitBot.UserActions')
    message = f"User {user_id} - {action}"
    if details:
        message += f" | {details}"
    user_logger.info(message)

def performance_monitor(func):
    """Декоратор для мониторинга производительности функций"""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        perf_logger = logging.getLogger('RepitBot.Performance')
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            perf_logger.info(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            perf_logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        perf_logger = logging.getLogger('RepitBot.Performance')
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            perf_logger.info(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            perf_logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    if hasattr(func, '__code__') and 'await' in func.__code__.co_names:
        return async_wrapper
    else:
        return sync_wrapper

class BotMetrics:
    """Класс для сбора метрик бота"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.message_count = 0
        self.error_count = 0
        self.active_users = set()
        self.command_stats = {}
    
    def record_message(self, user_id: int, command: Optional[str] = None):
        """Записывает статистику сообщения"""
        self.message_count += 1
        self.active_users.add(user_id)
        
        if command:
            self.command_stats[command] = self.command_stats.get(command, 0) + 1
    
    def record_error(self):
        """Записывает ошибку"""
        self.error_count += 1
    
    def get_stats(self) -> dict:
        """Возвращает текущую статистику"""
        uptime = datetime.now() - self.start_time
        return {
            'uptime_hours': round(uptime.total_seconds() / 3600, 2),
            'total_messages': self.message_count,
            'total_errors': self.error_count,
            'active_users': len(self.active_users),
            'error_rate': round(self.error_count / max(self.message_count, 1) * 100, 2),
            'top_commands': dict(sorted(self.command_stats.items(), key=lambda x: x[1], reverse=True)[:5])
        }

# Глобальный экземпляр метрик
metrics = BotMetrics()

def log_telegram_error(logger: logging.Logger, update, context, error_type: str = "Unknown"):
    """Специальная функция для логирования ошибок Telegram"""
    user_id = None
    message_text = None
    
    try:
        if update and hasattr(update, 'effective_user') and update.effective_user:
            user_id = update.effective_user.id
        
        if update and hasattr(update, 'message') and update.message:
            message_text = update.message.text
        elif update and hasattr(update, 'callback_query') and update.callback_query:
            message_text = f"Callback: {update.callback_query.data}"
    except Exception:
        pass
    
    error_details = {
        'error_type': error_type,
        'user_id': user_id,
        'message': message_text,
        'error': str(context.error) if context and hasattr(context, 'error') else 'Unknown error'
    }
    
    logger.error(f"Telegram error: {error_details}")
    metrics.record_error()

# Создаем базовый logger при импорте модуля
logger = setup_logging()