import asyncio
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import aio_pika
from aio_pika import Message, DeliveryMode
from app.core.config import settings
from app.services.notification_service import NotificationService
from app.models.notification import NotificationChannel, NotificationType, NotificationPriority

logger = logging.getLogger(__name__)


class NotificationEventConsumer:
    """Консюмер событий для отправки уведомлений"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.notification_service = NotificationService()
        self.running = False
        
        # Маппинг событий на типы уведомлений
        self.event_mapping = {
            "lesson.created": NotificationType.LESSON_REMINDER,
            "lesson.cancelled": NotificationType.LESSON_CANCELLED,
            "homework.assigned": NotificationType.HOMEWORK_ASSIGNED,
            "homework.overdue": NotificationType.HOMEWORK_OVERDUE,
            "payment.processed": NotificationType.PAYMENT_PROCESSED,
            "balance.low": NotificationType.BALANCE_LOW,
            "material.shared": NotificationType.MATERIAL_SHARED,
        }
    
    async def connect(self):
        """Подключиться к RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            self.channel = await self.connection.channel()
            
            # Настраиваем QoS
            await self.channel.set_qos(prefetch_count=10)
            
            logger.info("Connected to RabbitMQ for notifications")
            
        except Exception as e:
            logger.error(f"Error connecting to RabbitMQ: {e}")
            raise
    
    async def disconnect(self):
        """Отключиться от RabbitMQ"""
        if self.connection:
            await self.connection.close()
            logger.info("Disconnected from RabbitMQ")
    
    async def start_consuming(self):
        """Запустить обработку событий"""
        if not self.connection:
            await self.connect()
        
        self.running = True
        
        try:
            # Создаем exchange для событий
            events_exchange = await self.channel.declare_exchange(
                "events", aio_pika.ExchangeType.TOPIC, durable=True
            )
            
            # Создаем очередь для уведомлений
            notifications_queue = await self.channel.declare_queue(
                "notifications", durable=True
            )
            
            # Привязываем очередь к событиям
            bindings = [
                "lesson.created",
                "lesson.cancelled", 
                "lesson.reminder",
                "homework.assigned",
                "homework.overdue",
                "payment.processed",
                "balance.low",
                "material.shared",
                "user.registered",
                "system.notification"
            ]
            
            for binding in bindings:
                await notifications_queue.bind(events_exchange, binding)
            
            # Запускаем обработчик
            await notifications_queue.consume(self.process_event)
            
            logger.info("Started consuming notification events")
            
            # Ждем пока не остановим
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in event consumer: {e}")
            raise
        finally:
            self.running = False
    
    async def stop_consuming(self):
        """Остановить обработку событий"""
        self.running = False
        logger.info("Stopping notification event consumer")
    
    async def process_event(self, message: aio_pika.IncomingMessage):
        """Обработать событие"""
        async with message.process():
            try:
                # Парсим данные события
                event_data = json.loads(message.body.decode())
                routing_key = message.routing_key
                
                logger.info(f"Processing event: {routing_key}")
                
                # Обрабатываем в зависимости от типа события
                await self._handle_event(routing_key, event_data)
                
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                # Не перекидываем исключение, чтобы сообщение было acknowledged
    
    async def _handle_event(self, event_type: str, event_data: Dict[str, Any]):
        """Обработать конкретное событие"""
        try:
            if event_type == "lesson.created":
                await self._handle_lesson_created(event_data)
            elif event_type == "lesson.cancelled":
                await self._handle_lesson_cancelled(event_data)
            elif event_type == "lesson.reminder":
                await self._handle_lesson_reminder(event_data)
            elif event_type == "homework.assigned":
                await self._handle_homework_assigned(event_data)
            elif event_type == "homework.overdue":
                await self._handle_homework_overdue(event_data)
            elif event_type == "payment.processed":
                await self._handle_payment_processed(event_data)
            elif event_type == "balance.low":
                await self._handle_balance_low(event_data)
            elif event_type == "material.shared":
                await self._handle_material_shared(event_data)
            elif event_type == "user.registered":
                await self._handle_user_registered(event_data)
            elif event_type == "system.notification":
                await self._handle_system_notification(event_data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling event {event_type}: {e}")
    
    async def _handle_lesson_created(self, data: Dict[str, Any]):
        """Обработать событие создания урока"""
        lesson = data.get("lesson", {})
        student_id = lesson.get("student_id")
        tutor_id = lesson.get("tutor_id")
        
        if not student_id:
            return
        
        # Получаем контактную информацию
        user_contacts = await self._get_user_contacts(student_id)
        
        # Запланировать напоминание за час до урока
        lesson_time = datetime.fromisoformat(lesson.get("start_time"))
        reminder_time = lesson_time - timedelta(hours=1)
        
        context_data = {
            "lesson": lesson,
            "student": data.get("student", {}),
            "tutor": data.get("tutor", {})
        }
        
        for contact in user_contacts:
            await self.notification_service.send_notification(
                user_id=student_id,
                channel=contact["channel"],
                recipient_address=contact["address"],
                notification_type=NotificationType.LESSON_REMINDER,
                title="Напоминание об уроке",
                message=f"У вас урок {lesson.get('subject')} через час",
                context_data=context_data,
                template_name="lesson_reminder",
                scheduled_at=reminder_time,
                priority=NotificationPriority.HIGH
            )
    
    async def _handle_lesson_cancelled(self, data: Dict[str, Any]):
        """Обработать событие отмены урока"""
        lesson = data.get("lesson", {})
        student_id = lesson.get("student_id")
        tutor_id = lesson.get("tutor_id")
        
        # Уведомляем студента
        if student_id:
            user_contacts = await self._get_user_contacts(student_id)
            
            for contact in user_contacts:
                await self.notification_service.send_notification(
                    user_id=student_id,
                    channel=contact["channel"],
                    recipient_address=contact["address"],
                    notification_type=NotificationType.LESSON_CANCELLED,
                    title="Урок отменен",
                    message=f"Урок {lesson.get('subject')} на {lesson.get('start_time')} отменен",
                    context_data={"lesson": lesson, "reason": data.get("reason")},
                    template_name="lesson_cancelled",
                    priority=NotificationPriority.HIGH
                )
        
        # Уведомляем преподавателя
        if tutor_id:
            tutor_contacts = await self._get_user_contacts(tutor_id)
            
            for contact in tutor_contacts:
                await self.notification_service.send_notification(
                    user_id=tutor_id,
                    channel=contact["channel"],
                    recipient_address=contact["address"],
                    notification_type=NotificationType.LESSON_CANCELLED,
                    title="Урок отменен",
                    message=f"Урок отменен: {lesson.get('subject')}",
                    context_data={"lesson": lesson, "reason": data.get("reason")},
                    template_name="lesson_cancelled",
                    priority=NotificationPriority.HIGH
                )
    
    async def _handle_lesson_reminder(self, data: Dict[str, Any]):
        """Обработать напоминание об уроке"""
        lesson = data.get("lesson", {})
        student_id = lesson.get("student_id")
        
        if not student_id:
            return
        
        user_contacts = await self._get_user_contacts(student_id)
        
        for contact in user_contacts:
            await self.notification_service.send_notification(
                user_id=student_id,
                channel=contact["channel"],
                recipient_address=contact["address"],
                notification_type=NotificationType.LESSON_REMINDER,
                title="Напоминание об уроке",
                message=f"У вас урок {lesson.get('subject')} начинается через {data.get('time_until', '1 час')}",
                context_data={"lesson": lesson, "time_until": data.get("time_until")},
                template_name="lesson_reminder",
                priority=NotificationPriority.HIGH
            )
    
    async def _handle_homework_assigned(self, data: Dict[str, Any]):
        """Обработать событие назначения домашнего задания"""
        homework = data.get("homework", {})
        student_id = homework.get("student_id")
        
        if not student_id:
            return
        
        user_contacts = await self._get_user_contacts(student_id)
        
        for contact in user_contacts:
            await self.notification_service.send_notification(
                user_id=student_id,
                channel=contact["channel"],
                recipient_address=contact["address"],
                notification_type=NotificationType.HOMEWORK_ASSIGNED,
                title="Новое домашнее задание",
                message=f"Назначено новое задание по предмету {homework.get('subject')}",
                context_data={"homework": homework, "tutor": data.get("tutor", {})},
                template_name="homework_assigned",
                priority=NotificationPriority.NORMAL
            )
    
    async def _handle_homework_overdue(self, data: Dict[str, Any]):
        """Обработать событие просрочки домашнего задания"""
        homework = data.get("homework", {})
        student_id = homework.get("student_id")
        
        if not student_id:
            return
        
        user_contacts = await self._get_user_contacts(student_id)
        
        for contact in user_contacts:
            await self.notification_service.send_notification(
                user_id=student_id,
                channel=contact["channel"],
                recipient_address=contact["address"],
                notification_type=NotificationType.HOMEWORK_OVERDUE,
                title="Просроченное домашнее задание",
                message=f"Домашнее задание по {homework.get('subject')} просрочено",
                context_data={"homework": homework},
                template_name="homework_overdue",
                priority=NotificationPriority.URGENT
            )
    
    async def _handle_payment_processed(self, data: Dict[str, Any]):
        """Обработать событие обработки платежа"""
        payment = data.get("payment", {})
        user_id = payment.get("user_id")
        
        if not user_id:
            return
        
        user_contacts = await self._get_user_contacts(user_id)
        
        for contact in user_contacts:
            await self.notification_service.send_notification(
                user_id=user_id,
                channel=contact["channel"],
                recipient_address=contact["address"],
                notification_type=NotificationType.PAYMENT_PROCESSED,
                title="Платеж обработан",
                message=f"Платеж на сумму {payment.get('amount')} успешно обработан",
                context_data={"payment": payment},
                template_name="payment_processed",
                priority=NotificationPriority.HIGH
            )
    
    async def _handle_balance_low(self, data: Dict[str, Any]):
        """Обработать событие низкого баланса"""
        user_id = data.get("user_id")
        balance = data.get("balance", {})
        
        if not user_id:
            return
        
        user_contacts = await self._get_user_contacts(user_id)
        
        for contact in user_contacts:
            await self.notification_service.send_notification(
                user_id=user_id,
                channel=contact["channel"],
                recipient_address=contact["address"],
                notification_type=NotificationType.BALANCE_LOW,
                title="Низкий баланс",
                message=f"Ваш баланс составляет {balance.get('amount')}. Рекомендуем пополнить счет.",
                context_data={"balance": balance, "user": data.get("user", {})},
                template_name="balance_low",
                priority=NotificationPriority.NORMAL
            )
    
    async def _handle_material_shared(self, data: Dict[str, Any]):
        """Обработать событие публикации материала"""
        material = data.get("material", {})
        student_id = material.get("student_id")
        
        if not student_id:
            return
        
        user_contacts = await self._get_user_contacts(student_id)
        
        for contact in user_contacts:
            await self.notification_service.send_notification(
                user_id=student_id,
                channel=contact["channel"],
                recipient_address=contact["address"],
                notification_type=NotificationType.MATERIAL_SHARED,
                title="Новый учебный материал",
                message=f"Для вас опубликован новый материал: {material.get('title')}",
                context_data={"material": material, "tutor": data.get("tutor", {})},
                template_name="material_shared",
                priority=NotificationPriority.NORMAL
            )
    
    async def _handle_user_registered(self, data: Dict[str, Any]):
        """Обработать событие регистрации пользователя"""
        user = data.get("user", {})
        user_id = user.get("id")
        
        if not user_id:
            return
        
        user_contacts = await self._get_user_contacts(user_id)
        
        for contact in user_contacts:
            await self.notification_service.send_notification(
                user_id=user_id,
                channel=contact["channel"],
                recipient_address=contact["address"],
                notification_type=NotificationType.SYSTEM_NOTIFICATION,
                title="Добро пожаловать в RepitBot!",
                message=f"Добро пожаловать, {user.get('name')}! Ваш аккаунт успешно создан.",
                context_data={"user": user},
                template_name="welcome_message",
                priority=NotificationPriority.NORMAL
            )
    
    async def _handle_system_notification(self, data: Dict[str, Any]):
        """Обработать системное уведомление"""
        user_id = data.get("user_id")
        title = data.get("title", "Системное уведомление")
        message = data.get("message", "")
        
        if not user_id or not message:
            return
        
        user_contacts = await self._get_user_contacts(user_id)
        
        for contact in user_contacts:
            await self.notification_service.send_notification(
                user_id=user_id,
                channel=contact["channel"],
                recipient_address=contact["address"],
                notification_type=NotificationType.SYSTEM_NOTIFICATION,
                title=title,
                message=message,
                context_data=data.get("context_data", {}),
                priority=NotificationPriority.NORMAL
            )
    
    async def _get_user_contacts(self, user_id: int) -> list:
        """Получить контактную информацию пользователя"""
        try:
            # TODO: Реализовать получение контактов из User Service
            # Пока возвращаем заглушку
            
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.USER_SERVICE_URL}/api/v1/users/{user_id}/contacts"
                )
                
                if response.status_code == 200:
                    contacts_data = response.json()
                    contacts = []
                    
                    # Преобразуем в нужный формат
                    if contacts_data.get("telegram_id"):
                        contacts.append({
                            "channel": NotificationChannel.TELEGRAM,
                            "address": str(contacts_data["telegram_id"])
                        })
                    
                    if contacts_data.get("email"):
                        contacts.append({
                            "channel": NotificationChannel.EMAIL,
                            "address": contacts_data["email"]
                        })
                    
                    return contacts
                
        except Exception as e:
            logger.error(f"Error getting user contacts for {user_id}: {e}")
        
        # Заглушка - возвращаем пустой список
        return []


# Глобальный экземпляр консюмера
notification_consumer = NotificationEventConsumer()