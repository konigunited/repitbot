# -*- coding: utf-8 -*-
"""
Circuit Breaker for API Gateway
Реализация паттерна Circuit Breaker для защиты от каскадных сбоев
"""
import asyncio
import time
import logging
from typing import Dict, Optional, Any
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CircuitBreakerState(Enum):
    """Состояния Circuit Breaker"""
    CLOSED = "closed"      # Нормальная работа
    OPEN = "open"          # Сервис недоступен
    HALF_OPEN = "half_open"  # Пробное восстановление

class CircuitBreaker:
    """Circuit Breaker для защиты от сбоев сервиса"""
    
    def __init__(
        self, 
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        timeout: int = 30
    ):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.timeout = timeout
        
        # Состояние
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        
        # Статистика
        self.total_requests = 0
        self.total_failures = 0
        self.total_timeouts = 0
        
        self._lock = asyncio.Lock()
    
    async def record_success(self):
        """Записать успешный вызов"""
        async with self._lock:
            self.success_count += 1
            self.total_requests += 1
            self.last_success_time = datetime.now()
            
            # Если мы в состоянии HALF_OPEN и получили успех, переходим к CLOSED
            if self.state == CircuitBreakerState.HALF_OPEN:
                logger.info(f"Circuit breaker for {self.service_name}: HALF_OPEN -> CLOSED")
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
    
    async def record_failure(self):
        """Записать неудачный вызов"""
        async with self._lock:
            self.failure_count += 1
            self.total_requests += 1
            self.total_failures += 1
            self.last_failure_time = datetime.now()
            
            # Проверяем, нужно ли открыть circuit breaker
            if self.failure_count >= self.failure_threshold and self.state == CircuitBreakerState.CLOSED:
                logger.warning(f"Circuit breaker for {self.service_name}: CLOSED -> OPEN (failures: {self.failure_count})")
                self.state = CircuitBreakerState.OPEN
    
    async def record_timeout(self):
        """Записать таймаут"""
        async with self._lock:
            self.total_timeouts += 1
            await self.record_failure()  # Таймаут считается как неудача
    
    def is_open(self) -> bool:
        """Проверить, открыт ли circuit breaker"""
        if self.state == CircuitBreakerState.CLOSED:
            return False
        
        if self.state == CircuitBreakerState.OPEN:
            # Проверяем, не пора ли перейти в HALF_OPEN
            if self.last_failure_time and \
               (datetime.now() - self.last_failure_time).total_seconds() > self.recovery_timeout:
                logger.info(f"Circuit breaker for {self.service_name}: OPEN -> HALF_OPEN (recovery timeout reached)")
                self.state = CircuitBreakerState.HALF_OPEN
                return False
            return True
        
        # HALF_OPEN - пропускаем запросы для проверки
        return False
    
    def is_half_open(self) -> bool:
        """Проверить, в состоянии ли HALF_OPEN"""
        return self.state == CircuitBreakerState.HALF_OPEN
    
    def get_state(self) -> CircuitBreakerState:
        """Получить текущее состояние"""
        return self.state
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получить метрики circuit breaker"""
        success_rate = 0.0
        if self.total_requests > 0:
            success_rate = ((self.total_requests - self.total_failures) / self.total_requests) * 100
        
        return {
            "service_name": self.service_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "total_timeouts": self.total_timeouts,
            "success_rate": success_rate,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }
    
    def reset(self):
        """Сброс состояния circuit breaker"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        logger.info(f"Circuit breaker for {self.service_name} has been reset")

class CircuitBreakerManager:
    """Менеджер circuit breakers для всех сервисов"""
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
        self.default_config = {
            "failure_threshold": 5,
            "recovery_timeout": 60,
            "timeout": 30
        }
    
    def initialize(self):
        """Инициализация circuit breakers для всех сервисов"""
        services = [
            "user-service",
            "lesson-service", 
            "homework-service",
            "payment-service",
            "material-service",
            "notification-service",
            "analytics-service",
            "student-service"
        ]
        
        for service_name in services:
            self.breakers[service_name] = CircuitBreaker(
                service_name=service_name,
                **self.default_config
            )
        
        logger.info(f"Initialized circuit breakers for {len(services)} services")
    
    def get_breaker(self, service_name: str) -> CircuitBreaker:
        """Получить circuit breaker для сервиса"""
        if service_name not in self.breakers:
            # Создаем новый breaker если его нет
            self.breakers[service_name] = CircuitBreaker(
                service_name=service_name,
                **self.default_config
            )
        
        return self.breakers[service_name]
    
    def get_all_breakers(self) -> Dict[str, CircuitBreaker]:
        """Получить все circuit breakers"""
        return self.breakers.copy()
    
    def get_status(self) -> Dict[str, str]:
        """Получить статус всех circuit breakers"""
        return {
            name: breaker.get_state().value
            for name, breaker in self.breakers.items()
        }
    
    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Получить метрики всех circuit breakers"""
        return {
            name: breaker.get_metrics()
            for name, breaker in self.breakers.items()
        }
    
    def reset_breaker(self, service_name: str):
        """Сброс конкретного circuit breaker"""
        if service_name in self.breakers:
            self.breakers[service_name].reset()
    
    def reset_all_breakers(self):
        """Сброс всех circuit breakers"""
        for breaker in self.breakers.values():
            breaker.reset()
        logger.info("All circuit breakers have been reset")
    
    async def start_metrics_collection(self):
        """Запуск сбора метрик circuit breakers"""
        logger.info("Starting circuit breaker metrics collection...")
        
        while True:
            try:
                # Логируем статистику каждые 5 минут
                await asyncio.sleep(300)
                
                open_breakers = [
                    name for name, breaker in self.breakers.items()
                    if breaker.get_state() == CircuitBreakerState.OPEN
                ]
                
                half_open_breakers = [
                    name for name, breaker in self.breakers.items()
                    if breaker.get_state() == CircuitBreakerState.HALF_OPEN
                ]
                
                if open_breakers:
                    logger.warning(f"Open circuit breakers: {', '.join(open_breakers)}")
                
                if half_open_breakers:
                    logger.info(f"Half-open circuit breakers: {', '.join(half_open_breakers)}")
                
                # Логируем общую статистику
                total_requests = sum(breaker.total_requests for breaker in self.breakers.values())
                total_failures = sum(breaker.total_failures for breaker in self.breakers.values())
                
                if total_requests > 0:
                    overall_success_rate = ((total_requests - total_failures) / total_requests) * 100
                    logger.info(f"Overall success rate: {overall_success_rate:.2f}% ({total_requests} requests, {total_failures} failures)")
                
            except asyncio.CancelledError:
                logger.info("Circuit breaker metrics collection cancelled")
                break
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")

# Глобальный экземпляр менеджера
_circuit_breaker_manager: Optional[CircuitBreakerManager] = None

def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Получение глобального экземпляра менеджера circuit breakers"""
    global _circuit_breaker_manager
    if _circuit_breaker_manager is None:
        _circuit_breaker_manager = CircuitBreakerManager()
    return _circuit_breaker_manager