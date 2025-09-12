import asyncio
import logging
from contextual import get_logger
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.database.connection import init_db, close_db
from app.api.v1.notifications import router as notifications_router
from app.services.template_service import TemplateService
from app.services.scheduler_service import SchedulerService
from app.events.notification_events import notification_consumer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создаем FastAPI приложение
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Настраиваем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(notifications_router)

# Глобальные переменные для сервисов
scheduler_service = None
consumer_task = None
scheduler_task = None


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения"""
    global scheduler_service, consumer_task, scheduler_task
    
    try:
        logger.info("Starting Notification Service...")
        
        # Инициализируем базу данных
        await init_db()
        logger.info("Database initialized")
        
        # Создаем шаблоны по умолчанию
        template_service = TemplateService()
        await template_service.create_default_templates()
        logger.info("Default templates created")
        
        # Запускаем планировщик
        scheduler_service = SchedulerService()
        scheduler_task = asyncio.create_task(scheduler_service.run_scheduler())
        logger.info("Scheduler started")
        
        # Запускаем обработчик событий
        consumer_task = asyncio.create_task(notification_consumer.start_consuming())
        logger.info("Event consumer started")
        
        logger.info("Notification Service started successfully")
        
    except Exception as e:
        logger.error(f"Error starting Notification Service: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке приложения"""
    global scheduler_service, consumer_task, scheduler_task
    
    try:
        logger.info("Shutting down Notification Service...")
        
        # Останавливаем обработчик событий
        if consumer_task:
            await notification_consumer.stop_consuming()
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
        
        await notification_consumer.disconnect()
        
        # Останавливаем планировщик
        if scheduler_service:
            await scheduler_service.stop_scheduler()
            
        if scheduler_task:
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass
        
        if scheduler_service:
            await scheduler_service.disconnect()
        
        # Закрываем соединения с БД
        await close_db()
        
        logger.info("Notification Service stopped")
        
    except Exception as e:
        logger.error(f"Error shutting down Notification Service: {e}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальный обработчик исключений"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Notification Service",
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Проверяем состояние основных компонентов
        health_status = {
            "service": "notification-service",
            "status": "healthy",
            "version": settings.VERSION,
            "timestamp": "2024-01-01T00:00:00Z",  # TODO: использовать реальное время
            "components": {
                "database": "unknown",
                "scheduler": "unknown",
                "event_consumer": "unknown"
            }
        }
        
        # Проверяем планировщик
        if scheduler_service:
            scheduler_stats = await scheduler_service.get_scheduler_stats()
            if "error" not in scheduler_stats:
                health_status["components"]["scheduler"] = "healthy"
                health_status["scheduler_stats"] = scheduler_stats
            else:
                health_status["components"]["scheduler"] = "error"
                health_status["status"] = "degraded"
        else:
            health_status["components"]["scheduler"] = "not_running"
            health_status["status"] = "degraded"
        
        # Проверяем обработчик событий
        if notification_consumer.running:
            health_status["components"]["event_consumer"] = "healthy"
        else:
            health_status["components"]["event_consumer"] = "stopped"
            health_status["status"] = "degraded"
        
        # Проверяем БД (простая проверка)
        try:
            from app.database.connection import get_db_session
            async with get_db_session() as db:
                # Простой запрос для проверки соединения
                await db.execute("SELECT 1")
                health_status["components"]["database"] = "healthy"
        except Exception as e:
            health_status["components"]["database"] = "error"
            health_status["status"] = "unhealthy"
            logger.error(f"Database health check failed: {e}")
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "service": "notification-service",
            "status": "unhealthy",
            "error": str(e)
        }


@app.get("/metrics")
async def metrics():
    """Metrics endpoint for monitoring"""
    try:
        from app.database.connection import get_db_session
        from sqlalchemy import select, func
        from app.models.notification import Notification, NotificationStatus
        
        metrics = {
            "notifications_total": 0,
            "notifications_sent": 0,
            "notifications_failed": 0,
            "notifications_pending": 0
        }
        
        async with get_db_session() as db:
            # Общее количество уведомлений
            total_query = select(func.count(Notification.id))
            result = await db.execute(total_query)
            metrics["notifications_total"] = result.scalar() or 0
            
            # По статусам
            for status in [NotificationStatus.SENT, NotificationStatus.FAILED, NotificationStatus.PENDING]:
                status_query = select(func.count(Notification.id)).where(Notification.status == status)
                result = await db.execute(status_query)
                key = f"notifications_{status.value}"
                metrics[key] = result.scalar() or 0
        
        # Статистика планировщика
        if scheduler_service:
            scheduler_stats = await scheduler_service.get_scheduler_stats()
            if "error" not in scheduler_stats:
                metrics.update({
                    "scheduled_notifications_total": scheduler_stats.get("total_scheduled", 0),
                    "scheduled_notifications_overdue": scheduler_stats.get("overdue", 0)
                })
        
        return metrics
        
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )