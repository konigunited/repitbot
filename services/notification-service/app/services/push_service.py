import asyncio
import logging
from typing import Optional, Dict, Any, List
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class PushService:
    """Сервис для отправки push уведомлений через FCM"""
    
    def __init__(self):
        self.fcm_server_key = settings.FCM_SERVER_KEY
        self.fcm_project_id = settings.FCM_PROJECT_ID
        self.fcm_url = "https://fcm.googleapis.com/fcm/send"
        self.timeout = 30
        
        if not self.fcm_server_key:
            logger.warning("FCM_SERVER_KEY not configured")
    
    async def send_push_notification(
        self,
        device_tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image_url: Optional[str] = None,
        click_action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Отправить push уведомление
        
        Args:
            device_tokens: Список токенов устройств
            title: Заголовок уведомления
            body: Текст уведомления
            data: Дополнительные данные
            image_url: URL изображения
            click_action: Действие при клике
        
        Returns:
            Результат отправки
        """
        if not self.fcm_server_key:
            raise Exception("FCM server key not configured")
        
        if not device_tokens:
            raise Exception("Device tokens required")
        
        # Подготавливаем payload
        notification = {
            "title": title,
            "body": body
        }
        
        if image_url:
            notification["image"] = image_url
        
        if click_action:
            notification["click_action"] = click_action
        
        payload = {
            "registration_ids": device_tokens[:1000],  # FCM limit
            "notification": notification,
            "priority": "high"
        }
        
        if data:
            payload["data"] = data
        
        headers = {
            "Authorization": f"key={self.fcm_server_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.fcm_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Push notification sent to {len(device_tokens)} devices")
                return {
                    "success": True,
                    "multicast_id": result.get("multicast_id"),
                    "success_count": result.get("success", 0),
                    "failure_count": result.get("failure", 0),
                    "results": result.get("results", [])
                }
                
        except httpx.TimeoutException:
            logger.error("Timeout sending push notification")
            raise Exception("FCM API timeout")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending push notification: {e}")
            raise Exception(f"FCM API HTTP error: {e}")
        except Exception as e:
            logger.error(f"Error sending push notification: {e}")
            raise
    
    async def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        condition: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Отправить уведомление по топику
        
        Args:
            topic: Имя топика
            title: Заголовок
            body: Текст
            data: Дополнительные данные
            condition: Условие для отправки
        
        Returns:
            Результат отправки
        """
        if not self.fcm_server_key:
            raise Exception("FCM server key not configured")
        
        notification = {
            "title": title,
            "body": body
        }
        
        payload = {
            "notification": notification,
            "priority": "high"
        }
        
        if condition:
            payload["condition"] = condition
        else:
            payload["to"] = f"/topics/{topic}"
        
        if data:
            payload["data"] = data
        
        headers = {
            "Authorization": f"key={self.fcm_server_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.fcm_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Push notification sent to topic {topic}")
                return {
                    "success": True,
                    "message_id": result.get("message_id"),
                    "topic": topic
                }
                
        except Exception as e:
            logger.error(f"Error sending push to topic {topic}: {e}")
            raise
    
    async def subscribe_to_topic(self, tokens: List[str], topic: str) -> Dict[str, Any]:
        """
        Подписать токены на топик
        
        Args:
            tokens: Список токенов
            topic: Имя топика
        
        Returns:
            Результат подписки
        """
        if not self.fcm_server_key:
            raise Exception("FCM server key not configured")
        
        url = f"https://iid.googleapis.com/iid/v1:batchAdd"
        
        payload = {
            "to": f"/topics/{topic}",
            "registration_tokens": tokens[:1000]  # Limit
        }
        
        headers = {
            "Authorization": f"key={self.fcm_server_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Subscribed {len(tokens)} tokens to topic {topic}")
                return result
                
        except Exception as e:
            logger.error(f"Error subscribing to topic {topic}: {e}")
            raise
    
    async def unsubscribe_from_topic(self, tokens: List[str], topic: str) -> Dict[str, Any]:
        """
        Отписать токены от топика
        
        Args:
            tokens: Список токенов
            topic: Имя топика
        
        Returns:
            Результат отписки
        """
        if not self.fcm_server_key:
            raise Exception("FCM server key not configured")
        
        url = f"https://iid.googleapis.com/iid/v1:batchRemove"
        
        payload = {
            "to": f"/topics/{topic}",
            "registration_tokens": tokens[:1000]
        }
        
        headers = {
            "Authorization": f"key={self.fcm_server_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Unsubscribed {len(tokens)} tokens from topic {topic}")
                return result
                
        except Exception as e:
            logger.error(f"Error unsubscribing from topic {topic}: {e}")
            raise
    
    async def validate_tokens(self, tokens: List[str]) -> Dict[str, Any]:
        """
        Проверить валидность токенов
        
        Args:
            tokens: Список токенов для проверки
        
        Returns:
            Результат проверки
        """
        if not self.fcm_server_key:
            raise Exception("FCM server key not configured")
        
        # Отправляем тестовое сообщение для проверки токенов
        payload = {
            "registration_ids": tokens[:1000],
            "dry_run": True,
            "data": {"test": "validation"}
        }
        
        headers = {
            "Authorization": f"key={self.fcm_server_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.fcm_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                valid_tokens = []
                invalid_tokens = []
                
                results = result.get("results", [])
                for i, token_result in enumerate(results):
                    if i < len(tokens):
                        if token_result.get("message_id"):
                            valid_tokens.append(tokens[i])
                        else:
                            invalid_tokens.append({
                                "token": tokens[i],
                                "error": token_result.get("error")
                            })
                
                return {
                    "valid_tokens": valid_tokens,
                    "invalid_tokens": invalid_tokens,
                    "total_checked": len(tokens)
                }
                
        except Exception as e:
            logger.error(f"Error validating tokens: {e}")
            raise
    
    def is_configured(self) -> bool:
        """Проверить конфигурацию push сервиса"""
        return bool(self.fcm_server_key)