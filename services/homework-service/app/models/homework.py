# -*- coding: utf-8 -*-
"""
SQLAlchemy модели для Homework Service.
Модели домашних заданий, файлов, проверок, мигрированные из монолитной архитектуры.
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text, 
    Enum as SAEnum, Boolean, func, Index, Float, LargeBinary
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# Enums из оригинального кода
class HomeworkStatus(enum.Enum):
    """Статус домашнего задания."""
    PENDING = "pending"      # Ожидает выполнения
    SUBMITTED = "submitted"  # Сдано на проверку
    CHECKED = "checked"      # Проверено


class FileType(enum.Enum):
    """Тип файла."""
    IMAGE = "image"          # Изображение
    DOCUMENT = "document"    # Документ
    VIDEO = "video"          # Видео
    AUDIO = "audio"          # Аудио
    OTHER = "other"          # Другое


class SubmissionType(enum.Enum):
    """Тип отправки домашнего задания."""
    TEXT = "text"            # Текстовый ответ
    FILE = "file"            # Файлы
    MIXED = "mixed"          # Текст + файлы


class CheckStatus(enum.Enum):
    """Статус проверки."""
    PASSED = "passed"        # Зачтено
    FAILED = "failed"        # Незачтено
    NEEDS_REVISION = "needs_revision"  # Требует доработки


class Homework(Base):
    """
    Модель домашнего задания, мигрированная из монолитной архитектуры.
    Расширена дополнительными полями для микросервисной архитектуры.
    """
    __tablename__ = 'homework'
    
    # Основные поля
    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=False)
    status = Column(SAEnum(HomeworkStatus), default=HomeworkStatus.PENDING)
    deadline = Column(DateTime, nullable=True)
    
    # Связи с внешними сервисами
    lesson_id = Column(Integer, nullable=False, index=True)  # ID из Lesson Service
    student_id = Column(Integer, nullable=False, index=True)  # ID из User Service
    tutor_id = Column(Integer, nullable=False, index=True)    # ID репетитора
    
    # Файлы от репетитора (задание)
    file_link = Column(String, nullable=True)  # Для обратной совместимости
    photo_file_ids = Column(Text, nullable=True)  # JSON список file_id (legacy)
    
    # Ответ студента
    submission_text = Column(Text, nullable=True)  # Текстовый ответ
    submission_photo_file_ids = Column(Text, nullable=True)  # JSON file_id (legacy)
    submission_type = Column(SAEnum(SubmissionType), nullable=True)
    
    # Проверка
    checked_at = Column(DateTime, nullable=True)
    check_status = Column(SAEnum(CheckStatus), nullable=True)
    feedback = Column(Text, nullable=True)  # Комментарий репетитора
    grade = Column(Float, nullable=True)  # Оценка (1-5)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    submitted_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=False)  # ID создавшего
    checked_by = Column(Integer, nullable=True)   # ID проверившего
    
    # Дополнительные поля для микросервиса
    max_attempts = Column(Integer, default=1)  # Максимальное количество попыток
    current_attempt = Column(Integer, default=1)  # Текущая попытка
    auto_check = Column(Boolean, default=False)  # Автоматическая проверка
    weight = Column(Float, default=1.0)  # Вес задания в общей оценке
    
    # Уведомления
    reminder_sent = Column(Boolean, default=False)
    deadline_notification_sent = Column(Boolean, default=False)
    
    # Связи
    files = relationship("HomeworkFile", back_populates="homework", cascade="all, delete-orphan")
    submissions = relationship("HomeworkSubmission", back_populates="homework", cascade="all, delete-orphan")
    
    # Индексы для оптимизации
    __table_args__ = (
        Index('idx_homework_lesson', 'lesson_id'),
        Index('idx_homework_student', 'student_id'),
        Index('idx_homework_tutor', 'tutor_id'),
        Index('idx_homework_status', 'status'),
        Index('idx_homework_deadline', 'deadline'),
        Index('idx_homework_student_status', 'student_id', 'status'),
    )
    
    def __repr__(self):
        return f"<Homework(id={self.id}, lesson_id={self.lesson_id}, status={self.status})>"


class HomeworkFile(Base):
    """
    Модель файлов домашнего задания.
    Хранит метаданные о файлах, загруженных репетитором или студентом.
    """
    __tablename__ = 'homework_files'
    
    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey('homework.id'), nullable=False)
    
    # Метаданные файла
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # Путь к файлу в файловой системе
    file_size = Column(Integer, nullable=False)  # Размер в байтах
    file_type = Column(SAEnum(FileType), nullable=False)
    mime_type = Column(String, nullable=False)
    
    # Telegram файлы (для обратной совместимости)
    telegram_file_id = Column(String, nullable=True)
    telegram_file_unique_id = Column(String, nullable=True)
    
    # Кто загрузил
    uploaded_by = Column(Integer, nullable=False)  # ID пользователя
    upload_source = Column(String, default="api")  # "api", "telegram", "web"
    
    # Обработка файла
    is_processed = Column(Boolean, default=False)
    thumbnail_path = Column(String, nullable=True)  # Путь к миниатюре
    compressed_path = Column(String, nullable=True)  # Путь к сжатой версии
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    downloaded_count = Column(Integer, default=0)  # Счетчик скачиваний
    
    # Связи
    homework = relationship("Homework", back_populates="files")
    
    # Индексы
    __table_args__ = (
        Index('idx_file_homework', 'homework_id'),
        Index('idx_file_telegram_id', 'telegram_file_id'),
        Index('idx_file_type', 'file_type'),
    )
    
    def __repr__(self):
        return f"<HomeworkFile(id={self.id}, filename='{self.filename}', homework_id={self.homework_id})>"


class HomeworkSubmission(Base):
    """
    Модель отправки домашнего задания студентом.
    Поддерживает множественные попытки сдачи.
    """
    __tablename__ = 'homework_submissions'
    
    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey('homework.id'), nullable=False)
    
    # Информация о попытке
    attempt_number = Column(Integer, nullable=False, default=1)
    submission_type = Column(SAEnum(SubmissionType), nullable=False)
    
    # Содержимое отправки
    text_content = Column(Text, nullable=True)
    
    # Метаданные
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_by = Column(Integer, nullable=False)  # ID студента
    
    # IP и User-Agent для безопасности
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Статус обработки
    is_processed = Column(Boolean, default=False)
    processing_error = Column(Text, nullable=True)
    
    # Связи
    homework = relationship("Homework", back_populates="submissions")
    files = relationship("SubmissionFile", back_populates="submission", cascade="all, delete-orphan")
    
    # Индексы
    __table_args__ = (
        Index('idx_submission_homework', 'homework_id'),
        Index('idx_submission_attempt', 'homework_id', 'attempt_number'),
        Index('idx_submission_student', 'submitted_by'),
    )
    
    def __repr__(self):
        return f"<HomeworkSubmission(id={self.id}, homework_id={self.homework_id}, attempt={self.attempt_number})>"


class SubmissionFile(Base):
    """
    Модель файлов в отправке студента.
    Связана с конкретной попыткой сдачи.
    """
    __tablename__ = 'submission_files'
    
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey('homework_submissions.id'), nullable=False)
    
    # Метаданные файла (аналогично HomeworkFile)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(SAEnum(FileType), nullable=False)
    mime_type = Column(String, nullable=False)
    
    # Telegram файлы
    telegram_file_id = Column(String, nullable=True)
    telegram_file_unique_id = Column(String, nullable=True)
    
    # Обработка
    is_processed = Column(Boolean, default=False)
    thumbnail_path = Column(String, nullable=True)
    compressed_path = Column(String, nullable=True)
    
    # Метаданные
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    submission = relationship("HomeworkSubmission", back_populates="files")
    
    def __repr__(self):
        return f"<SubmissionFile(id={self.id}, filename='{self.filename}', submission_id={self.submission_id})>"


class HomeworkTemplate(Base):
    """
    Модель шаблонов домашних заданий.
    Позволяет создавать типовые задания.
    """
    __tablename__ = 'homework_templates'
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=True)  # Категория задания
    difficulty_level = Column(Integer, default=1)  # 1-5
    
    # Настройки по умолчанию
    default_deadline_hours = Column(Integer, default=168)  # 7 дней
    default_max_attempts = Column(Integer, default=1)
    default_weight = Column(Float, default=1.0)
    
    # Автопроверка
    auto_check_enabled = Column(Boolean, default=False)
    auto_check_criteria = Column(Text, nullable=True)  # JSON критерии
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, nullable=False)
    
    # Статистика использования
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<HomeworkTemplate(id={self.id}, name='{self.name}')>"


class HomeworkComment(Base):
    """
    Модель комментариев к домашнему заданию.
    Поддерживает обратную связь между студентом и репетитором.
    """
    __tablename__ = 'homework_comments'
    
    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey('homework.id'), nullable=False)
    
    # Содержимое комментария
    content = Column(Text, nullable=False)
    comment_type = Column(String, default="general")  # "general", "feedback", "question"
    
    # Автор
    author_id = Column(Integer, nullable=False)  # ID автора
    author_role = Column(String, nullable=False)  # "student", "tutor"
    
    # Привязка к попытке (опционально)
    submission_id = Column(Integer, ForeignKey('homework_submissions.id'), nullable=True)
    
    # Статус
    is_read = Column(Boolean, default=False)
    is_important = Column(Boolean, default=False)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Связи
    homework = relationship("Homework", foreign_keys=[homework_id])
    submission = relationship("HomeworkSubmission", foreign_keys=[submission_id])
    
    # Индексы
    __table_args__ = (
        Index('idx_comment_homework', 'homework_id'),
        Index('idx_comment_author', 'author_id'),
        Index('idx_comment_unread', 'is_read'),
    )
    
    def __repr__(self):
        return f"<HomeworkComment(id={self.id}, homework_id={self.homework_id}, author_role='{self.author_role}')>"