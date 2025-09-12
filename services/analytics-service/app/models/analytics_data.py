from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class AnalyticsData(Base):
    """Base analytics data model for storing raw metrics"""
    __tablename__ = "analytics_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String, nullable=False, index=True)  # lesson, payment, homework, etc.
    entity_id = Column(String, nullable=False)  # ID сущности
    user_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Метаданные события
    metadata = Column(JSON, nullable=True)
    
    # Числовые метрики
    value = Column(Float, nullable=True)
    duration = Column(Integer, nullable=True)  # в секундах
    count = Column(Integer, default=1)
    
    # Статус и категоризация
    status = Column(String, nullable=True)
    category = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)  # массив тегов
    
    # Географические данные
    location = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    
    # Технические данные
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    platform = Column(String, nullable=True)
    
    # Контекст
    session_id = Column(String, nullable=True)
    parent_event_id = Column(String, ForeignKey('analytics_data.id'), nullable=True)
    
    # Флаги
    is_processed = Column(Boolean, default=False)
    is_anomaly = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent_event = relationship("AnalyticsData", remote_side=[id])

    def __repr__(self):
        return f"<AnalyticsData(id={self.id}, event_type={self.event_type}, user_id={self.user_id})>"

    def to_dict(self):
        return {
            'id': self.id,
            'event_type': self.event_type,
            'entity_id': self.entity_id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': self.metadata,
            'value': self.value,
            'duration': self.duration,
            'count': self.count,
            'status': self.status,
            'category': self.category,
            'tags': self.tags,
            'location': self.location,
            'timezone': self.timezone,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }