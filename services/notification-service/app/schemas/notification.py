from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class NotificationChannel(str, Enum):
    TELEGRAM = "telegram"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationType(str, Enum):
    LESSON_REMINDER = "lesson_reminder"
    LESSON_CANCELLED = "lesson_cancelled"
    HOMEWORK_ASSIGNED = "homework_assigned"
    HOMEWORK_OVERDUE = "homework_overdue"
    PAYMENT_PROCESSED = "payment_processed"
    BALANCE_LOW = "balance_low"
    MATERIAL_SHARED = "material_shared"
    SYSTEM_NOTIFICATION = "system_notification"
    CUSTOM = "custom"


# Base schemas
class NotificationBase(BaseModel):
    user_id: int = Field(..., description="ID пользователя-получателя")
    channel: NotificationChannel = Field(..., description="Канал доставки")
    recipient_address: str = Field(..., description="Адрес получателя")
    type: NotificationType = Field(..., description="Тип уведомления")
    title: str = Field(..., max_length=255, description="Заголовок уведомления")
    message: str = Field(..., description="Текст сообщения")
    html_message: Optional[str] = Field(None, description="HTML версия сообщения")
    priority: NotificationPriority = Field(NotificationPriority.NORMAL, description="Приоритет")
    scheduled_at: Optional[datetime] = Field(None, description="Время отправки")
    correlation_id: Optional[str] = Field(None, description="ID для группировки")
    context_data: Optional[Dict[str, Any]] = Field(None, description="Данные для шаблона")


class NotificationCreate(NotificationBase):
    template_name: Optional[str] = Field(None, description="Имя шаблона для использования")
    
    @validator('recipient_address')
    def validate_recipient_address(cls, v, values):
        channel = values.get('channel')
        if channel == NotificationChannel.EMAIL:
            # Basic email validation
            if '@' not in v:
                raise ValueError('Invalid email address')
        elif channel == NotificationChannel.TELEGRAM:
            # Telegram ID should be numeric
            if not v.isdigit():
                raise ValueError('Telegram ID should be numeric')
        return v


class NotificationUpdate(BaseModel):
    status: Optional[NotificationStatus] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    retry_count: Optional[int] = None


class NotificationResponse(NotificationBase):
    id: int
    status: NotificationStatus
    template_id: Optional[int] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    retry_count: int
    max_retries: int
    error_message: Optional[str] = None
    last_error_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Template schemas
class NotificationTemplateBase(BaseModel):
    name: str = Field(..., max_length=100, description="Уникальное имя шаблона")
    type: NotificationType = Field(..., description="Тип уведомления")
    channel: NotificationChannel = Field(..., description="Канал доставки")
    language: str = Field("ru", max_length=5, description="Язык шаблона")
    subject_template: str = Field(..., max_length=255, description="Шаблон заголовка")
    body_template: str = Field(..., description="Шаблон тела сообщения")
    html_template: Optional[str] = Field(None, description="HTML шаблон")
    description: Optional[str] = Field(None, description="Описание шаблона")
    variables: Optional[List[str]] = Field(None, description="Список доступных переменных")


class NotificationTemplateCreate(NotificationTemplateBase):
    pass


class NotificationTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    subject_template: Optional[str] = Field(None, max_length=255)
    body_template: Optional[str] = None
    html_template: Optional[str] = None
    description: Optional[str] = None
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = None


class NotificationTemplateResponse(NotificationTemplateBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Preference schemas
class NotificationPreferenceBase(BaseModel):
    user_id: int = Field(..., description="ID пользователя")
    notification_type: NotificationType = Field(..., description="Тип уведомления")
    telegram_enabled: bool = Field(True, description="Включить Telegram")
    email_enabled: bool = Field(True, description="Включить Email")
    push_enabled: bool = Field(True, description="Включить Push")
    sms_enabled: bool = Field(False, description="Включить SMS")
    quiet_hours_start: Optional[str] = Field(None, regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    quiet_hours_end: Optional[str] = Field(None, regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    timezone: str = Field("Europe/Moscow", description="Часовой пояс")
    digest_mode: bool = Field(False, description="Режим сводки")
    min_interval_minutes: int = Field(0, ge=0, description="Минимальный интервал в минутах")


class NotificationPreferenceCreate(NotificationPreferenceBase):
    pass


class NotificationPreferenceUpdate(BaseModel):
    telegram_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = Field(None, regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    quiet_hours_end: Optional[str] = Field(None, regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    timezone: Optional[str] = None
    digest_mode: Optional[bool] = None
    min_interval_minutes: Optional[int] = Field(None, ge=0)


class NotificationPreferenceResponse(NotificationPreferenceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Batch operation schemas
class BatchNotificationCreate(BaseModel):
    notifications: List[NotificationCreate] = Field(..., max_items=100)
    correlation_id: Optional[str] = Field(None, description="ID для группировки всех уведомлений")


class BatchNotificationResponse(BaseModel):
    total_created: int
    created_ids: List[int]
    errors: List[str] = []


# Statistics schemas
class NotificationStats(BaseModel):
    total_sent: int = 0
    total_delivered: int = 0
    total_failed: int = 0
    by_channel: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    by_status: Dict[str, int] = {}


# Event schemas for RabbitMQ
class NotificationEvent(BaseModel):
    event_type: str
    user_id: int
    notification_type: NotificationType
    data: Dict[str, Any] = {}
    correlation_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Template rendering request
class TemplateRenderRequest(BaseModel):
    template_name: str
    context_data: Dict[str, Any]
    language: str = "ru"


class TemplateRenderResponse(BaseModel):
    subject: str
    body: str
    html_body: Optional[str] = None