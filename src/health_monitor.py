# -*- coding: utf-8 -*-
"""
Система мониторинга здоровья бота и автоматического восстановления.
Включает health checks, автоматическое восстановление соединений и уведомления.
"""

import asyncio
import logging
import time
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger('RepitBot.HealthMonitor')

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"

@dataclass
class HealthCheck:
    name: str
    check_func: Callable
    interval: int  # секунды
    timeout: int   # секунды
    last_check: Optional[datetime] = None
    last_status: HealthStatus = HealthStatus.HEALTHY
    failure_count: int = 0
    max_failures: int = 3

class HealthMonitor:
    """Мониторинг здоровья системы"""
    
    def __init__(self, bot_application=None):
        self.bot_application = bot_application
        self.checks: Dict[str, HealthCheck] = {}
        self.is_running = False
        self.monitor_task = None
        self.start_time = datetime.now()
        
    def add_check(self, name: str, check_func: Callable, interval: int = 60, 
                  timeout: int = 10, max_failures: int = 3):
        """Добавляет новую проверку здоровья"""
        self.checks[name] = HealthCheck(
            name=name,
            check_func=check_func,
            interval=interval,
            timeout=timeout,
            max_failures=max_failures
        )
        logger.info(f"Добавлена проверка здоровья: {name} (интервал: {interval}с)")
    
    async def run_check(self, check: HealthCheck) -> HealthStatus:
        """Выполняет одну проверку здоровья"""
        try:
            # Выполняем проверку с таймаутом
            result = await asyncio.wait_for(
                check.check_func(),
                timeout=check.timeout
            )
            
            if result:
                check.failure_count = 0
                check.last_status = HealthStatus.HEALTHY
                return HealthStatus.HEALTHY
            else:
                check.failure_count += 1
                if check.failure_count >= check.max_failures:
                    check.last_status = HealthStatus.CRITICAL
                    return HealthStatus.CRITICAL
                else:
                    check.last_status = HealthStatus.WARNING
                    return HealthStatus.WARNING
                    
        except asyncio.TimeoutError:
            check.failure_count += 1
            check.last_status = HealthStatus.CRITICAL
            logger.error(f"Health check {check.name} timeout after {check.timeout}s")
            return HealthStatus.CRITICAL
            
        except Exception as e:
            check.failure_count += 1
            check.last_status = HealthStatus.CRITICAL
            logger.error(f"Health check {check.name} failed: {e}")
            return HealthStatus.CRITICAL
    
    async def start_monitoring(self):
        """Запускает мониторинг"""
        if self.is_running:
            return
            
        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Мониторинг здоровья запущен")
    
    async def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.is_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️ Мониторинг здоровья остановлен")
    
    async def _monitor_loop(self):
        """Основной цикл мониторинга"""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                for check in self.checks.values():
                    # Проверяем, нужно ли выполнить проверку
                    if (not check.last_check or 
                        (current_time - check.last_check).seconds >= check.interval):
                        
                        status = await self.run_check(check)
                        check.last_check = current_time
                        
                        if status == HealthStatus.CRITICAL:
                            await self._handle_critical_failure(check)
                        elif status == HealthStatus.WARNING:
                            await self._handle_warning(check)
                
                await asyncio.sleep(10)  # Проверяем каждые 10 секунд
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(30)
    
    async def _handle_critical_failure(self, check: HealthCheck):
        """Обрабатывает критические сбои"""
        logger.critical(f"CRITICAL: Health check {check.name} failed {check.failure_count} times")
        
        # Попытка автоматического восстановления
        if check.name == "database_connection":
            await self._recover_database()
        elif check.name == "bot_connection":
            await self._recover_bot_connection()
    
    async def _handle_warning(self, check: HealthCheck):
        """Обрабатывает предупреждения"""
        logger.warning(f"WARNING: Health check {check.name} failed {check.failure_count} times")
    
    async def _recover_database(self):
        """Попытка восстановления подключения к БД"""
        try:
            from .database import engine, SessionLocal
            
            # Попытка переподключения
            db = SessionLocal()
            db.execute("SELECT 1")
            db.close()
            
            logger.info("Database connection recovered")
            
        except Exception as e:
            logger.error(f"❌ Failed to recover database: {e}")
    
    async def _recover_bot_connection(self):
        """Попытка восстановления подключения к Telegram"""
        try:
            if self.bot_application and self.bot_application.bot:
                me = await self.bot_application.bot.get_me()
                logger.info(f"Bot connection recovered: {me.username}")
                
        except Exception as e:
            logger.error(f"❌ Failed to recover bot connection: {e}")
    
    def get_health_report(self) -> Dict:
        """Возвращает отчет о здоровье системы"""
        uptime = datetime.now() - self.start_time
        
        checks_status = {}
        overall_status = HealthStatus.HEALTHY
        
        for name, check in self.checks.items():
            checks_status[name] = {
                'status': check.last_status.value,
                'last_check': check.last_check.isoformat() if check.last_check else None,
                'failure_count': check.failure_count,
                'next_check_in': check.interval - (datetime.now() - check.last_check).seconds if check.last_check else 0
            }
            
            # Определяем общий статус
            if check.last_status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
            elif check.last_status == HealthStatus.WARNING and overall_status != HealthStatus.CRITICAL:
                overall_status = HealthStatus.WARNING
        
        return {
            'overall_status': overall_status.value,
            'uptime_seconds': int(uptime.total_seconds()),
            'checks': checks_status,
            'system_info': self._get_system_info()
        }
    
    def _get_system_info(self) -> Dict:
        """Получает информацию о системе"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:\\').percent,
                'process_memory_mb': round(psutil.Process().memory_info().rss / 1024 / 1024, 2)
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {}

# Предустановленные проверки здоровья

async def check_database_connection():
    """Проверка подключения к базе данных"""
    try:
        from .database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception:
        return False

async def check_bot_connection():
    """Проверка подключения к Telegram API"""
    try:
        # Эта функция должна быть вызвана с передачей bot instance
        # Реализация зависит от конкретного bot application
        return True
    except Exception:
        return False

async def check_disk_space():
    """Проверка свободного места на диске"""
    try:
        disk_path = '/' if os.name != 'nt' else 'C:\\'
        usage = psutil.disk_usage(disk_path)
        free_percent = (usage.free / usage.total) * 100
        return free_percent > 10  # Более 10% свободного места
    except Exception:
        return False

async def check_memory_usage():
    """Проверка использования памяти"""
    try:
        memory = psutil.virtual_memory()
        return memory.percent < 90  # Менее 90% использования памяти
    except Exception:
        return False

# Глобальный экземпляр монитора
health_monitor = HealthMonitor()

def setup_default_checks():
    """Настраивает стандартные проверки здоровья"""
    health_monitor.add_check("database_connection", check_database_connection, interval=60)
    health_monitor.add_check("disk_space", check_disk_space, interval=300)  # каждые 5 минут
    health_monitor.add_check("memory_usage", check_memory_usage, interval=120)  # каждые 2 минуты
    logger.info("Стандартные проверки здоровья настроены")