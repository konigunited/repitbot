# -*- coding: utf-8 -*-
"""
HTTP Client for Microservices Integration
Клиент для взаимодействия с микросервисами через API Gateway
"""
import httpx
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
import json

logger = logging.getLogger(__name__)

class MicroserviceClient:
    """Клиент для взаимодействия с микросервисами"""
    
    def __init__(self):
        # URL сервисов из переменных окружения
        self.api_gateway_url = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000")
        self.user_service_url = os.getenv("USER_SERVICE_URL", "http://user-service:8001")
        self.lesson_service_url = os.getenv("LESSON_SERVICE_URL", "http://lesson-service:8002")
        self.homework_service_url = os.getenv("HOMEWORK_SERVICE_URL", "http://homework-service:8003")
        self.payment_service_url = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8004")
        self.material_service_url = os.getenv("MATERIAL_SERVICE_URL", "http://material-service:8005")
        self.notification_service_url = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8006")
        self.analytics_service_url = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:8007")
        self.student_service_url = os.getenv("STUDENT_SERVICE_URL", "http://student-service:8008")
        
        # Настройки
        self.timeout = 30.0
        self.max_retries = 3
        self.enable_circuit_breaker = True
        self.use_api_gateway = os.getenv("USE_API_GATEWAY", "true").lower() == "true"
        
        # Хранилище для токенов
        self._auth_tokens: Dict[str, str] = {}
        
        # HTTP клиент
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={
                "User-Agent": "RepitBot-TelegramBot/1.0",
                "Content-Type": "application/json"
            }
        )
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def close(self):
        """Закрытие HTTP клиента"""
        await self.client.aclose()
    
    def get_service_url(self, service: str, endpoint: str = "") -> str:
        """Получение URL сервиса"""
        if self.use_api_gateway:
            return f"{self.api_gateway_url}/api/v1{endpoint}"
        
        # Прямое обращение к сервисам
        service_urls = {
            "user": self.user_service_url,
            "lesson": self.lesson_service_url,
            "homework": self.homework_service_url,
            "payment": self.payment_service_url,
            "material": self.material_service_url,
            "notification": self.notification_service_url,
            "analytics": self.analytics_service_url,
            "student": self.student_service_url
        }
        
        base_url = service_urls.get(service)
        if not base_url:
            raise ValueError(f"Unknown service: {service}")
        
        return f"{base_url}/api/v1{endpoint}"
    
    def get_auth_headers(self, user_id: Optional[int] = None) -> Dict[str, str]:
        """Получение заголовков авторизации"""
        headers = {}
        
        if user_id and str(user_id) in self._auth_tokens:
            headers["Authorization"] = f"Bearer {self._auth_tokens[str(user_id)]}"
        
        # Добавляем системные заголовки
        headers.update({
            "X-Client": "telegram-bot",
            "X-Client-Version": "1.0.0",
            "X-Request-Time": datetime.now().isoformat()
        })
        
        return headers
    
    async def request(
        self,
        method: str,
        service: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Базовый метод для HTTP запросов"""
        
        url = self.get_service_url(service, endpoint)
        headers = self.get_auth_headers(user_id)
        
        request_timeout = timeout or self.timeout
        
        logger.debug(f"Making {method} request to {url}")
        
        for attempt in range(self.max_retries):
            try:
                if method.upper() == "GET":
                    response = await self.client.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=request_timeout
                    )
                else:
                    response = await self.client.request(
                        method,
                        url,
                        json=data,
                        params=params,
                        headers=headers,
                        timeout=request_timeout
                    )
                
                # Проверяем статус ответа
                if response.status_code < 400:
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        return {"status": "success", "data": response.text}
                
                # Обрабатываем ошибки
                logger.warning(f"Request failed with status {response.status_code}: {response.text}")
                
                if response.status_code < 500:
                    # Клиентская ошибка - не повторяем
                    try:
                        error_data = response.json()
                    except json.JSONDecodeError:
                        error_data = {"error": response.text}
                    
                    raise HTTPException(response.status_code, error_data)
                
                # Серверная ошибка - можем повторить
                if attempt == self.max_retries - 1:
                    raise HTTPException(response.status_code, {"error": "Service unavailable"})
                
                # Ждем перед повторной попыткой
                await asyncio.sleep(2 ** attempt)
                
            except httpx.TimeoutException:
                logger.warning(f"Request timeout for {url} (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    raise ServiceUnavailableException(f"Service {service} timeout")
                await asyncio.sleep(2 ** attempt)
                
            except httpx.ConnectError:
                logger.error(f"Connection error for {url} (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    raise ServiceUnavailableException(f"Service {service} unavailable")
                await asyncio.sleep(2 ** attempt)
        
        raise ServiceUnavailableException(f"Service {service} failed after {self.max_retries} attempts")
    
    async def get(self, service: str, endpoint: str, params: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        """GET запрос"""
        return await self.request("GET", service, endpoint, params=params, user_id=user_id)
    
    async def post(self, service: str, endpoint: str, data: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        """POST запрос"""
        return await self.request("POST", service, endpoint, data=data, user_id=user_id)
    
    async def put(self, service: str, endpoint: str, data: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        """PUT запрос"""
        return await self.request("PUT", service, endpoint, data=data, user_id=user_id)
    
    async def delete(self, service: str, endpoint: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """DELETE запрос"""
        return await self.request("DELETE", service, endpoint, user_id=user_id)
    
    # ============== USER SERVICE ==============
    
    async def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение профиля пользователя"""
        try:
            response = await self.get("user", f"/users/{user_id}", user_id=user_id)
            return response
        except HTTPException as e:
            if e.status_code == 404:
                return None
            raise
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание пользователя"""
        return await self.post("user", "/users", data=user_data)
    
    async def update_user(self, user_id: int, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновление пользователя"""
        return await self.put("user", f"/users/{user_id}", data=user_data, user_id=user_id)
    
    # ============== LESSON SERVICE ==============
    
    async def get_user_lessons(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение уроков пользователя"""
        try:
            response = await self.get("lesson", "/lessons", params={"user_id": user_id}, user_id=user_id)
            return response.get("lessons", [])
        except HTTPException:
            return []
    
    async def create_lesson(self, lesson_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание урока"""
        return await self.post("lesson", "/lessons", data=lesson_data)
    
    async def update_lesson_status(self, lesson_id: int, status: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Обновление статуса урока"""
        return await self.put("lesson", f"/lessons/{lesson_id}/status", data={"status": status}, user_id=user_id)
    
    # ============== HOMEWORK SERVICE ==============
    
    async def get_user_homework(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение домашних заданий пользователя"""
        try:
            response = await self.get("homework", "/homework", params={"student_id": user_id}, user_id=user_id)
            return response.get("homework", [])
        except HTTPException:
            return []
    
    async def submit_homework(self, homework_data: Dict[str, Any]) -> Dict[str, Any]:
        """Отправка домашнего задания"""
        return await self.post("homework", "/homework/submit", data=homework_data)
    
    # ============== PAYMENT SERVICE ==============
    
    async def get_user_balance(self, user_id: int) -> Dict[str, Any]:
        """Получение баланса пользователя"""
        try:
            response = await self.get("payment", f"/balance/{user_id}", user_id=user_id)
            return response
        except HTTPException:
            return {"balance": 0, "currency": "RUB"}
    
    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание платежа"""
        return await self.post("payment", "/payments", data=payment_data)
    
    # ============== STUDENT SERVICE ==============
    
    async def get_student_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение профиля студента"""
        try:
            response = await self.get("student", f"/students/by-user/{user_id}", user_id=user_id)
            return response
        except HTTPException as e:
            if e.status_code == 404:
                return None
            raise
    
    async def create_student(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание профиля студента"""
        return await self.post("student", "/students", data=student_data)
    
    async def get_student_achievements(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение достижений студента"""
        try:
            student = await self.get_student_profile(user_id)
            if not student:
                return []
            
            response = await self.get("student", f"/achievements", params={"student_id": student["id"]}, user_id=user_id)
            return response.get("achievements", [])
        except HTTPException:
            return []
    
    async def add_student_xp(self, user_id: int, xp_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Добавление опыта студенту"""
        try:
            student = await self.get_student_profile(user_id)
            if not student:
                return None
            
            response = await self.post("student", f"/students/{student['id']}/experience", data=xp_data, user_id=user_id)
            return response
        except HTTPException:
            return None
    
    # ============== NOTIFICATION SERVICE ==============
    
    async def send_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Отправка уведомления"""
        return await self.post("notification", "/notifications/send", data=notification_data)
    
    # ============== ANALYTICS SERVICE ==============
    
    async def get_user_analytics(self, user_id: int) -> Dict[str, Any]:
        """Получение аналитики пользователя"""
        try:
            response = await self.get("analytics", f"/analytics/user/{user_id}", user_id=user_id)
            return response
        except HTTPException:
            return {}
    
    # ============== UTILITY METHODS ==============
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья микросервисов"""
        if self.use_api_gateway:
            try:
                response = await self.get("", "/health")
                return response
            except Exception as e:
                return {"status": "unhealthy", "error": str(e)}
        else:
            # Проверяем каждый сервис отдельно
            results = {}
            services = ["user", "lesson", "homework", "payment", "material", "notification", "analytics", "student"]
            
            for service in services:
                try:
                    url = self.get_service_url(service, "/health")
                    response = await self.client.get(url, timeout=5.0)
                    results[service] = "healthy" if response.status_code == 200 else "unhealthy"
                except Exception:
                    results[service] = "unhealthy"
            
            return {"services": results}
    
    def set_auth_token(self, user_id: int, token: str):
        """Установка токена авторизации для пользователя"""
        self._auth_tokens[str(user_id)] = token
    
    def clear_auth_token(self, user_id: int):
        """Очистка токена авторизации"""
        self._auth_tokens.pop(str(user_id), None)


# Исключения
class HTTPException(Exception):
    """HTTP исключение"""
    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class ServiceUnavailableException(Exception):
    """Исключение недоступности сервиса"""
    pass


# Глобальный клиент
_microservice_client: Optional[MicroserviceClient] = None

def get_microservice_client() -> MicroserviceClient:
    """Получение глобального экземпляра клиента микросервисов"""
    global _microservice_client
    if _microservice_client is None:
        _microservice_client = MicroserviceClient()
    return _microservice_client

async def close_microservice_client():
    """Закрытие глобального клиента"""
    global _microservice_client
    if _microservice_client:
        await _microservice_client.close()
        _microservice_client = None