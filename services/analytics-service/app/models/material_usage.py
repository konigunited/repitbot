from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class MaterialUsage(Base):
    """Material usage analytics and engagement metrics"""
    __tablename__ = "material_usage"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    material_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=True)
    
    # Основная информация о материале
    material_type = Column(String, nullable=False)  # video, pdf, quiz, interactive, etc.
    material_title = Column(String, nullable=True)
    material_category = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    difficulty_level = Column(String, nullable=True)
    
    # Данные доступа
    access_date = Column(DateTime, nullable=False, index=True)
    first_access = Column(Boolean, default=False)
    access_method = Column(String, nullable=True)  # direct, lesson, homework, search
    referrer_type = Column(String, nullable=True)  # lesson, tutor, parent, self
    
    # Метрики использования
    view_duration = Column(Integer, nullable=True)  # в секундах
    total_duration = Column(Integer, nullable=True)  # общая длительность материала
    completion_percentage = Column(Float, default=0.0)
    is_completed = Column(Boolean, default=False)
    
    # Активность и взаимодействие
    interactions_count = Column(Integer, default=0)  # клики, скроллы, etc.
    pause_count = Column(Integer, default=0)
    rewind_count = Column(Integer, default=0)
    fast_forward_count = Column(Integer, default=0)
    bookmark_added = Column(Boolean, default=False)
    
    # Для видео материалов
    video_segments_watched = Column(JSON, nullable=True)  # какие сегменты просмотрены
    video_quality = Column(String, nullable=True)  # 720p, 1080p, etc.
    playback_speed = Column(Float, default=1.0)
    
    # Для текстовых материалов
    pages_viewed = Column(Integer, nullable=True)
    total_pages = Column(Integer, nullable=True)
    reading_speed = Column(Float, nullable=True)  # страниц в минуту
    
    # Для интерактивных материалов
    quiz_attempts = Column(Integer, default=0)
    quiz_score = Column(Float, nullable=True)
    interactive_elements_used = Column(JSON, nullable=True)
    
    # Оценки и фидбек
    user_rating = Column(Float, nullable=True)  # 1-5
    difficulty_rating = Column(Float, nullable=True)  # насколько сложным показался
    usefulness_rating = Column(Float, nullable=True)
    would_recommend = Column(Boolean, nullable=True)
    
    # Контекст использования
    device_type = Column(String, nullable=True)
    browser = Column(String, nullable=True)
    screen_size = Column(String, nullable=True)
    connection_speed = Column(String, nullable=True)
    
    # Местоположение
    country = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    access_location = Column(String, nullable=True)  # home, school, library, etc.
    
    # Временные паттерны
    hour_of_day = Column(Integer, nullable=True)
    day_of_week = Column(Integer, nullable=True)
    is_weekend = Column(Boolean, default=False)
    
    # Прогресс и обучение
    prerequisite_completed = Column(Boolean, nullable=True)
    learning_path_position = Column(Integer, nullable=True)
    related_materials_accessed = Column(JSON, nullable=True)
    
    # Результативность
    post_material_performance = Column(Float, nullable=True)  # улучшение после изучения
    knowledge_retention_score = Column(Float, nullable=True)
    follow_up_materials_accessed = Column(Integer, default=0)
    
    # Сотрудничество
    shared_with_others = Column(Boolean, default=False)
    discussed_with_tutor = Column(Boolean, default=False)
    parent_notified = Column(Boolean, default=False)
    
    # Проблемы и поддержка
    technical_issues = Column(JSON, nullable=True)
    help_requests = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    loading_time = Column(Float, nullable=True)  # время загрузки в секундах
    
    # Персонализация
    adaptation_level = Column(Float, nullable=True)  # насколько материал адаптирован
    ai_recommendations_followed = Column(Integer, default=0)
    custom_settings_used = Column(JSON, nullable=True)
    
    # Мотивация и вовлеченность
    engagement_score = Column(Float, nullable=True)  # calculated engagement metric
    attention_span = Column(Integer, nullable=True)  # как долго активно взаимодействовал
    distraction_indicators = Column(JSON, nullable=True)
    
    # Социальные аспекты
    peer_comparisons_viewed = Column(Boolean, default=False)
    group_activity_participation = Column(Boolean, default=False)
    competition_elements_used = Column(Boolean, default=False)
    
    # Повторные обращения
    revisit_count = Column(Integer, default=0)
    last_revisit_date = Column(DateTime, nullable=True)
    total_time_spent = Column(Integer, default=0)  # суммарное время всех сессий
    
    # Результаты и достижения
    badges_earned = Column(JSON, nullable=True)
    milestones_reached = Column(JSON, nullable=True)
    certificates_obtained = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<MaterialUsage(material_id={self.material_id}, user_id={self.user_id}, access_date={self.access_date})>"

    def to_dict(self):
        return {
            'id': self.id,
            'material_id': self.material_id,
            'user_id': self.user_id,
            'material_type': self.material_type,
            'material_title': self.material_title,
            'access_date': self.access_date.isoformat() if self.access_date else None,
            'view_duration': self.view_duration,
            'completion_percentage': self.completion_percentage,
            'is_completed': self.is_completed,
            'user_rating': self.user_rating,
            'engagement_score': self.engagement_score,
            'revisit_count': self.revisit_count
        }

    def calculate_engagement_score(self) -> float:
        """Calculate engagement score based on usage patterns"""
        score = 0.0
        
        # Completion factor (30%)
        if self.completion_percentage:
            score += self.completion_percentage * 0.3
        
        # Interaction factor (25%)
        if self.interactions_count:
            # Normalize interactions (assume 50 interactions = max score)
            normalized_interactions = min(self.interactions_count / 50, 1.0)
            score += normalized_interactions * 25
        
        # Duration factor (20%)
        if self.view_duration and self.total_duration:
            duration_ratio = min(self.view_duration / self.total_duration, 1.0)
            score += duration_ratio * 20
        
        # Rating factor (15%)
        if self.user_rating:
            score += (self.user_rating / 5.0) * 15
        
        # Revisit factor (10%)
        if self.revisit_count:
            # More revisits indicate higher engagement
            revisit_score = min(self.revisit_count / 5, 1.0)  # 5 revisits = max score
            score += revisit_score * 10
            
        return min(score, 100.0)

    def get_usage_pattern(self) -> str:
        """Determine usage pattern category"""
        if self.completion_percentage >= 90 and self.revisit_count > 2:
            return 'thorough_learner'
        elif self.completion_percentage >= 70 and self.interactions_count > 20:
            return 'active_learner'
        elif self.completion_percentage < 30 and self.view_duration < 300:
            return 'quick_browser'
        elif self.revisit_count > 0:
            return 'gradual_learner'
        else:
            return 'casual_viewer'

    def get_learning_effectiveness(self) -> dict:
        """Calculate learning effectiveness metrics"""
        effectiveness = {
            'completion_rate': self.completion_percentage,
            'engagement_level': self.calculate_engagement_score(),
            'persistence': self.revisit_count > 0,
            'depth_of_study': self.interactions_count / max(self.view_duration or 1, 1),
            'satisfaction': self.user_rating or 0
        }
        
        # Overall effectiveness score
        weights = {
            'completion_rate': 0.3,
            'engagement_level': 0.25,
            'persistence': 0.2,
            'depth_of_study': 0.15,
            'satisfaction': 0.1
        }
        
        overall_score = 0
        for metric, value in effectiveness.items():
            if metric in weights and value:
                if metric == 'persistence':
                    normalized_value = 100 if value else 0
                elif metric == 'depth_of_study':
                    normalized_value = min(value * 10, 100)  # normalize interaction rate
                elif metric == 'satisfaction':
                    normalized_value = (value / 5.0) * 100
                else:
                    normalized_value = value
                    
                overall_score += weights[metric] * normalized_value
        
        effectiveness['overall_score'] = overall_score
        return effectiveness

    def identify_improvement_areas(self) -> list:
        """Identify areas where material usage could be improved"""
        improvements = []
        
        if self.completion_percentage < 50:
            improvements.append('low_completion_rate')
        
        if self.interactions_count < 5:
            improvements.append('low_interaction')
            
        if self.user_rating and self.user_rating < 3:
            improvements.append('low_satisfaction')
            
        if self.technical_issues and len(self.technical_issues) > 0:
            improvements.append('technical_barriers')
            
        if self.help_requests > 3:
            improvements.append('comprehension_difficulties')
            
        if self.error_count > 5:
            improvements.append('usability_issues')
            
        return improvements