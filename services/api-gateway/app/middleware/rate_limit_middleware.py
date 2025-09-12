# -*- coding: utf-8 -*-
"""
Rate Limiting Middleware for API Gateway
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import time
import asyncio
from collections import defaultdict, deque
from typing import Dict, Deque
import logging

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware с использованием sliding window алгоритма"""
    
    def __init__(self, app, requests_per_minute: int = 60, burst_size: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.window_size = 60  # 1 минута в секундах
        
        # Хранилище для отслеживания запросов по IP
        self.request_history: Dict[str, Deque[float]] = defaultdict(lambda: deque())
        self._lock = asyncio.Lock()
        
        # Исключения из rate limiting
        self.exempt_paths = {
            "/health",
            "/health/ready", 
            "/health/live",
            "/gateway/info"
        }
    
    async def dispatch(self, request: Request, call_next):
        """Основная логика middleware"""
        
        # Проверяем исключения
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Получаем IP клиента
        client_ip = self.get_client_ip(request)
        
        # Проверяем rate limit
        if await self.is_rate_limited(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {self.requests_per_minute} requests per minute",
                    "retry_after": 60,
                    "client_ip": client_ip
                },
                headers={
                    "Retry-After": "60",
                    "X-Rate-Limit-Limit": str(self.requests_per_minute),
                    "X-Rate-Limit-Remaining": "0",
                    "X-Rate-Limit-Reset": str(int(time.time() + 60))
                }
            )
        
        # Записываем запрос
        await self.record_request(client_ip)
        
        # Добавляем заголовки rate limit в ответ
        response = await call_next(request)
        
        remaining_requests = await self.get_remaining_requests(client_ip)
        response.headers["X-Rate-Limit-Limit"] = str(self.requests_per_minute)
        response.headers["X-Rate-Limit-Remaining"] = str(remaining_requests)
        response.headers["X-Rate-Limit-Reset"] = str(int(time.time() + 60))
        
        return response
    
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
    
    async def is_rate_limited(self, client_ip: str) -> bool:
        """Проверка, превышен ли rate limit"""
        async with self._lock:
            current_time = time.time()
            requests = self.request_history[client_ip]
            
            # Удаляем старые запросы (вне окна)
            while requests and current_time - requests[0] > self.window_size:
                requests.popleft()
            
            # Проверяем количество запросов
            return len(requests) >= self.requests_per_minute
    
    async def record_request(self, client_ip: str):
        """Записать новый запрос"""
        async with self._lock:
            current_time = time.time()
            self.request_history[client_ip].append(current_time)
            
            # Ограничиваем размер истории
            requests = self.request_history[client_ip]
            if len(requests) > self.requests_per_minute * 2:  # Буфер
                # Удаляем старые запросы
                while requests and current_time - requests[0] > self.window_size:
                    requests.popleft()
    
    async def get_remaining_requests(self, client_ip: str) -> int:
        """Получить количество оставшихся запросов"""
        async with self._lock:
            current_time = time.time()
            requests = self.request_history[client_ip]
            
            # Удаляем старые запросы
            while requests and current_time - requests[0] > self.window_size:
                requests.popleft()
            
            return max(0, self.requests_per_minute - len(requests))
    
    async def cleanup_old_entries(self):
        """Периодическая очистка старых записей"""
        while True:
            try:
                await asyncio.sleep(300)  # Каждые 5 минут
                
                async with self._lock:
                    current_time = time.time()
                    
                    # Удаляем пустые и старые записи
                    to_remove = []
                    for client_ip, requests in self.request_history.items():
                        # Удаляем старые запросы
                        while requests and current_time - requests[0] > self.window_size * 2:
                            requests.popleft()
                        
                        # Помечаем пустые записи для удаления
                        if not requests:
                            to_remove.append(client_ip)
                    
                    for client_ip in to_remove:
                        del self.request_history[client_ip]
                    
                    if to_remove:
                        logger.debug(f"Cleaned up {len(to_remove)} old rate limit entries")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in rate limit cleanup: {e}")