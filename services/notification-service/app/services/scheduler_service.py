import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json
from app.core.config import settings
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class SchedulerService:
    """Сервис для отложенных и повторяющихся уведомлений"""
    
    def __init__(self):
        self.redis_client = None
        self.scheduler_key = "notification_scheduler"
        self.running = False
        
    async def connect(self):
        """Подключиться к Redis"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis for scheduler")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Отключиться от Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Disconnected from Redis")
    
    async def schedule_notification(
        self,
        notification_data: Dict[str, Any],
        scheduled_time: datetime,
        notification_id: Optional[str] = None
    ) -> str:
        """
        Запланировать отправку уведомления
        
        Args:
            notification_data: Данные уведомления
            scheduled_time: Время отправки
            notification_id: ID уведомления (опционально)
        
        Returns:
            ID задачи планировщика
        """
        if not self.redis_client:
            await self.connect()
        
        # Генерируем ID задачи
        task_id = notification_id or f"task_{int(datetime.utcnow().timestamp() * 1000)}"
        
        # Подготавливаем данные задачи
        task_data = {
            "task_id": task_id,
            "notification_data": notification_data,
            "scheduled_time": scheduled_time.isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "status": "scheduled"
        }
        
        # Сохраняем в Redis с score = timestamp
        score = scheduled_time.timestamp()
        
        try:
            await self.redis_client.zadd(
                self.scheduler_key,
                {json.dumps(task_data): score}
            )
            
            logger.info(f"Scheduled notification task {task_id} for {scheduled_time}")
            return task_id
            
        except Exception as e:
            logger.error(f"Error scheduling notification: {e}")
            raise
    
    async def cancel_scheduled_notification(self, task_id: str) -> bool:
        """
        Отменить запланированное уведомление
        
        Args:
            task_id: ID задачи
        
        Returns:
            True если задача была отменена
        """
        if not self.redis_client:
            await self.connect()
        
        try:
            # Получаем все задачи
            tasks = await self.redis_client.zrange(self.scheduler_key, 0, -1)
            
            for task_json in tasks:
                task_data = json.loads(task_json)
                if task_data.get("task_id") == task_id:
                    # Удаляем задачу
                    removed = await self.redis_client.zrem(self.scheduler_key, task_json)
                    if removed:
                        logger.info(f"Cancelled scheduled notification {task_id}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling scheduled notification {task_id}: {e}")
            return False
    
    async def get_scheduled_notifications(
        self,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None
    ) -> list:
        """
        Получить список запланированных уведомлений
        
        Args:
            from_time: Начало периода
            to_time: Конец периода
        
        Returns:
            Список запланированных уведомлений
        """
        if not self.redis_client:
            await self.connect()
        
        try:
            min_score = from_time.timestamp() if from_time else "-inf"
            max_score = to_time.timestamp() if to_time else "+inf"
            
            tasks = await self.redis_client.zrangebyscore(
                self.scheduler_key,
                min_score,
                max_score,
                withscores=True
            )
            
            scheduled_notifications = []
            for task_json, score in tasks:
                task_data = json.loads(task_json)
                task_data["scheduled_timestamp"] = score
                scheduled_notifications.append(task_data)
            
            return scheduled_notifications
            
        except Exception as e:
            logger.error(f"Error getting scheduled notifications: {e}")
            return []
    
    async def schedule_recurring_notification(
        self,
        notification_data: Dict[str, Any],
        start_time: datetime,
        interval_minutes: int,
        end_time: Optional[datetime] = None,
        max_occurrences: Optional[int] = None
    ) -> list:
        """
        Запланировать повторяющееся уведомление
        
        Args:
            notification_data: Данные уведомления
            start_time: Время первой отправки
            interval_minutes: Интервал в минутах
            end_time: Время окончания повторений
            max_occurrences: Максимальное количество повторений
        
        Returns:
            Список ID созданных задач
        """
        task_ids = []
        current_time = start_time
        occurrence_count = 0
        
        while True:
            # Проверяем условия остановки
            if end_time and current_time > end_time:
                break
            if max_occurrences and occurrence_count >= max_occurrences:
                break
            
            # Создаем данные для этого повторения
            recurring_data = notification_data.copy()
            recurring_data["recurring_sequence"] = occurrence_count + 1
            recurring_data["recurring_total"] = max_occurrences
            
            # Планируем уведомление
            task_id = f"recurring_{int(start_time.timestamp())}_{occurrence_count + 1}"
            await self.schedule_notification(recurring_data, current_time, task_id)
            task_ids.append(task_id)
            
            # Переходим к следующему времени
            current_time += timedelta(minutes=interval_minutes)
            occurrence_count += 1
            
            # Защита от бесконечного цикла
            if occurrence_count > 1000:
                logger.warning("Recurring notification limit reached (1000)")
                break
        
        logger.info(f"Scheduled {len(task_ids)} recurring notifications")
        return task_ids
    
    async def run_scheduler(self):
        """Запустить планировщик (основной цикл)"""
        if not self.redis_client:
            await self.connect()
        
        self.running = True
        logger.info("Notification scheduler started")
        
        while self.running:
            try:
                await self._process_due_notifications()
                await asyncio.sleep(30)  # Проверяем каждые 30 секунд
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)  # Увеличиваем интервал при ошибке
        
        logger.info("Notification scheduler stopped")
    
    async def stop_scheduler(self):
        """Остановить планировщик"""
        self.running = False
    
    async def _process_due_notifications(self):
        """Обработать уведомления, время которых наступило"""
        current_timestamp = datetime.utcnow().timestamp()
        
        try:
            # Получаем задачи, время которых наступило
            due_tasks = await self.redis_client.zrangebyscore(
                self.scheduler_key,
                "-inf",
                current_timestamp,
                withscores=True
            )
            
            if not due_tasks:
                return
            
            logger.info(f"Processing {len(due_tasks)} due notifications")
            
            for task_json, score in due_tasks:
                try:
                    task_data = json.loads(task_json)
                    
                    # Отправляем уведомление
                    await self._send_scheduled_notification(task_data)
                    
                    # Удаляем задачу из планировщика
                    await self.redis_client.zrem(self.scheduler_key, task_json)
                    
                except Exception as e:
                    logger.error(f"Error processing scheduled task: {e}")
                    # Оставляем задачу в планировщике для повторной попытки
                    continue
                    
        except Exception as e:
            logger.error(f"Error processing due notifications: {e}")
    
    async def _send_scheduled_notification(self, task_data: Dict[str, Any]):
        """Отправить запланированное уведомление"""
        from app.services.notification_service import NotificationService
        
        notification_data = task_data.get("notification_data", {})
        task_id = task_data.get("task_id")
        
        try:
            # Создаем экземпляр сервиса уведомлений
            notification_service = NotificationService()
            
            # Отправляем уведомление
            result = await notification_service.send_notification(
                user_id=notification_data.get("user_id"),
                channel=notification_data.get("channel"),
                recipient_address=notification_data.get("recipient_address"),
                notification_type=notification_data.get("type"),
                title=notification_data.get("title"),
                message=notification_data.get("message"),
                context_data=notification_data.get("context_data"),
                correlation_id=task_id
            )
            
            logger.info(f"Scheduled notification sent: {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error sending scheduled notification {task_id}: {e}")
            raise
    
    async def get_scheduler_stats(self) -> Dict[str, Any]:
        """Получить статистику планировщика"""
        if not self.redis_client:
            await self.connect()
        
        try:
            total_tasks = await self.redis_client.zcard(self.scheduler_key)
            
            current_time = datetime.utcnow().timestamp()
            overdue_tasks = await self.redis_client.zcount(
                self.scheduler_key,
                "-inf",
                current_time
            )
            
            return {
                "total_scheduled": total_tasks,
                "overdue": overdue_tasks,
                "pending": total_tasks - overdue_tasks,
                "running": self.running
            }
            
        except Exception as e:
            logger.error(f"Error getting scheduler stats: {e}")
            return {"error": str(e)}