# -*- coding: utf-8 -*-
import os
import enum
from datetime import datetime
from sqlalchemy import (create_engine, Column, Integer, String, ForeignKey,
                        DateTime, Text, Enum as SAEnum, Boolean, func as sql_func)
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func


# Получаем абсолютный путь к директории, где находится этот файл
basedir = os.path.abspath(os.path.dirname(__file__))
# Создаем путь к файлу базы данных
DATABASE_URL = "sqlite:///" + os.path.join(basedir, "..", "repitbot.db") # Go up one level

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Enums ---
class UserRole(enum.Enum):
    TUTOR = "tutor"
    STUDENT = "student"
    PARENT = "parent"

class HomeworkStatus(enum.Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    CHECKED = "checked"

class TopicMastery(enum.Enum):
    NOT_LEARNED = "not_learned"
    LEARNED = "learned"
    MASTERED = "mastered"

# --- Models ---
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=True)
    username = Column(String, unique=True, nullable=True)
    full_name = Column(String, nullable=False)
    role = Column(SAEnum(UserRole), nullable=False)
    access_code = Column(String, unique=True, nullable=False)
    points = Column(Integer, default=0) # <-- Новое поле для баллов
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи для ученика
    student_lessons = relationship("Lesson", back_populates="student", cascade="all, delete-orphan", foreign_keys="[Lesson.student_id]")
    payments = relationship("Payment", back_populates="student", cascade="all, delete-orphan", foreign_keys="[Payment.student_id]")

    # --- Связи Родитель <-> Ученик ---
    parent_id = Column(Integer, ForeignKey('users.id'))
    parent = relationship("User", remote_side=[id], foreign_keys=[parent_id], back_populates="children")
    children = relationship("User", back_populates="parent")


class Lesson(Base):
    __tablename__ = 'lessons'
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    skills_developed = Column(Text, nullable=True)
    mastery_level = Column(SAEnum(TopicMastery), default=TopicMastery.NOT_LEARNED)
    mastery_comment = Column(Text, nullable=True)
    is_attended = Column(Boolean, default=False, nullable=False) # <-- Новое поле
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    student = relationship("User", back_populates="student_lessons")
    homeworks = relationship("Homework", back_populates="lesson", cascade="all, delete-orphan")


class Homework(Base):
    __tablename__ = 'homeworks'
    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=False)
    file_link = Column(String, nullable=True)
    status = Column(SAEnum(HomeworkStatus), default=HomeworkStatus.PENDING)
    deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    checked_at = Column(DateTime, nullable=True) # <-- Новое поле для с��атистики

    # Связи
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=False)
    lesson = relationship("Lesson", back_populates="homeworks")

# Новая модель для оплат
class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True, index=True)
    lessons_paid = Column(Integer, nullable=False)
    payment_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    student = relationship("User", back_populates="payments")


# Новая модель для материалов
class Material(Base):
    __tablename__ = 'materials'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    link = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_by_telegram_id(telegram_id: int):
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    db.close()
    return user

def get_student_by_name(full_name: str):
    db = SessionLocal()
    user = db.query(User).filter(User.full_name == full_name, User.role == UserRole.STUDENT).first()
    db.close()
    return user

def get_all_users():
    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    return users

def get_all_students():
    db = SessionLocal()
    students = db.query(User).filter(User.role == UserRole.STUDENT).all()
    db.close()
    return students

def get_lesson_by_id(lesson_id: int):
    db = SessionLocal()
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    db.close()
    return lesson

def get_homework_by_id(hw_id: int):
    db = SessionLocal()
    hw = db.query(Homework).filter(Homework.id == hw_id).first()
    db.close()
    return hw

def get_user_by_id(user_id: int):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    return user

def get_lessons_for_student_by_month(student_id: int, year: int, month: int):
    """Возвращает все уроки для ученика за указанный год и месяц."""
    db = SessionLocal()
    lessons = db.query(Lesson).filter(
        Lesson.student_id == student_id,
        func.extract('year', Lesson.date) == year,
        func.extract('month', Lesson.date) == month
    ).order_by(Lesson.date).all()
    db.close()
    return lessons

def get_payments_for_student_by_month(student_id: int, year: int, month: int):
    """Возвращает все платежи для ученика за указанный год и месяц."""
    db = SessionLocal()
    payments = db.query(Payment).filter(
        Payment.student_id == student_id,
        func.extract('year', Payment.payment_date) == year,
        func.extract('month', Payment.payment_date) == month
    ).order_by(Payment.payment_date).all()
    db.close()
    return payments

def get_all_materials():
    """Возвращает все материалы из библиотеки."""
    db = SessionLocal()
    materials = db.query(Material).order_by(Material.created_at.desc()).all()
    db.close()
    return materials

def get_material_by_id(material_id: int):
    """Возвращает материал по его ID."""
    db = SessionLocal()
    material = db.query(Material).filter(Material.id == material_id).first()
    db.close()
    return material

def delete_material_by_id(material_id: int):
    """Удаляет материал по его ID."""
    db = SessionLocal()
    material = db.query(Material).filter(Material.id == material_id).first()
    if material:
        db.delete(material)
        db.commit()
    db.close()

def get_student_balance(student_id: int):
    """Рассчитывает баланс занятий для ученика."""
    db = SessionLocal()
    try:
        total_paid = db.query(sql_func.sum(Payment.lessons_paid)).filter(Payment.student_id == student_id).scalar() or 0
        total_attended = db.query(Lesson).filter(Lesson.student_id == student_id, Lesson.is_attended == True).count()
        return total_paid - total_attended
    finally:
        db.close()

# --- Функции для дашборда ---
def get_dashboard_stats():
    """Собирает статистику для дашборда репетитора."""
    db = SessionLocal()
    try:
        now = datetime.now()
        year, month = now.year, now.month

        student_count = db.query(User).filter(User.role == UserRole.STUDENT).count()
        
        lessons_this_month = db.query(Lesson).filter(
            Lesson.is_attended == True,
            func.extract('year', Lesson.date) == year,
            func.extract('month', Lesson.date) == month
        ).count()

        checked_hw_this_month = db.query(Homework).filter(
            Homework.status == HomeworkStatus.CHECKED,
            func.extract('year', Homework.checked_at) == year,
            func.extract('month', Homework.checked_at) == month
        ).count()

        payments_sum_this_month = db.query(sql_func.sum(Payment.lessons_paid)).filter(
            func.extract('year', Payment.payment_date) == year,
            func.extract('month', Payment.payment_date) == month
        ).scalar() or 0

        return {
            "student_count": student_count,
            "lessons_this_month": lessons__this_month,
            "checked_hw_this_month": checked_hw_this_month,
            "payments_sum_this_month": payments_sum_this_month
        }
    finally:
        db.close()
