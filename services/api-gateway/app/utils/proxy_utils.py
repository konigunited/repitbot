# -*- coding: utf-8 -*-
"""
Proxy Utilities for API Gateway
"""
import httpx
import json
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

class ProxyUtils:
    """Утилиты для проксирования запросов"""
    
    def __init__(self):
        self.default_timeout = 30.0
        self.max_retries = 3
        self.retry_delay = 1.0
    
    def prepare_headers(
        self, 
        original_headers: Dict[str, str], 
        user_data: Optional[Dict[str, Any]] = None,
        additional_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Подготовка заголовков для проксирования"""
        
        # Заголовки, которые нужно передать
        forwarded_headers = {}
        
        # Основные заголовки
        headers_to_forward = [
            "content-type",
            "accept",
            "accept-language", 
            "accept-encoding",
            "user-agent",
            "authorization"
        ]
        
        for header in headers_to_forward:
            if header in original_headers:
                forwarded_headers[header] = original_headers[header]
        
        # Заголовки прокси
        forwarded_headers.update({
            "X-Forwarded-For": original_headers.get("x-forwarded-for", "unknown"),
            "X-Forwarded-Proto": original_headers.get("x-forwarded-proto", "http"),
            "X-Forwarded-Host": original_headers.get("host", "unknown"),
            "X-Gateway": "RepitBot-API-Gateway",
            "X-Gateway-Version": "1.0.0"
        })
        
        # Информация о пользователе
        if user_data:
            forwarded_headers.update({
                "X-User-ID": str(user_data.get("user_id", "")),
                "X-User-Role": user_data.get("role", ""),
                "X-User-Email": user_data.get("email", ""),
                "X-User-Authenticated": "true"
            })
        else:
            forwarded_headers["X-User-Authenticated"] = "false"
        
        # Дополнительные заголовки
        if additional_headers:
            forwarded_headers.update(additional_headers)
        
        return forwarded_headers
    
    def prepare_url(self, service_url: str, path: str, query_params: str = "") -> str:
        """Подготовка URL для запроса к сервису"""
        
        # Убираем слеш в конце service_url если есть
        service_url = service_url.rstrip("/")
        
        # Формируем полный URL
        if path.startswith("/"):
            full_url = service_url + path
        else:
            full_url = f"{service_url}/{path}"
        
        # Добавляем query параметры
        if query_params:
            separator = "&" if "?" in full_url else "?"
            full_url = f"{full_url}{separator}{query_params}"
        
        return full_url
    
    def filter_response_headers(self, headers: httpx.Headers) -> Dict[str, str]:
        """Фильтрация заголовков ответа"""
        
        # Заголовки, которые НЕ нужно передавать клиенту
        headers_to_exclude = {
            "content-length",
            "content-encoding", 
            "transfer-encoding",
            "connection",
            "server",
            "date"  # Будет установлен автоматически
        }
        
        # Формируем финальные заголовки
        response_headers = {}
        
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower not in headers_to_exclude:
                response_headers[key] = value
        
        # Добавляем заголовки Gateway
        response_headers.update({
            "X-Gateway": "RepitBot-API-Gateway",
            "X-Proxy-Cache": "MISS"  # Пока что кеширования нет
        })
        
        return response_headers
    
    def is_json_content(self, headers: httpx.Headers) -> bool:
        """Проверка, является ли контент JSON"""
        content_type = headers.get("content-type", "")
        return content_type.startswith("application/json")
    
    def transform_request_body(self, body: bytes, headers: Dict[str, str]) -> bytes:
        """Преобразование тела запроса при необходимости"""
        
        # Пока что просто возвращаем как есть
        # В будущем здесь можно добавить логику трансформации
        return body
    
    def transform_response_body(self, body: bytes, headers: httpx.Headers) -> bytes:
        """Преобразование тела ответа при необходимости"""
        
        # Если это JSON, можно добавить метаинформацию
        if self.is_json_content(headers):
            try:
                data = json.loads(body)
                
                # Добавляем информацию о Gateway (только для отладки)
                if isinstance(data, dict) and "__gateway_debug__" in data:
                    data["__gateway_info__"] = {
                        "proxied_by": "RepitBot-API-Gateway",
                        "version": "1.0.0"
                    }
                
                return json.dumps(data, ensure_ascii=False).encode("utf-8")
                
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Если не удалось декодировать, возвращаем как есть
                pass
        
        return body
    
    def get_retry_delay(self, attempt: int) -> float:
        """Вычисление задержки для повторных попыток (exponential backoff)"""
        return min(self.retry_delay * (2 ** attempt), 10.0)  # Максимум 10 секунд
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Определение, нужно ли повторить запрос"""
        
        if attempt >= self.max_retries:
            return False
        
        # Повторяем только для определенных типов ошибок
        retryable_exceptions = (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.ReadError
        )
        
        return isinstance(exception, retryable_exceptions)
    
    def extract_service_from_path(self, path: str) -> Optional[str]:
        """Извлечение имени сервиса из пути"""
        
        # Ожидаем пути вида: /api/v1/SERVICE_NAME/...
        path_parts = path.strip("/").split("/")
        
        if len(path_parts) >= 3 and path_parts[0] == "api" and path_parts[1] == "v1":
            service_part = path_parts[2]
            
            # Маппинг путей к сервисам
            service_mapping = {
                "users": "user-service",
                "auth": "user-service",
                "lessons": "lesson-service", 
                "schedule": "lesson-service",
                "homework": "homework-service",
                "assignments": "homework-service",
                "payments": "payment-service",
                "billing": "payment-service",
                "balance": "payment-service",
                "materials": "material-service",
                "library": "material-service", 
                "files": "material-service",
                "notifications": "notification-service",
                "messages": "notification-service",
                "analytics": "analytics-service",
                "reports": "analytics-service",
                "charts": "analytics-service",
                "students": "student-service",
                "achievements": "student-service",
                "gamification": "student-service",
                "progress": "student-service"
            }
            
            return service_mapping.get(service_part)
        
        return None
    
    def validate_service_response(self, response: httpx.Response, service_name: str) -> bool:
        """Валидация ответа от сервиса"""
        
        # Базовая валидация
        if not (200 <= response.status_code < 600):
            logger.warning(f"Invalid status code from {service_name}: {response.status_code}")
            return False
        
        # Проверяем заголовки
        if not response.headers.get("content-type"):
            logger.warning(f"Missing content-type header from {service_name}")
            # Не критично, продолжаем
        
        # Проверяем размер ответа
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > 100 * 1024 * 1024:  # 100MB
            logger.warning(f"Large response from {service_name}: {content_length} bytes")
            # Не блокируем, но логируем
        
        return True
    
    def create_error_response(self, error_type: str, message: str, status_code: int = 500) -> Dict[str, Any]:
        """Создание стандартного ответа об ошибке"""
        
        return {
            "error": error_type,
            "message": message,
            "gateway": "RepitBot-API-Gateway",
            "timestamp": httpx._utils.utcnow().isoformat(),
            "status_code": status_code
        }