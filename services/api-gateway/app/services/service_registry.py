# -*- coding: utf-8 -*-
"""
Service Registry for API Gateway
Реестр сервисов и service discovery
"""
import asyncio
import httpx
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """Реестр микросервисов и их состояния"""
    
    def __init__(self):
        self.services: Dict[str, Dict] = {}
        self.healthy_services: Set[str] = set()
        self.unhealthy_services: Set[str] = set()
        self.last_health_check: Optional[datetime] = None
        self._lock = asyncio.Lock()
        
        # Конфигурация сервисов
        self.service_configs = {
            "user-service": {
                "host": "user-service", 
                "port": 8001,
                "health_endpoint": "/health",
                "timeout": 5.0,
                "critical": True  # Критически важный сервис
            },
            "lesson-service": {
                "host": "lesson-service",
                "port": 8002,
                "health_endpoint": "/health", 
                "timeout": 5.0,
                "critical": True
            },
            "homework-service": {
                "host": "homework-service",
                "port": 8003,
                "health_endpoint": "/health",
                "timeout": 5.0,
                "critical": False
            },
            "payment-service": {
                "host": "payment-service",
                "port": 8004,
                "health_endpoint": "/health",
                "timeout": 5.0,
                "critical": True
            },
            "material-service": {
                "host": "material-service", 
                "port": 8005,
                "health_endpoint": "/health",
                "timeout": 5.0,
                "critical": False
            },
            "notification-service": {
                "host": "notification-service",
                "port": 8006,
                "health_endpoint": "/health",
                "timeout": 5.0,
                "critical": False
            },
            "analytics-service": {
                "host": "analytics-service",
                "port": 8007,
                "health_endpoint": "/health",
                "timeout": 5.0,
                "critical": False
            },
            "student-service": {
                "host": "student-service",
                "port": 8008,
                "health_endpoint": "/health",
                "timeout": 5.0,
                "critical": False
            }
        }
        
        # Инициализируем сервисы
        for service_name, config in self.service_configs.items():
            self.services[service_name] = {
                "name": service_name,
                "host": config["host"],
                "port": config["port"],
                "url": f"http://{config['host']}:{config['port']}",
                "health_endpoint": config["health_endpoint"],
                "timeout": config["timeout"],
                "critical": config["critical"],
                "status": "unknown",
                "last_check": None,
                "last_success": None,
                "last_failure": None,
                "failure_count": 0,
                "response_time": None,
                "metadata": {}
            }
    
    async def initialize(self):
        """Инициализация реестра сервисов"""
        logger.info("Initializing service registry...")
        await self.update_all_services_health()
        logger.info(f"Service registry initialized with {len(self.services)} services")
    
    async def get_service_url(self, service_name: str) -> Optional[str]:
        """Получение URL сервиса"""
        service = self.services.get(service_name)
        if not service:
            return None
        
        # Возвращаем URL только если сервис здоров
        if service["status"] == "healthy":
            return service["url"]
        
        return None
    
    async def get_all_services(self) -> Dict[str, Dict]:
        """Получение всех зарегистрированных сервисов"""
        return self.services.copy()
    
    async def get_healthy_services(self) -> List[str]:
        """Получение списка здоровых сервисов"""
        return list(self.healthy_services)
    
    async def get_unhealthy_services(self) -> List[str]:
        """Получение списка нездоровых сервисов"""
        return list(self.unhealthy_services)
    
    async def get_services_status(self) -> Dict[str, str]:
        """Получение статуса всех сервисов"""
        return {
            name: service["status"] 
            for name, service in self.services.items()
        }
    
    async def get_detailed_services_info(self) -> Dict[str, Dict]:
        """Получение детальной информации о сервисах"""
        return {
            name: {
                "status": service["status"],
                "url": service["url"],
                "last_check": service["last_check"].isoformat() if service["last_check"] else None,
                "last_success": service["last_success"].isoformat() if service["last_success"] else None,
                "failure_count": service["failure_count"],
                "response_time": service["response_time"],
                "critical": service["critical"],
                "metadata": service["metadata"]
            }
            for name, service in self.services.items()
        }
    
    async def check_service_health(self, service_name: str) -> bool:
        """Проверка здоровья конкретного сервиса"""
        service = self.services.get(service_name)
        if not service:
            logger.warning(f"Service {service_name} not found in registry")
            return False
        
        health_url = f"{service['url']}{service['health_endpoint']}"
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=service["timeout"]) as client:
                response = await client.get(health_url)
                
            response_time = time.time() - start_time
            is_healthy = response.status_code == 200
            
            # Обновляем информацию о сервисе
            async with self._lock:
                service["last_check"] = datetime.now()
                service["response_time"] = response_time
                
                if is_healthy:
                    service["status"] = "healthy"
                    service["last_success"] = datetime.now()
                    service["failure_count"] = 0
                    
                    # Добавляем в здоровые сервисы
                    self.healthy_services.add(service_name)
                    self.unhealthy_services.discard(service_name)
                    
                    # Обновляем метаданные из ответа
                    try:
                        if response.headers.get("content-type", "").startswith("application/json"):
                            health_data = response.json()
                            service["metadata"].update(health_data)
                    except Exception:
                        pass
                        
                else:
                    service["status"] = "unhealthy"
                    service["last_failure"] = datetime.now()
                    service["failure_count"] += 1
                    
                    # Добавляем в нездоровые сервисы
                    self.unhealthy_services.add(service_name)
                    self.healthy_services.discard(service_name)
            
            logger.debug(f"Health check for {service_name}: {'OK' if is_healthy else 'FAILED'} ({response_time:.3f}s)")
            return is_healthy
            
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning(f"Health check timeout/connection error for {service_name}: {e}")
        except Exception as e:
            logger.error(f"Health check error for {service_name}: {e}")
        
        # Обновляем при ошибке
        async with self._lock:
            service["last_check"] = datetime.now()
            service["status"] = "unhealthy"
            service["last_failure"] = datetime.now()
            service["failure_count"] += 1
            service["response_time"] = time.time() - start_time
            
            self.unhealthy_services.add(service_name)
            self.healthy_services.discard(service_name)
        
        return False
    
    async def update_all_services_health(self):
        """Обновление здоровья всех сервисов"""
        logger.debug("Checking health of all services...")
        
        # Проверяем все сервисы параллельно
        tasks = [
            self.check_service_health(service_name)
            for service_name in self.services.keys()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Подсчитываем результаты
        healthy_count = sum(1 for result in results if result is True)
        total_count = len(self.services)
        
        self.last_health_check = datetime.now()
        
        logger.info(f"Health check completed: {healthy_count}/{total_count} services healthy")
        
        # Логируем критические сервисы, которые недоступны
        for service_name, service in self.services.items():
            if service["critical"] and service["status"] != "healthy":
                logger.error(f"Critical service {service_name} is unhealthy!")
    
    async def start_health_checks(self):
        """Запуск периодических проверок здоровья"""
        logger.info("Starting periodic health checks...")
        
        while True:
            try:
                await self.update_all_services_health()
                await asyncio.sleep(30)  # Проверяем каждые 30 секунд
            except asyncio.CancelledError:
                logger.info("Health check task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(10)  # Ждем меньше при ошибке
    
    async def is_service_available(self, service_name: str) -> bool:
        """Проверка доступности сервиса"""
        service = self.services.get(service_name)
        if not service:
            return False
        
        return service["status"] == "healthy"
    
    async def get_service_load_balancing_candidates(self, service_name: str) -> List[str]:
        """Получение кандидатов для балансировки нагрузки (пока что один экземпляр)"""
        if await self.is_service_available(service_name):
            return [service_name]
        return []
    
    async def mark_service_failure(self, service_name: str):
        """Отметить сбой сервиса"""
        service = self.services.get(service_name)
        if not service:
            return
        
        async with self._lock:
            service["failure_count"] += 1
            service["last_failure"] = datetime.now()
            
            # Если много сбоев, помечаем как нездоровый
            if service["failure_count"] >= 3:
                service["status"] = "unhealthy"
                self.unhealthy_services.add(service_name)
                self.healthy_services.discard(service_name)
    
    async def mark_service_success(self, service_name: str):
        """Отметить успешный вызов сервиса"""
        service = self.services.get(service_name)
        if not service:
            return
        
        async with self._lock:
            service["last_success"] = datetime.now()
            
            # Если сервис был нездоровым, проверим его статус
            if service["status"] != "healthy":
                # Запланируем быструю проверку здоровья
                asyncio.create_task(self.check_service_health(service_name))
    
    async def cleanup(self):
        """Очистка ресурсов"""
        logger.info("Cleaning up service registry...")
        # Очищаем состояние
        self.healthy_services.clear()
        self.unhealthy_services.clear()

# Глобальный экземпляр реестра
_service_registry: Optional[ServiceRegistry] = None

def get_service_registry() -> ServiceRegistry:
    """Получение глобального экземпляра реестра сервисов"""
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry()
    return _service_registry