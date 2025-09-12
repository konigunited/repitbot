from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class UserActivity(Base):
    """User activity aggregated metrics"""
    __tablename__ = "user_activity"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)  # дата для агрегации
    
    # Активность по типам
    lessons_attended = Column(Integer, default=0)
    lessons_missed = Column(Integer, default=0) 
    homeworks_submitted = Column(Integer, default=0)
    homeworks_overdue = Column(Integer, default=0)
    materials_accessed = Column(Integer, default=0)
    
    # Временные метрики
    total_study_time = Column(Integer, default=0)  # в минутах
    average_lesson_rating = Column(Float, nullable=True)
    login_count = Column(Integer, default=0)
    session_duration = Column(Integer, default=0)  # в секундах
    
    # Успеваемость
    homework_completion_rate = Column(Float, default=0.0)
    lesson_attendance_rate = Column(Float, default=0.0)
    material_engagement_score = Column(Float, default=0.0)
    
    # Поведенческие метрики
    late_submissions = Column(Integer, default=0)
    early_submissions = Column(Integer, default=0)
    questions_asked = Column(Integer, default=0)
    help_requests = Column(Integer, default=0)
    
    # Технические метрики
    platform_usage = Column(JSON, nullable=True)  # {'web': 10, 'mobile': 5, 'telegram': 20}
    device_types = Column(JSON, nullable=True)
    peak_activity_hours = Column(JSON, nullable=True)
    
    # Прогресс и достижения
    skill_improvements = Column(JSON, nullable=True)
    badges_earned = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    
    # Социальные метрики
    peer_interactions = Column(Integer, default=0)
    tutor_interactions = Column(Integer, default=0)
    parent_communications = Column(Integer, default=0)
    
    # Качественные показатели
    satisfaction_score = Column(Float, nullable=True)  # 1-5
    difficulty_rating = Column(Float, nullable=True)  # 1-5
    recommendation_likelihood = Column(Float, nullable=True)  # 1-10
    
    # Флаги и статусы
    is_active = Column(Boolean, default=True)
    needs_attention = Column(Boolean, default=False)
    risk_level = Column(String, default='low')  # low, medium, high
    
    # Периодические данные
    week_number = Column(Integer, nullable=True)
    month_number = Column(Integer, nullable=True)
    quarter_number = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserActivity(user_id={self.user_id}, date={self.date})>"

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.date.isoformat() if self.date else None,
            'lessons_attended': self.lessons_attended,
            'lessons_missed': self.lessons_missed,
            'homeworks_submitted': self.homeworks_submitted,
            'homeworks_overdue': self.homeworks_overdue,
            'materials_accessed': self.materials_accessed,
            'total_study_time': self.total_study_time,
            'average_lesson_rating': self.average_lesson_rating,
            'homework_completion_rate': self.homework_completion_rate,
            'lesson_attendance_rate': self.lesson_attendance_rate,
            'satisfaction_score': self.satisfaction_score,
            'risk_level': self.risk_level,
            'streak_days': self.streak_days
        }

    def calculate_engagement_score(self) -> float:
        """Calculate user engagement score based on various activities"""
        score = 0.0
        
        # Activity weights
        if self.lessons_attended > 0:
            score += self.lesson_attendance_rate * 30
        
        if self.homeworks_submitted > 0:
            score += self.homework_completion_rate * 25
            
        if self.materials_accessed > 0:
            score += min(self.materials_accessed * 2, 20)
            
        if self.total_study_time > 0:
            score += min(self.total_study_time / 60 * 2, 15)  # convert to hours
            
        if self.login_count > 0:
            score += min(self.login_count * 0.5, 10)
            
        return min(score, 100.0)
    
    def get_risk_indicators(self) -> list:
        """Get list of risk indicators for this user"""
        indicators = []
        
        if self.lesson_attendance_rate < 0.8:
            indicators.append("low_attendance")
            
        if self.homework_completion_rate < 0.7:
            indicators.append("poor_homework_completion")
            
        if self.homeworks_overdue > 3:
            indicators.append("multiple_overdue_assignments")
            
        if self.total_study_time < 60:  # less than 1 hour per day
            indicators.append("insufficient_study_time")
            
        if self.login_count == 0:
            indicators.append("no_platform_usage")
            
        return indicators