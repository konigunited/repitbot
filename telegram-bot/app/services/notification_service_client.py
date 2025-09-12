"""
Notification Service Client for Telegram Bot
HTTP client for communicating with Notification Service
"""

import httpx
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class NotificationServiceClient:
    """Client for Notification Service"""
    
    def __init__(self):
        self.base_url = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8006")
        self.timeout = 30.0
        self.retries = 3
        self.retry_delay = 1.0

    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make HTTP request with retry logic"""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, params=params, headers=headers)
                    elif method.upper() == "POST":
                        response = await client.post(url, json=data, headers=headers)
                    elif method.upper() == "PUT":
                        response = await client.put(url, json=data, headers=headers)
                    elif method.upper() == "DELETE":
                        response = await client.delete(url, headers=headers)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                    
                    response.raise_for_status()
                    return response.json()
                    
            except httpx.RequestError as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.retries}): {str(e)}")
                if attempt < self.retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"All retry attempts failed for {url}")
                    return None
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} for {url}: {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error for {url}: {str(e)}")
                return None
        
        return None

    async def send_telegram_notification(
        self,
        user_id: int,
        message: str,
        notification_type: str = "info",
        template_data: Optional[Dict] = None,
        priority: str = "normal"
    ) -> bool:
        """Send Telegram notification"""
        try:
            data = {
                "user_id": user_id,
                "channel": "telegram",
                "message": message,
                "notification_type": notification_type,
                "template_data": template_data or {},
                "priority": priority,
                "metadata": {
                    "source": "telegram_bot",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            result = await self._make_request("POST", "/api/v1/notifications/send", data=data)
            return result is not None and result.get("success", False)
            
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {str(e)}")
            return False

    async def send_email_notification(
        self,
        user_id: int,
        subject: str,
        message: str,
        template_name: Optional[str] = None,
        template_data: Optional[Dict] = None
    ) -> bool:
        """Send email notification"""
        try:
            data = {
                "user_id": user_id,
                "channel": "email",
                "subject": subject,
                "message": message,
                "template_name": template_name,
                "template_data": template_data or {},
                "metadata": {
                    "source": "telegram_bot",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            result = await self._make_request("POST", "/api/v1/notifications/send", data=data)
            return result is not None and result.get("success", False)
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False

    async def send_bulk_notifications(
        self,
        user_ids: List[int],
        message: str,
        channels: List[str] = ["telegram"],
        notification_type: str = "info"
    ) -> Dict[str, Any]:
        """Send bulk notifications to multiple users"""
        try:
            data = {
                "user_ids": user_ids,
                "channels": channels,
                "message": message,
                "notification_type": notification_type,
                "metadata": {
                    "source": "telegram_bot",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            result = await self._make_request("POST", "/api/v1/notifications/bulk", data=data)
            return result or {"success": False, "sent_count": 0, "failed_count": len(user_ids)}
            
        except Exception as e:
            logger.error(f"Error sending bulk notifications: {str(e)}")
            return {"success": False, "sent_count": 0, "failed_count": len(user_ids)}

    async def get_notification_preferences(self, user_id: int) -> Optional[Dict]:
        """Get user notification preferences"""
        try:
            result = await self._make_request("GET", f"/api/v1/preferences/{user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting notification preferences: {str(e)}")
            return None

    async def update_notification_preferences(
        self,
        user_id: int,
        preferences: Dict[str, Any]
    ) -> bool:
        """Update user notification preferences"""
        try:
            result = await self._make_request(
                "PUT", 
                f"/api/v1/preferences/{user_id}", 
                data=preferences
            )
            return result is not None and result.get("success", False)
            
        except Exception as e:
            logger.error(f"Error updating notification preferences: {str(e)}")
            return False

    async def schedule_notification(
        self,
        user_id: int,
        message: str,
        send_at: datetime,
        channels: List[str] = ["telegram"],
        notification_type: str = "reminder"
    ) -> Optional[str]:
        """Schedule a notification for later delivery"""
        try:
            data = {
                "user_id": user_id,
                "channels": channels,
                "message": message,
                "notification_type": notification_type,
                "send_at": send_at.isoformat(),
                "metadata": {
                    "source": "telegram_bot",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            result = await self._make_request("POST", "/api/v1/notifications/schedule", data=data)
            return result.get("notification_id") if result else None
            
        except Exception as e:
            logger.error(f"Error scheduling notification: {str(e)}")
            return None

    async def cancel_scheduled_notification(self, notification_id: str) -> bool:
        """Cancel a scheduled notification"""
        try:
            result = await self._make_request(
                "DELETE", 
                f"/api/v1/notifications/scheduled/{notification_id}"
            )
            return result is not None and result.get("success", False)
            
        except Exception as e:
            logger.error(f"Error canceling scheduled notification: {str(e)}")
            return False

    async def get_notification_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> Optional[List[Dict]]:
        """Get user notification history"""
        try:
            params = {
                "limit": limit,
                "offset": offset
            }
            
            result = await self._make_request(
                "GET", 
                f"/api/v1/notifications/history/{user_id}",
                params=params
            )
            return result.get("notifications", []) if result else []
            
        except Exception as e:
            logger.error(f"Error getting notification history: {str(e)}")
            return []

    async def get_available_templates(self) -> Optional[List[Dict]]:
        """Get available notification templates"""
        try:
            result = await self._make_request("GET", "/api/v1/templates")
            return result.get("templates", []) if result else []
            
        except Exception as e:
            logger.error(f"Error getting notification templates: {str(e)}")
            return []

    async def send_lesson_reminder(
        self,
        user_id: int,
        lesson_data: Dict[str, Any],
        reminder_type: str = "upcoming"
    ) -> bool:
        """Send lesson reminder notification"""
        try:
            template_name = f"lesson_{reminder_type}_reminder"
            
            data = {
                "user_id": user_id,
                "channel": "telegram",
                "template_name": template_name,
                "template_data": lesson_data,
                "notification_type": "reminder",
                "priority": "high" if reminder_type == "starting_soon" else "normal",
                "metadata": {
                    "source": "telegram_bot",
                    "lesson_id": lesson_data.get("lesson_id"),
                    "reminder_type": reminder_type,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            result = await self._make_request("POST", "/api/v1/notifications/send", data=data)
            return result is not None and result.get("success", False)
            
        except Exception as e:
            logger.error(f"Error sending lesson reminder: {str(e)}")
            return False

    async def send_homework_notification(
        self,
        user_id: int,
        homework_data: Dict[str, Any],
        notification_type: str = "assignment"
    ) -> bool:
        """Send homework-related notification"""
        try:
            template_name = f"homework_{notification_type}"
            
            data = {
                "user_id": user_id,
                "channel": "telegram",
                "template_name": template_name,
                "template_data": homework_data,
                "notification_type": notification_type,
                "priority": "normal",
                "metadata": {
                    "source": "telegram_bot",
                    "homework_id": homework_data.get("homework_id"),
                    "notification_type": notification_type,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            result = await self._make_request("POST", "/api/v1/notifications/send", data=data)
            return result is not None and result.get("success", False)
            
        except Exception as e:
            logger.error(f"Error sending homework notification: {str(e)}")
            return False

    async def send_payment_notification(
        self,
        user_id: int,
        payment_data: Dict[str, Any],
        notification_type: str = "payment_received"
    ) -> bool:
        """Send payment-related notification"""
        try:
            template_name = f"payment_{notification_type}"
            
            data = {
                "user_id": user_id,
                "channels": ["telegram", "email"],  # Important notifications go to both
                "template_name": template_name,
                "template_data": payment_data,
                "notification_type": "transaction",
                "priority": "high",
                "metadata": {
                    "source": "telegram_bot",
                    "payment_id": payment_data.get("payment_id"),
                    "notification_type": notification_type,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            result = await self._make_request("POST", "/api/v1/notifications/send", data=data)
            return result is not None and result.get("success", False)
            
        except Exception as e:
            logger.error(f"Error sending payment notification: {str(e)}")
            return False

    async def health_check(self) -> bool:
        """Check if Notification Service is healthy"""
        try:
            result = await self._make_request("GET", "/health")
            return result is not None and result.get("status") == "healthy"
            
        except Exception as e:
            logger.error(f"Notification service health check failed: {str(e)}")
            return False

# Global client instance
notification_client = NotificationServiceClient()