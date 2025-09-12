# -*- coding: utf-8 -*-
"""
Logging Middleware for API Gateway
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
import logging
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования всех запросов"""
    
    def __init__(self, app):
        super().__init__(app)
        
        # Пути, которые не нужно логировать подробно
        self.skip_detailed_logging = {
            "/health",
            "/health/ready", 
            "/health/live",
            "/metrics"
        }
    
    async def dispatch(self, request: Request, call_next):
        """Основная логика middleware"""
        
        start_time = time.time()
        
        # Получаем информацию о запросе
        client_ip = self.get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Начальное логирование
        if request.url.path not in self.skip_detailed_logging:
            logger.info(
                f"Request started: {request.method} {request.url.path} "
                f"from {client_ip} (ID: {request_id})"
            )
        
        # Выполняем запрос
        try:
            response = await call_next(request)
            
            # Вычисляем время обработки
            process_time = time.time() - start_time
            
            # Получаем информацию о пользователе
            user_info = getattr(request.state, "user", {})
            user_id = user_info.get("user_id") if user_info else None
            
            # Формируем лог-запись
            log_data = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params) if request.query_params else None,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "user_id": user_id,
                "status_code": response.status_code,
                "process_time": round(process_time, 4),
                "response_size": response.headers.get("content-length"),
                "service": response.headers.get("X-Service"),
                "authenticated": getattr(request.state, "authenticated", False)
            }
            
            # Определяем уровень логирования
            if request.url.path in self.skip_detailed_logging:
                if response.status_code >= 400:
                    logger.warning(f"Health check failed: {response.status_code}")
            elif response.status_code >= 500:
                logger.error(f"Server error: {self.format_log_message(log_data)}")
            elif response.status_code >= 400:
                logger.warning(f"Client error: {self.format_log_message(log_data)}")
            elif process_time > 5.0:  # Медленные запросы
                logger.warning(f"Slow request: {self.format_log_message(log_data)}")
            else:
                logger.info(f"Request completed: {self.format_log_message(log_data)}")
            
            return response
            
        except Exception as e:
            # Логируем исключения
            process_time = time.time() - start_time
            
            error_data = {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_ip,
                "error": str(e),
                "error_type": type(e).__name__,
                "process_time": round(process_time, 4)
            }
            
            logger.error(f"Request failed: {self.format_log_message(error_data)}")
            raise
    
    def get_client_ip(self, request: Request) -> str:
        """Получение IP адреса клиента"""
        # Проверяем заголовки прокси
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Возвращаем IP из соединения
        if hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"
    
    def format_log_message(self, data: Dict[str, Any]) -> str:
        """Форматирование лог-сообщения"""
        # Основная информация
        method = data.get("method", "?")
        path = data.get("path", "?")
        status = data.get("status_code", "?")
        time_ms = data.get("process_time", 0) * 1000
        
        message_parts = [f"{method} {path}"]
        
        if "status_code" in data:
            message_parts.append(f"status={status}")
        
        if "process_time" in data:
            message_parts.append(f"time={time_ms:.1f}ms")
        
        if data.get("client_ip"):
            message_parts.append(f"ip={data['client_ip']}")
        
        if data.get("user_id"):
            message_parts.append(f"user={data['user_id']}")
        
        if data.get("service"):
            message_parts.append(f"service={data['service']}")
        
        if data.get("request_id"):
            message_parts.append(f"req_id={data['request_id']}")
        
        if data.get("error"):
            message_parts.append(f"error={data['error']}")
        
        return " | ".join(message_parts)
    
    def should_log_body(self, request: Request) -> bool:
        """Определяет, нужно ли логировать тело запроса"""
        # Не логируем тела для определенных путей
        sensitive_paths = ["/auth/login", "/auth/refresh"]
        return request.url.path not in sensitive_paths
    
    async def log_request_body(self, request: Request) -> str:
        """Безопасное логирование тела запроса"""
        if not self.should_log_body(request):
            return "[SENSITIVE_DATA]"
        
        try:
            body = await request.body()
            if not body:
                return ""
            
            # Ограничиваем размер
            if len(body) > 1000:
                return f"[LARGE_BODY_{len(body)}_bytes]"
            
            # Пытаемся декодировать как JSON
            try:
                decoded = body.decode("utf-8")
                json.loads(decoded)  # Проверяем валидность JSON
                return decoded
            except (UnicodeDecodeError, json.JSONDecodeError):
                return f"[BINARY_BODY_{len(body)}_bytes]"
                
        except Exception as e:
            return f"[ERROR_READING_BODY: {str(e)}]"