# -*- coding: utf-8 -*-
"""
SQLAlchemy модели для Lesson Service.
Модели урока, расписания, посещаемости, мигрированные из монолитной архитектуры.
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text, 
    Enum as SAEnum, Boolean, func, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# Enums из оригинального кода
class TopicMastery(enum.Enum):
    """Уровень освоения темы урока."""
    NOT_LEARNED = "not_learned"
    LEARNED = "learned"
    MASTERED = "mastered"


class AttendanceStatus(enum.Enum):
    """Статус посещения урока."""
    ATTENDED = "attended"
    EXCUSED_ABSENCE = "excused_absence"
    UNEXCUSED_ABSENCE = "unexcused_absence"
    RESCHEDULED = "rescheduled"


class LessonStatus(enum.Enum):
    """Статус проведения урока."""
    NOT_CONDUCTED = "not_conducted"  # Урок не проведен (по умолчанию для будущих уроков)
    CONDUCTED = "conducted"          # Урок проведен


class ScheduleRecurrenceType(enum.Enum):
    """Тип повторения в расписании."""
    NONE = "none"          # Разовый урок
    WEEKLY = "weekly"      # Еженедельно
    BIWEEKLY = "biweekly"  # Раз в две недели
    MONTHLY = "monthly"    # Ежемесячно
    CUSTOM = "custom"      # Пользовательский интервал


class Lesson(Base):
    """
    Модель урока, мигрированная из монолитной архитектуры.
    Расширена дополнительными полями для микросервисной архитектуры.
    """
    __tablename__ = 'lessons'
    
    # Основные поля
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(Integer, default=60, nullable=False)
    
    # Навыки и прогресс
    skills_developed = Column(Text, nullable=True)
    mastery_level = Column(SAEnum(TopicMastery), default=TopicMastery.NOT_LEARNED)
    mastery_comment = Column(Text, nullable=True)
    
    # Посещаемость и статус
    is_attended = Column(Boolean, default=False, nullable=False)  # Для обратной совместимости
    attendance_status = Column(SAEnum(AttendanceStatus), default=AttendanceStatus.ATTENDED, nullable=False)
    lesson_status = Column(SAEnum(LessonStatus), default=LessonStatus.NOT_CONDUCTED, nullable=False)
    
    # Перенос урока
    original_date = Column(DateTime, nullable=True)  # Оригинальная дата при переносе
    is_rescheduled = Column(Boolean, default=False, nullable=False)
    reschedule_reason = Column(Text, nullable=True)
    
    # Связи с пользователями (внешние ключи для User Service)
    student_id = Column(Integer, nullable=False, index=True)  # ID из User Service
    tutor_id = Column(Integer, nullable=True, index=True)     # ID репетитора
    
    # Связь с расписанием
    schedule_id = Column(Integer, ForeignKey('schedules.id'), nullable=True)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, nullable=True)  # ID пользователя, создавшего урок
    
    # Дополнительные поля для микросервиса
    notes = Column(Text, nullable=True)  # Заметки к уроку
    homework_assigned = Column(Boolean, default=False)  # Назначено ли ДЗ
    room_url = Column(String, nullable=True)  # Ссылка на онлайн-комнату
    materials_used = Column(Text, nullable=True)  # JSON список используемых материалов
    
    # Внешние события
    reminder_sent = Column(Boolean, default=False)  # Отправлено ли напоминание
    notification_sent = Column(Boolean, default=False)  # Отправлено ли уведомление
    
    # Связи
    schedule = relationship("Schedule", back_populates="lessons")
    
    # Индексы для оптимизации
    __table_args__ = (
        Index('idx_student_date', 'student_id', 'date'),
        Index('idx_tutor_date', 'tutor_id', 'date'),
        Index('idx_date_status', 'date', 'lesson_status'),
        Index('idx_attendance_status', 'attendance_status'),
    )
    
    def __repr__(self):
        return f"<Lesson(id={self.id}, topic='{self.topic}', date={self.date}, student_id={self.student_id})>"


class Schedule(Base):
    """
    Модель расписания для автоматического создания уроков.
    Поддерживает различные типы повторений.
    """
    __tablename__ = 'schedules'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Связи с пользователями
    student_id = Column(Integer, nullable=False, index=True)
    tutor_id = Column(Integer, nullable=False, index=True)
    
    # Настройки повторения
    recurrence_type = Column(SAEnum(ScheduleRecurrenceType), default=ScheduleRecurrenceType.WEEKLY)
    interval_days = Column(Integer, default=7)  # Интервал в днях для CUSTOM типа
    
    # Время и длительность
    start_time = Column(DateTime, nullable=False)  # Время начала уроков
    duration_minutes = Column(Integer, default=60)
    
    # Период действия расписания
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=True)  # NULL = бессрочно
    
    # Дни недели для повторения (JSON array: [1,3,5] для пн,ср,пт)
    weekdays = Column(String, nullable=True)  # JSON строка с днями недели
    
    # Статус
    is_active = Column(Boolean, default=True)
    
    # Настройки по умолчанию для создаваемых уроков
    default_topic_template = Column(String, nullable=True)  # Шаблон темы: "Урок {lesson_number}"
    default_room_url = Column(String, nullable=True)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, nullable=False)
    
    # Статистика
    lessons_created = Column(Integer, default=0)  # Сколько уроков создано по этому расписанию
    last_lesson_created = Column(DateTime, nullable=True)  # Дата последнего созданного урока
    
    # Связи
    lessons = relationship("Lesson", back_populates="schedule", cascade="all, delete-orphan")
    
    # Индексы
    __table_args__ = (
        Index('idx_student_tutor', 'student_id', 'tutor_id'),
        Index('idx_active_valid', 'is_active', 'valid_from', 'valid_until'),
    )
    
    def __repr__(self):
        return f"<Schedule(id={self.id}, name='{self.name}', student_id={self.student_id})>"


class LessonAttendance(Base):
    """
    Модель для детальной информации о посещаемости.
    Расширяет базовую информацию в Lesson.
    """
    __tablename__ = 'lesson_attendance'
    
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=False, unique=True)
    
    # Детали посещаемости
    attendance_status = Column(SAEnum(AttendanceStatus), nullable=False)
    check_in_time = Column(DateTime, nullable=True)  # Время отметки прихода
    check_out_time = Column(DateTime, nullable=True)  # Время ухода
    actual_duration_minutes = Column(Integer, nullable=True)  # Фактическая длительность
    
    # Причины отсутствия
    absence_reason = Column(Text, nullable=True)
    is_excused = Column(Boolean, default=False)
    
    # Оценка урока студентом
    student_rating = Column(Integer, nullable=True)  # 1-5
    student_feedback = Column(Text, nullable=True)
    
    # Оценка урока преподавателем
    tutor_rating = Column(Integer, nullable=True)  # 1-5
    tutor_notes = Column(Text, nullable=True)
    
    # Метаданные
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    recorded_by = Column(Integer, nullable=False)  # ID того, кто отметил посещаемость
    
    def __repr__(self):
        return f"<LessonAttendance(id={self.id}, lesson_id={self.lesson_id}, status={self.attendance_status})>"


class LessonCancellation(Base):
    """
    Модель для хранения информации об отменах и переносах уроков.
    Ведет историю изменений расписания.
    """
    __tablename__ = 'lesson_cancellations'
    
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=False)
    
    # Тип изменения
    action_type = Column(String, nullable=False)  # 'cancelled', 'rescheduled'
    
    # Исходные данные
    original_date = Column(DateTime, nullable=False)
    original_topic = Column(String, nullable=True)
    
    # Новые данные (для переноса)
    new_date = Column(DateTime, nullable=True)
    new_topic = Column(String, nullable=True)
    
    # Причина и детали
    reason = Column(Text, nullable=False)
    initiated_by = Column(Integer, nullable=False)  # ID пользователя, инициировавшего изменение
    approved_by = Column(Integer, nullable=True)    # ID одобрившего (если требуется одобрение)
    
    # Уведомления
    student_notified = Column(Boolean, default=False)
    tutor_notified = Column(Boolean, default=False)
    parent_notified = Column(Boolean, default=False)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<LessonCancellation(id={self.id}, lesson_id={self.lesson_id}, action={self.action_type})>"