from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db_session
from app.schemas.notification import (
    NotificationCreate, NotificationResponse, NotificationUpdate,
    BatchNotificationCreate, BatchNotificationResponse,
    NotificationStats, TemplateRenderRequest, TemplateRenderResponse
)
from app.models.notification import NotificationStatus, NotificationChannel, NotificationType
from app.services.notification_service import NotificationService
from app.services.template_service import TemplateService
from app.services.scheduler_service import SchedulerService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

# Зависимости
def get_notification_service() -> NotificationService:
    return NotificationService()

def get_template_service() -> TemplateService:
    return TemplateService()

def get_scheduler_service() -> SchedulerService:
    return SchedulerService()


@router.post("/send", response_model=dict)
async def send_notification(
    notification_data: NotificationCreate,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Отправить уведомление"""
    try:
        result = await notification_service.send_notification(
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
            correlation_id=notification_data.correlation_id,
            scheduled_at=notification_data.scheduled_at
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in send_notification endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=BatchNotificationResponse)
async def send_batch_notifications(
    batch_data: BatchNotificationCreate,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Массовая отправка уведомлений"""
    try:
        result = await notification_service.send_batch_notifications(
            notifications=batch_data.notifications,
            correlation_id=batch_data.correlation_id
        )
        
        return BatchNotificationResponse(
            total_created=result["total"],
            created_ids=[],  # TODO: Возвращать реальные ID
            errors=result["errors"]
        )
        
    except Exception as e:
        logger.error(f"Error in batch_notifications endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{notification_id}", response_model=dict)
async def get_notification_status(
    notification_id: int,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Получить статус уведомления"""
    try:
        result = await notification_service.get_notification_status(notification_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_notification_status endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{notification_id}/retry", response_model=dict)
async def retry_notification(
    notification_id: int,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Повторная отправка уведомления"""
    try:
        result = await notification_service.retry_failed_notification(notification_id)
        return result
        
    except Exception as e:
        logger.error(f"Error in retry_notification endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}", response_model=List[dict])
async def get_user_notifications(
    user_id: int,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[NotificationStatus] = Query(None),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Получить уведомления пользователя"""
    try:
        notifications = await notification_service.get_user_notifications(
            user_id=user_id,
            limit=limit,
            offset=offset,
            status_filter=status
        )
        
        return notifications
        
    except Exception as e:
        logger.error(f"Error in get_user_notifications endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/template/render", response_model=TemplateRenderResponse)
async def render_template(
    render_request: TemplateRenderRequest,
    template_service: TemplateService = Depends(get_template_service)
):
    """Рендерить шаблон"""
    try:
        # Получаем шаблон из БД
        from app.database.connection import get_db_session
        from sqlalchemy import select
        from app.models.notification import NotificationTemplate
        
        async with get_db_session() as db:
            query = select(NotificationTemplate).where(
                NotificationTemplate.name == render_request.template_name,
                NotificationTemplate.language == render_request.language,
                NotificationTemplate.is_active == True
            )
            result = await db.execute(query)
            template = result.scalar_one_or_none()
            
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
            
            # Рендерим шаблон
            subject = await template_service.render_template(
                template.subject_template,
                render_request.context_data
            )
            body = await template_service.render_template(
                template.body_template,
                render_request.context_data
            )
            
            response = TemplateRenderResponse(
                subject=subject,
                body=body
            )
            
            if template.html_template:
                html_body = await template_service.render_template(
                    template.html_template,
                    render_request.context_data
                )
                response.html_body = html_body
            
            return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in render_template endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary", response_model=NotificationStats)
async def get_notification_stats(
    user_id: Optional[int] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    """Получить статистику уведомлений"""
    try:
        from sqlalchemy import select, func
        from app.models.notification import Notification
        
        query = select(Notification)
        
        if user_id:
            query = query.where(Notification.user_id == user_id)
        if from_date:
            query = query.where(Notification.created_at >= from_date)
        if to_date:
            query = query.where(Notification.created_at <= to_date)
        
        result = await db.execute(query)
        notifications = result.scalars().all()
        
        stats = NotificationStats()
        stats.by_channel = {}
        stats.by_type = {}
        stats.by_status = {}
        
        for notification in notifications:
            # Статистика по каналам
            channel_key = notification.channel.value
            stats.by_channel[channel_key] = stats.by_channel.get(channel_key, 0) + 1
            
            # Статистика по типам
            type_key = notification.type.value
            stats.by_type[type_key] = stats.by_type.get(type_key, 0) + 1
            
            # Статистика по статусам
            status_key = notification.status.value
            stats.by_status[status_key] = stats.by_status.get(status_key, 0) + 1
            
            # Общая статистика
            if notification.status == NotificationStatus.SENT:
                stats.total_sent += 1
            elif notification.status == NotificationStatus.DELIVERED:
                stats.total_delivered += 1
            elif notification.status == NotificationStatus.FAILED:
                stats.total_failed += 1
        
        return stats
        
    except Exception as e:
        logger.error(f"Error in get_notification_stats endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule", response_model=dict)
async def schedule_notification(
    notification_data: NotificationCreate,
    background_tasks: BackgroundTasks,
    scheduler_service: SchedulerService = Depends(get_scheduler_service)
):
    """Запланировать отправку уведомления"""
    try:
        if not notification_data.scheduled_at:
            raise HTTPException(status_code=400, detail="scheduled_at is required")
        
        if notification_data.scheduled_at <= datetime.utcnow():
            raise HTTPException(status_code=400, detail="scheduled_at must be in the future")
        
        # Данные для планировщика
        notification_dict = {
            "user_id": notification_data.user_id,
            "channel": notification_data.channel.value,
            "recipient_address": notification_data.recipient_address,
            "type": notification_data.type.value,
            "title": notification_data.title,
            "message": notification_data.message,
            "html_message": notification_data.html_message,
            "priority": notification_data.priority.value,
            "context_data": notification_data.context_data,
            "correlation_id": notification_data.correlation_id
        }
        
        task_id = await scheduler_service.schedule_notification(
            notification_data=notification_dict,
            scheduled_time=notification_data.scheduled_at
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "scheduled_at": notification_data.scheduled_at,
            "message": "Notification scheduled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in schedule_notification endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/schedule/{task_id}", response_model=dict)
async def cancel_scheduled_notification(
    task_id: str,
    scheduler_service: SchedulerService = Depends(get_scheduler_service)
):
    """Отменить запланированное уведомление"""
    try:
        success = await scheduler_service.cancel_scheduled_notification(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Scheduled notification not found")
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Scheduled notification cancelled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in cancel_scheduled_notification endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedule/list", response_model=List[dict])
async def list_scheduled_notifications(
    from_time: Optional[datetime] = Query(None),
    to_time: Optional[datetime] = Query(None),
    scheduler_service: SchedulerService = Depends(get_scheduler_service)
):
    """Получить список запланированных уведомлений"""
    try:
        scheduled = await scheduler_service.get_scheduled_notifications(
            from_time=from_time,
            to_time=to_time
        )
        
        return scheduled
        
    except Exception as e:
        logger.error(f"Error in list_scheduled_notifications endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint"""
    try:
        # Проверяем основные сервисы
        telegram_service = TelegramService()
        email_service = EmailService()
        push_service = PushService()
        
        telegram_status = await telegram_service.check_bot_status()
        email_status = await email_service.check_connection()
        push_status = push_service.is_configured()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "services": {
                "telegram": "ok" if telegram_status else "error",
                "email": "ok" if email_status else "error", 
                "push": "ok" if push_status else "not_configured"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in health_check endpoint: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow(),
            "error": str(e)
        }