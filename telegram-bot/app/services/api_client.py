# -*- coding: utf-8 -*-
"""
Telegram Bot - Base API Client
Базовый HTTP клиент для взаимодействия с микросервисами
"""
import os
import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class ApiClientError(Exception):
    """Базовое исключение для API клиента"""
    pass

class ServiceUnavailableError(ApiClientError):
    """Исключение когда сервис недоступен"""
    pass

class AuthenticationError(ApiClientError):
    """Исключение аутентификации"""
    pass

class ValidationError(ApiClientError):
    """Исключение валидации данных"""
    pass

class APIClient:
    """Базовый класс для HTTP клиентов микросервисов"""
    
    def __init__(
        self, 
        base_url: str,
        service_name: str = "unknown",
        timeout: int = 10,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.base_url = base_url.rstrip('/')
        self.service_name = service_name
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Токен для межсервисного взаимодействия
        self.api_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
    
    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        await self.start_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        await self.close_session()
    
    async def start_session(self):
        """Создание HTTP сессии"""
        if not self.session or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=20,
                keepalive_timeout=30
            )
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers={
                    'User-Agent': f'RepitBot-TelegramService/1.0',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            )
    
    async def close_session(self):
        """Закрытие HTTP сессии"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Получение заголовков для запроса"""
        headers = {}
        
        if self.api_token:
            headers['Authorization'] = f'Bearer {self.api_token}'
        
        if additional_headers:
            headers.update(additional_headers)
        
        return headers
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """Выполнение HTTP запроса с повторными попытками"""
        
        if not self.session:
            await self.start_session()
        
        url = f"{self.base_url}{endpoint}"
        request_headers = self._get_headers(headers)
        
        try:
            logger.debug(f"Making {method} request to {url}")
            
            kwargs = {
                'headers': request_headers,
                'params': params
            }
            
            if data is not None:
                kwargs['json'] = data
            
            async with self.session.request(method, url, **kwargs) as response:
                response_text = await response.text()
                
                # Логируем ответ
                logger.debug(
                    f"{method} {url} -> {response.status} "
                    f"({len(response_text)} bytes)"
                )
                
                # Обрабатываем различные статусы ответа
                if response.status == 200 or response.status == 201:
                    if response_text:
                        return await response.json()
                    return {}
                
                elif response.status == 204:
                    return {}
                
                elif response.status == 401:
                    logger.warning(f"Authentication failed for {self.service_name}")
                    raise AuthenticationError(f"Authentication failed: {response_text}")
                
                elif response.status == 403:
                    logger.warning(f"Access forbidden for {self.service_name}")
                    raise AuthenticationError(f"Access forbidden: {response_text}")
                
                elif response.status == 422:
                    logger.warning(f"Validation error for {self.service_name}: {response_text}")
                    raise ValidationError(f"Validation error: {response_text}")
                
                elif response.status >= 500:
                    logger.error(f"Server error in {self.service_name}: {response.status} {response_text}")
                    raise ServiceUnavailableError(f"Server error: {response.status}")
                
                else:
                    logger.error(f"Unexpected response from {self.service_name}: {response.status} {response_text}")
                    raise ApiClientError(f"Unexpected response: {response.status} {response_text}")
        
        except aiohttp.ClientError as e:
            logger.error(f"Network error with {self.service_name}: {e}")
            
            # Повторные попытки при сетевых ошибках
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (2 ** retry_count)  # Exponential backoff
                logger.info(f"Retrying {self.service_name} request in {wait_time}s (attempt {retry_count + 1}/{self.max_retries})")
                await asyncio.sleep(wait_time)
                return await self._make_request(method, endpoint, data, params, headers, retry_count + 1)
            
            raise ServiceUnavailableError(f"Service {self.service_name} unavailable: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error with {self.service_name}: {e}")
            raise ApiClientError(f"Unexpected error: {e}")
    
    async def get(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """GET запрос"""
        return await self._make_request('GET', endpoint, params=params, headers=headers)
    
    async def post(
        self, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """POST запрос"""
        return await self._make_request('POST', endpoint, data=data, params=params, headers=headers)
    
    async def put(
        self, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """PUT запрос"""
        return await self._make_request('PUT', endpoint, data=data, headers=headers)
    
    async def delete(
        self, 
        endpoint: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """DELETE запрос"""
        return await self._make_request('DELETE', endpoint, headers=headers)
    
    # Convenience methods for common patterns
    async def _get(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Internal GET method with error handling"""
        try:
            return await self.get(endpoint, **kwargs)
        except Exception as e:
            logger.error(f"GET {endpoint} failed: {e}")
            return None
    
    async def _post(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Internal POST method with error handling"""
        try:
            return await self.post(endpoint, **kwargs)
        except Exception as e:
            logger.error(f"POST {endpoint} failed: {e}")
            return None
    
    async def _put(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Internal PUT method with error handling"""
        try:
            return await self.put(endpoint, **kwargs)
        except Exception as e:
            logger.error(f"PUT {endpoint} failed: {e}")
            return None
    
    async def _delete(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Internal DELETE method with error handling"""
        try:
            return await self.delete(endpoint, **kwargs)
        except Exception as e:
            logger.error(f"DELETE {endpoint} failed: {e}")
            return None
    
    async def _get_bytes(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[bytes]:
        """Get binary data (for file downloads)"""
        if not self.session:
            await self.start_session()
        
        url = f"{self.base_url}{endpoint}"
        request_headers = self._get_headers()
        
        try:
            async with self.session.get(url, headers=request_headers, params=params) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"File download failed: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"File download error: {e}")
            return None
    
    async def _post_files(
        self, 
        endpoint: str, 
        files: Dict[str, Any],
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """POST request with file upload"""
        if not self.session:
            await self.start_session()
        
        url = f"{self.base_url}{endpoint}"
        request_headers = self._get_headers()
        
        # Remove Content-Type for file uploads (let aiohttp set it)
        if 'Content-Type' in request_headers:
            del request_headers['Content-Type']
        
        try:
            form_data = aiohttp.FormData()
            
            # Add files
            for field_name, file_data in files.items():
                if isinstance(file_data, tuple):
                    filename, content = file_data
                    form_data.add_field(field_name, content, filename=filename)
                else:
                    form_data.add_field(field_name, file_data)
            
            # Add other data
            if data:
                for key, value in data.items():
                    form_data.add_field(key, str(value))
            
            async with self.session.post(url, headers=request_headers, data=form_data) as response:
                if response.status in [200, 201]:
                    return await response.json()
                else:
                    response_text = await response.text()
                    logger.error(f"File upload failed: {response.status} {response_text}")
                    return None
        except Exception as e:
            logger.error(f"File upload error: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Проверка здоровья сервиса"""
        try:
            response = await self.get('/health')
            return response.get('status') == 'healthy'
        except Exception as e:
            logger.warning(f"Health check failed for {self.service_name}: {e}")
            return False
    
    def set_auth_token(self, token: str, expires_at: Optional[datetime] = None):
        """Установка токена аутентификации"""
        self.api_token = token
        self.token_expires_at = expires_at
        logger.debug(f"Auth token set for {self.service_name}")
    
    def clear_auth_token(self):
        """Очистка токена аутентификации"""
        self.api_token = None
        self.token_expires_at = None
        logger.debug(f"Auth token cleared for {self.service_name}")
    
    def is_token_expired(self) -> bool:
        """Проверка истечения токена"""
        if not self.token_expires_at:
            return False
        return datetime.utcnow() >= self.token_expires_at

class ServiceRegistry:
    """Реестр микросервисов"""
    
    def __init__(self):
        self.services = {}
        self.health_status = {}
        
        # Конфигурация сервисов из переменных окружения
        self.services = {
            'user': {
                'url': os.getenv('USER_SERVICE_URL', 'http://localhost:8001'),
                'timeout': int(os.getenv('USER_SERVICE_TIMEOUT', '10')),
                'retries': int(os.getenv('USER_SERVICE_RETRIES', '3'))
            },
            'lesson': {
                'url': os.getenv('LESSON_SERVICE_URL', 'http://localhost:8002'),
                'timeout': int(os.getenv('LESSON_SERVICE_TIMEOUT', '10')),
                'retries': int(os.getenv('LESSON_SERVICE_RETRIES', '3'))
            },
            'payment': {
                'url': os.getenv('PAYMENT_SERVICE_URL', 'http://localhost:8003'),
                'timeout': int(os.getenv('PAYMENT_SERVICE_TIMEOUT', '10')),
                'retries': int(os.getenv('PAYMENT_SERVICE_RETRIES', '3'))
            },
            'material': {
                'url': os.getenv('MATERIAL_SERVICE_URL', 'http://localhost:8004'),
                'timeout': int(os.getenv('MATERIAL_SERVICE_TIMEOUT', '10')),
                'retries': int(os.getenv('MATERIAL_SERVICE_RETRIES', '3'))
            },
            'homework': {
                'url': os.getenv('HOMEWORK_SERVICE_URL', 'http://localhost:8005'),
                'timeout': int(os.getenv('HOMEWORK_SERVICE_TIMEOUT', '10')),
                'retries': int(os.getenv('HOMEWORK_SERVICE_RETRIES', '3'))
            }
        }
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Получение конфигурации сервиса"""
        return self.services.get(service_name, {})
    
    def is_service_healthy(self, service_name: str) -> bool:
        """Проверка здоровья сервиса"""
        return self.health_status.get(service_name, False)
    
    def update_service_health(self, service_name: str, is_healthy: bool):
        """Обновление статуса здоровья сервиса"""
        self.health_status[service_name] = is_healthy
        logger.info(f"Service {service_name} health status: {'healthy' if is_healthy else 'unhealthy'}")

# Глобальный реестр сервисов
service_registry = ServiceRegistry()

# Функции-утилиты для fallback режима
def with_fallback(fallback_func):
    """Декоратор для добавления fallback функциональности"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except (ServiceUnavailableError, ApiClientError) as e:
                logger.warning(f"Microservice call failed, using fallback: {e}")
                return await fallback_func(*args, **kwargs)
        return wrapper
    return decorator

async def check_all_services_health() -> Dict[str, bool]:
    """Проверка здоровья всех сервисов"""
    results = {}
    
    for service_name, config in service_registry.services.items():
        try:
            client = APIClient(
                base_url=config['url'],
                service_name=service_name,
                timeout=5  # Быстрая проверка
            )
            
            async with client:
                is_healthy = await client.health_check()
                results[service_name] = is_healthy
                service_registry.update_service_health(service_name, is_healthy)
        
        except Exception as e:
            logger.error(f"Failed to check health of {service_name}: {e}")
            results[service_name] = False
            service_registry.update_service_health(service_name, False)
    
    return results