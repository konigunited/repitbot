from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class LessonStats(Base):
    """Lesson statistics and aggregated metrics"""
    __tablename__ = "lesson_stats"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_id = Column(String, nullable=False, index=True)
    tutor_id = Column(String, nullable=False, index=True)
    student_id = Column(String, nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    
    # Основные метрики урока
    duration_minutes = Column(Integer, nullable=False)
    planned_duration = Column(Integer, nullable=False)
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)
    
    # Статусы и результаты
    status = Column(String, nullable=False)  # completed, cancelled, missed, rescheduled
    completion_rate = Column(Float, default=0.0)  # % выполнения плана урока
    attendance_status = Column(String, nullable=False)  # present, absent, late
    
    # Оценки и фидбек
    tutor_rating = Column(Float, nullable=True)  # от тьютора к студенту
    student_rating = Column(Float, nullable=True)  # от студента к тьютору
    parent_rating = Column(Float, nullable=True)  # от родителя
    difficulty_rating = Column(Float, nullable=True)  # сложность урока 1-5
    
    # Контент и материалы
    materials_used = Column(JSON, nullable=True)  # список ID материалов
    topics_covered = Column(JSON, nullable=True)  # темы, пройденные на уроке
    homework_assigned = Column(JSON, nullable=True)  # назначенные ДЗ
    
    # Активность и вовлеченность
    student_questions = Column(Integer, default=0)
    tutor_explanations = Column(Integer, default=0)
    interactive_activities = Column(Integer, default=0)
    breaks_taken = Column(Integer, default=0)
    
    # Технические метрики
    connection_quality = Column(Float, nullable=True)  # 1-5
    technical_issues = Column(JSON, nullable=True)  # список проблем
    platform_used = Column(String, nullable=True)  # zoom, teams, etc.
    
    # Прогресс и достижения
    learning_objectives_met = Column(JSON, nullable=True)
    skills_practiced = Column(JSON, nullable=True)
    improvements_noted = Column(JSON, nullable=True)
    areas_for_improvement = Column(JSON, nullable=True)
    
    # Поведенческие показатели
    punctuality_score = Column(Float, nullable=True)  # насколько вовремя начался урок
    engagement_score = Column(Float, nullable=True)  # вовлеченность студента
    preparation_score = Column(Float, nullable=True)  # подготовленность к уроку
    
    # Расписание и планирование
    was_rescheduled = Column(Boolean, default=False)
    reschedule_count = Column(Integer, default=0)
    advance_notice_hours = Column(Integer, nullable=True)  # за сколько часов отменили/перенесли
    
    # Коммуникация
    pre_lesson_messages = Column(Integer, default=0)
    post_lesson_messages = Column(Integer, default=0)
    parent_communication = Column(Boolean, default=False)
    
    # Результативность
    homework_completion_previous = Column(Boolean, nullable=True)
    quiz_scores = Column(JSON, nullable=True)
    progress_milestones = Column(JSON, nullable=True)
    
    # Настроение и эмоциональное состояние
    student_mood = Column(String, nullable=True)  # happy, neutral, frustrated, etc.
    energy_level = Column(String, nullable=True)  # high, medium, low
    motivation_level = Column(Float, nullable=True)  # 1-5
    
    # Административные данные
    cost = Column(Float, nullable=True)
    payment_status = Column(String, nullable=True)
    invoice_id = Column(String, nullable=True)
    
    # Метаданные
    lesson_type = Column(String, nullable=True)  # regular, trial, makeup, intensive
    subject = Column(String, nullable=True)
    grade_level = Column(String, nullable=True)
    
    # Флаги и маркеры
    is_trial = Column(Boolean, default=False)
    is_makeup = Column(Boolean, default=False)
    is_cancelled = Column(Boolean, default=False)
    requires_followup = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<LessonStats(lesson_id={self.lesson_id}, student_id={self.student_id}, date={self.date})>"

    def to_dict(self):
        return {
            'id': self.id,
            'lesson_id': self.lesson_id,
            'tutor_id': self.tutor_id,
            'student_id': self.student_id,
            'date': self.date.isoformat() if self.date else None,
            'duration_minutes': self.duration_minutes,
            'status': self.status,
            'completion_rate': self.completion_rate,
            'attendance_status': self.attendance_status,
            'tutor_rating': self.tutor_rating,
            'student_rating': self.student_rating,
            'difficulty_rating': self.difficulty_rating,
            'topics_covered': self.topics_covered,
            'student_questions': self.student_questions,
            'engagement_score': self.engagement_score,
            'is_trial': self.is_trial,
            'requires_followup': self.requires_followup
        }

    def calculate_overall_rating(self) -> float:
        """Calculate overall lesson rating"""
        ratings = []
        
        if self.tutor_rating:
            ratings.append(self.tutor_rating)
        if self.student_rating:
            ratings.append(self.student_rating)
        if self.parent_rating:
            ratings.append(self.parent_rating)
            
        if ratings:
            return sum(ratings) / len(ratings)
        return 0.0
    
    def get_success_indicators(self) -> dict:
        """Get success indicators for this lesson"""
        return {
            'on_time_start': self.punctuality_score and self.punctuality_score >= 4.0,
            'full_duration': self.duration_minutes >= self.planned_duration * 0.9,
            'high_engagement': self.engagement_score and self.engagement_score >= 4.0,
            'objectives_met': self.learning_objectives_met and len(self.learning_objectives_met or []) > 0,
            'positive_rating': self.calculate_overall_rating() >= 4.0,
            'no_technical_issues': not self.technical_issues or len(self.technical_issues or []) == 0
        }
    
    def get_performance_score(self) -> float:
        """Calculate lesson performance score (0-100)"""
        score = 0.0
        
        # Attendance and punctuality (20 points)
        if self.attendance_status == 'present':
            score += 15
            if self.punctuality_score and self.punctuality_score >= 4:
                score += 5
        
        # Duration completion (15 points)
        if self.duration_minutes and self.planned_duration:
            duration_ratio = min(self.duration_minutes / self.planned_duration, 1.0)
            score += duration_ratio * 15
        
        # Engagement and participation (25 points)
        if self.engagement_score:
            score += (self.engagement_score / 5.0) * 25
        
        # Learning objectives and completion (20 points)
        if self.completion_rate:
            score += self.completion_rate * 20
        
        # Ratings (20 points)
        overall_rating = self.calculate_overall_rating()
        if overall_rating > 0:
            score += (overall_rating / 5.0) * 20
            
        return min(score, 100.0)