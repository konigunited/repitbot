import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database.connection import get_db_session
from app.models.notification import (
    Notification, NotificationTemplate, NotificationPreference,
    NotificationChannel, NotificationStatus, NotificationType, NotificationPriority
)
from app.schemas.notification import NotificationCreate, NotificationUpdate
from app.services.telegram_service import TelegramService
from app.services.email_service import EmailService
from app.services.push_service import PushService
from app.services.template_service import TemplateService

logger = logging.getLogger(__name__)


class NotificationService:
    """Основной сервис для работы с уведомлениями"""
    
    def __init__(self):
        self.telegram_service = TelegramService()
        self.email_service = EmailService()
        self.push_service = PushService()
        self.template_service = TemplateService()
    
    async def send_notification(
        self,
        user_id: int,
        channel: NotificationChannel,
        recipient_address: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        html_message: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        context_data: Optional[Dict[str, Any]] = None,
        template_name: Optional[str] = None,
        correlation_id: Optional[str] = None,
        scheduled_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Отправить уведомление
        
        Args:
            user_id: ID пользователя
            channel: Канал доставки
            recipient_address: Адрес получателя
            notification_type: Тип уведомления
            title: Заголовок
            message: Текст сообщения
            html_message: HTML версия
            priority: Приоритет
            context_data: Данные для шаблона
            template_name: Имя шаблона
            correlation_id: ID корреляции
            scheduled_at: Время отправки
        
        Returns:
            Результат отправки
        """
        async with get_db_session() as db:
            try:
                # Проверяем предпочтения пользователя
                if not await self._check_user_preferences(db, user_id, notification_type, channel):
                    logger.info(f"Notification blocked by user preferences: {user_id}, {notification_type}, {channel}")
                    return {"success": False, "reason": "blocked_by_preferences"}
                
                # Применяем шаблон если указан
                if template_name:
                    template_result = await self._apply_template(
                        db, template_name, channel, context_data or {}
                    )
                    if template_result:
                        title = template_result["subject"]
                        message = template_result["body"]
                        if template_result.get("html_body"):
                            html_message = template_result["html_body"]
                
                # Создаем запись в БД
                notification = Notification(
                    user_id=user_id,
                    channel=channel,
                    recipient_address=recipient_address,
                    type=notification_type,
                    title=title,
                    message=message,
                    html_message=html_message,
                    priority=priority,
                    context_data=context_data,
                    correlation_id=correlation_id,
                    scheduled_at=scheduled_at,
                    status=NotificationStatus.PENDING
                )
                
                db.add(notification)
                await db.flush()
                await db.refresh(notification)
                
                # Если отправка запланирована на будущее
                if scheduled_at and scheduled_at > datetime.utcnow():
                    await db.commit()
                    return {
                        "success": True,
                        "notification_id": notification.id,
                        "status": "scheduled",
                        "scheduled_at": scheduled_at
                    }
                
                # Отправляем немедленно
                result = await self._deliver_notification(notification)
                
                # Обновляем статус
                if result["success"]:
                    notification.status = NotificationStatus.SENT
                    notification.sent_at = datetime.utcnow()
                else:
                    notification.status = NotificationStatus.FAILED
                    notification.error_message = result.get("error")
                    notification.last_error_at = datetime.utcnow()
                
                await db.commit()
                
                return {
                    "success": result["success"],
                    "notification_id": notification.id,
                    "channel": channel.value,
                    "error": result.get("error")
                }
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error sending notification: {e}")
                return {"success": False, "error": str(e)}
    
    async def send_batch_notifications(
        self,
        notifications: List[NotificationCreate],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Массовая отправка уведомлений
        
        Args:
            notifications: Список уведомлений
            correlation_id: ID корреляции для всех уведомлений
        
        Returns:
            Результат массовой отправки
        """
        results = {
            "total": len(notifications),
            "sent": 0,
            "failed": 0,
            "scheduled": 0,
            "errors": []
        }
        
        tasks = []
        for notification_data in notifications:
            task = self.send_notification(
                user_id=notification_data.user_id,
                channel=notification_data.channel,
                recipient_address=notification_data.recipient_address,
                notification_type=notification_data.type,
                title=notification_data.title,
                message=notification_data.message,
                html_message=notification_data.html_message,
                priority=notification_data.priority,
                context_data=notification_data.context_data,
                template_name=getattr(notification_data, 'template_name', None),
                correlation_id=correlation_id or notification_data.correlation_id,
                scheduled_at=notification_data.scheduled_at
            )
            tasks.append(task)
        
        # Выполняем батчи параллельно
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                results["failed"] += 1
                results["errors"].append(str(result))
            elif result.get("success"):
                if result.get("status") == "scheduled":
                    results["scheduled"] += 1
                else:
                    results["sent"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(result.get("error", "Unknown error"))
        
        logger.info(f"Batch notification completed: {results}")
        return results
    
    async def retry_failed_notification(self, notification_id: int) -> Dict[str, Any]:
        """
        Повторная отправка неудачного уведомления
        
        Args:
            notification_id: ID уведомления
        
        Returns:
            Результат повторной отправки
        """
        async with get_db_session() as db:
            try:
                # Получаем уведомление
                notification = await db.get(Notification, notification_id)
                if not notification:
                    return {"success": False, "error": "Notification not found"}
                
                if notification.status not in [NotificationStatus.FAILED, NotificationStatus.PENDING]:
                    return {"success": False, "error": "Notification not in retryable state"}
                
                if notification.retry_count >= notification.max_retries:
                    return {"success": False, "error": "Max retries exceeded"}
                
                # Увеличиваем счетчик попыток
                notification.retry_count += 1
                notification.status = NotificationStatus.SENDING
                
                await db.flush()
                
                # Пытаемся отправить
                result = await self._deliver_notification(notification)
                
                if result["success"]:
                    notification.status = NotificationStatus.SENT
                    notification.sent_at = datetime.utcnow()
                    notification.error_message = None
                else:
                    notification.status = NotificationStatus.FAILED
                    notification.error_message = result.get("error")
                    notification.last_error_at = datetime.utcnow()
                
                await db.commit()
                
                return {
                    "success": result["success"],
                    "notification_id": notification_id,
                    "retry_count": notification.retry_count,
                    "error": result.get("error")
                }
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Error retrying notification {notification_id}: {e}")
                return {"success": False, "error": str(e)}
    
    async def get_notification_status(self, notification_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить статус уведомления
        
        Args:
            notification_id: ID уведомления
        
        Returns:
            Статус уведомления
        """
        async with get_db_session() as db:
            try:
                notification = await db.get(Notification, notification_id)
                if not notification:
                    return None
                
                return {
                    "id": notification.id,
                    "status": notification.status.value,
                    "channel": notification.channel.value,
                    "type": notification.type.value,
                    "sent_at": notification.sent_at,
                    "delivered_at": notification.delivered_at,
                    "retry_count": notification.retry_count,
                    "error_message": notification.error_message,
                    "created_at": notification.created_at
                }
                
            except Exception as e:
                logger.error(f"Error getting notification status {notification_id}: {e}")
                return None
    
    async def get_user_notifications(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[NotificationStatus] = None
    ) -> List[Dict[str, Any]]:
        """
        Получить уведомления пользователя
        
        Args:
            user_id: ID пользователя
            limit: Лимит результатов
            offset: Смещение
            status_filter: Фильтр по статусу
        
        Returns:
            Список уведомлений
        """
        async with get_db_session() as db:
            try:
                query = select(Notification).where(Notification.user_id == user_id)
                
                if status_filter:
                    query = query.where(Notification.status == status_filter)
                
                query = query.order_by(Notification.created_at.desc())
                query = query.limit(limit).offset(offset)
                
                result = await db.execute(query)
                notifications = result.scalars().all()
                
                return [
                    {
                        "id": n.id,
                        "channel": n.channel.value,
                        "type": n.type.value,
                        "title": n.title,
                        "message": n.message,
                        "status": n.status.value,
                        "sent_at": n.sent_at,
                        "created_at": n.created_at
                    }
                    for n in notifications
                ]
                
            except Exception as e:
                logger.error(f"Error getting user notifications {user_id}: {e}")
                return []
    
    async def _deliver_notification(self, notification: Notification) -> Dict[str, Any]:
        """Доставить уведомление через соответствующий канал"""
        try:
            if notification.channel == NotificationChannel.TELEGRAM:
                return await self._send_telegram_notification(notification)
            elif notification.channel == NotificationChannel.EMAIL:
                return await self._send_email_notification(notification)
            elif notification.channel == NotificationChannel.PUSH:
                return await self._send_push_notification(notification)
            elif notification.channel == NotificationChannel.SMS:
                return await self._send_sms_notification(notification)
            else:
                return {"success": False, "error": f"Unsupported channel: {notification.channel}"}
                
        except Exception as e:
            logger.error(f"Error delivering notification {notification.id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_telegram_notification(self, notification: Notification) -> Dict[str, Any]:
        """Отправить Telegram уведомление"""
        try:
            message = notification.html_message or notification.message
            
            result = await self.telegram_service.send_message(
                chat_id=notification.recipient_address,
                text=message,
                parse_mode="HTML"
            )
            
            return {"success": True, "result": result}
            
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_email_notification(self, notification: Notification) -> Dict[str, Any]:
        """Отправить Email уведомление"""
        try:
            result = await self.email_service.send_email(
                to_email=notification.recipient_address,
                subject=notification.title,
                body_text=notification.message,
                body_html=notification.html_message
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_push_notification(self, notification: Notification) -> Dict[str, Any]:
        """Отправить Push уведомление"""
        try:
            # recipient_address содержит device token или их список
            tokens = [notification.recipient_address] if isinstance(notification.recipient_address, str) else notification.recipient_address
            
            result = await self.push_service.send_push_notification(
                device_tokens=tokens,
                title=notification.title,
                body=notification.message,
                data=notification.context_data
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending push notification: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_sms_notification(self, notification: Notification) -> Dict[str, Any]:
        """Отправить SMS уведомление (заглушка)"""
        # TODO: Реализовать SMS провайдер
        return {"success": False, "error": "SMS not implemented"}
    
    async def _check_user_preferences(
        self,
        db: AsyncSession,
        user_id: int,
        notification_type: NotificationType,
        channel: NotificationChannel
    ) -> bool:
        """Проверить предпочтения пользователя"""
        try:
            query = select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                NotificationPreference.notification_type == notification_type
            )
            
            result = await db.execute(query)
            preference = result.scalar_one_or_none()
            
            if not preference:
                return True  # Разрешаем по умолчанию
            
            if channel == NotificationChannel.TELEGRAM:
                return preference.telegram_enabled
            elif channel == NotificationChannel.EMAIL:
                return preference.email_enabled
            elif channel == NotificationChannel.PUSH:
                return preference.push_enabled
            elif channel == NotificationChannel.SMS:
                return preference.sms_enabled
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking user preferences: {e}")
            return True  # При ошибке разрешаем отправку
    
    async def _apply_template(
        self,
        db: AsyncSession,
        template_name: str,
        channel: NotificationChannel,
        context_data: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        """Применить шаблон к уведомлению"""
        try:
            query = select(NotificationTemplate).where(
                NotificationTemplate.name == template_name,
                NotificationTemplate.channel == channel,
                NotificationTemplate.is_active == True
            )
            
            result = await db.execute(query)
            template = result.scalar_one_or_none()
            
            if not template:
                logger.warning(f"Template not found: {template_name} for {channel}")
                return None
            
            # Рендерим шаблоны
            subject = await self.template_service.render_template(
                template.subject_template, context_data, template_name
            )
            body = await self.template_service.render_template(
                template.body_template, context_data, template_name
            )
            
            result = {
                "subject": subject,
                "body": body
            }
            
            if template.html_template:
                html_body = await self.template_service.render_template(
                    template.html_template, context_data, template_name
                )
                result["html_body"] = html_body
            
            return result
            
        except Exception as e:
            logger.error(f"Error applying template {template_name}: {e}")
            return None