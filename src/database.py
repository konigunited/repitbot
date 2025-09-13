# -*- coding: utf-8 -*-
import os
import enum
from datetime import datetime, timedelta
from .timezone_utils import now as tz_now
from sqlalchemy import (create_engine, Column, Integer, String, ForeignKey,
                        DateTime, Text, Enum as SAEnum, Boolean, func as sql_func)
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, joinedload
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

class AttendanceStatus(enum.Enum):
    SCHEDULED = "scheduled"  # Урок запланирован (по умолчанию)
    ATTENDED = "attended"
    EXCUSED_ABSENCE = "excused_absence"
    UNEXCUSED_ABSENCE = "unexcused_absence"
    RESCHEDULED = "rescheduled"

class LessonStatus(enum.Enum):
    NOT_CONDUCTED = "not_conducted"  # Урок не проведен (по умолчанию для будущих уроков)
    CONDUCTED = "conducted"          # Урок проведен

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
    streak_days = Column(Integer, default=0) # Дни подряд с уроками
    last_lesson_date = Column(DateTime, nullable=True) # Дата последнего урока для streak
    total_study_hours = Column(Integer, default=0) # Общее время изучения (в минутах)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи для ученика
    student_lessons = relationship("Lesson", back_populates="student", cascade="all, delete-orphan", foreign_keys="[Lesson.student_id]")
    payments = relationship("Payment", back_populates="student", cascade="all, delete-orphan", foreign_keys="[Payment.student_id]")

    # --- Связи Родитель <-> Ученик ---
    parent_id = Column(Integer, ForeignKey('users.id'))
    second_parent_id = Column(Integer, ForeignKey('users.id'))
    
    parent = relationship("User", remote_side=[id], foreign_keys=[parent_id], back_populates="children")
    second_parent = relationship("User", remote_side=[id], foreign_keys=[second_parent_id])
    children = relationship("User", back_populates="parent", foreign_keys=[parent_id])


class Lesson(Base):
    __tablename__ = 'lessons'
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    skills_developed = Column(Text, nullable=True)
    mastery_level = Column(SAEnum(TopicMastery), default=TopicMastery.NOT_LEARNED)
    mastery_comment = Column(Text, nullable=True)
    is_attended = Column(Boolean, default=False, nullable=False) # <-- Старое поле для совместимости
    attendance_status = Column(SAEnum(AttendanceStatus), default=AttendanceStatus.ATTENDED, nullable=False) # <-- Новое поле для статуса посещения
    lesson_status = Column(SAEnum(LessonStatus), default=LessonStatus.NOT_CONDUCTED, nullable=False) # <-- Статус проведения урока
    original_date = Column(DateTime, nullable=True) # <-- Оригинальная дата урока (если был перенос)
    is_rescheduled = Column(Boolean, default=False, nullable=False) # <-- Флаг переноса
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
    photo_file_ids = Column(Text, nullable=True)  # JSON список file_id фотографий от репетитора
    submission_text = Column(Text, nullable=True)  # Текст ответа ученика
    submission_photo_file_ids = Column(Text, nullable=True)  # JSON список file_id фото от ученика
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
    link = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    grade = Column(Integer, nullable=False, default=5)  # Класс 2-9
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Модель для достижений студентов
class WeeklySchedule(Base):
    __tablename__ = 'weekly_schedules'
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    tutor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    monday = Column(Boolean, default=False)
    tuesday = Column(Boolean, default=False)
    wednesday = Column(Boolean, default=False)
    thursday = Column(Boolean, default=False)
    friday = Column(Boolean, default=False)
    saturday = Column(Boolean, default=False)
    sunday = Column(Boolean, default=False)
    monday_note = Column(Text, nullable=True)
    tuesday_note = Column(Text, nullable=True)
    wednesday_note = Column(Text, nullable=True)
    thursday_note = Column(Text, nullable=True)
    friday_note = Column(Text, nullable=True)
    saturday_note = Column(Text, nullable=True)
    sunday_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    student = relationship("User", foreign_keys=[student_id])
    tutor = relationship("User", foreign_keys=[tutor_id])

class Achievement(Base):
    __tablename__ = 'achievements'
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    achievement_type = Column(String, nullable=False)  # "first_lesson", "streak_7", "hw_master", etc.
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String, default="🏆")
    earned_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    student = relationship("User", foreign_keys=[student_id])

# Функции для работы с еженедельным расписанием
def get_weekly_schedule(student_id: int, tutor_id: int):
    """Возвращает еженедельное расписание для ученика и репетитора."""
    db = SessionLocal()
    schedule = db.query(WeeklySchedule).filter(
        WeeklySchedule.student_id == student_id,
        WeeklySchedule.tutor_id == tutor_id
    ).first()
    db.close()
    return schedule

def create_or_update_weekly_schedule(student_id: int, tutor_id: int, schedule_data: dict):
    """Создает или обновляет еженедельное расписание."""
    db = SessionLocal()
    try:
        existing_schedule = db.query(WeeklySchedule).filter(
            WeeklySchedule.student_id == student_id,
            WeeklySchedule.tutor_id == tutor_id
        ).first()

        if existing_schedule:
            # Обновляем существующее расписание
            for day, value in schedule_data.items():
                if hasattr(existing_schedule, day):
                    setattr(existing_schedule, day, value)
            existing_schedule.updated_at = tz_now()
        else:
            # Создаем новое расписание
            new_schedule = WeeklySchedule(
                student_id=student_id,
                tutor_id=tutor_id,
                **schedule_data
            )
            db.add(new_schedule)

        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Ошибка при сохранении расписания: {e}")
        return False
    finally:
        db.close()

def toggle_schedule_day(student_id: int, tutor_id: int, day_name: str):
    """Переключает день недели в расписании (включает/выключает)."""
    db = SessionLocal()
    try:
        schedule = db.query(WeeklySchedule).filter(
            WeeklySchedule.student_id == student_id,
            WeeklySchedule.tutor_id == tutor_id
        ).first()

        if not schedule:
            # Создаем новое расписание, если его нет
            schedule_data = {day_name: True}
            schedule = WeeklySchedule(
                student_id=student_id,
                tutor_id=tutor_id,
                **schedule_data
            )
            db.add(schedule)
        else:
            # Переключаем день
            current_value = getattr(schedule, day_name, False)
            setattr(schedule, day_name, not current_value)
            schedule.updated_at = tz_now()

        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Ошибка при переключении дня расписания: {e}")
        return False
    finally:
        db.close()

def get_schedule_days_text(schedule):
    """Возвращает текстовое представление дней расписания."""
    if not schedule:
        return "Нет регулярного расписания"

    days_ru = {
        'monday': 'Понедельник',
        'tuesday': 'Вторник',
        'wednesday': 'Среда',
        'thursday': 'Четверг',
        'friday': 'Пятница',
        'saturday': 'Суббота',
        'sunday': 'Воскресенье'
    }

    active_days = []
    for day_en, day_ru in days_ru.items():
        if getattr(schedule, day_en, False):
            active_days.append(day_ru)

    if not active_days:
        return "Нет активных дней"

    result = "Регулярные занятия: " + ", ".join(active_days)
    if schedule.preferred_time:
        result += f" в {schedule.preferred_time}"

    return result

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
    lesson = db.query(Lesson).options(joinedload(Lesson.homeworks), joinedload(Lesson.student)).filter(Lesson.id == lesson_id).first()
    db.close()
    return lesson

def get_homework_by_id(hw_id: int):
    db = SessionLocal()
    hw = db.query(Homework).options(joinedload(Homework.lesson)).filter(Homework.id == hw_id).first()
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
    materials = db.query(Material).order_by(Material.grade, Material.created_at.desc()).all()
    db.close()
    return materials

def get_materials_by_grade(grade: int):
    """Возвращает материалы для определённого класса."""
    db = SessionLocal()
    materials = db.query(Material).filter(Material.grade == grade).order_by(Material.created_at.desc()).all()
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

def get_all_parents():
    """Возвращает всех родителей с их детьми."""
    db = SessionLocal()
    # Используем joinedload для загрузки детей сразу
    parents = db.query(User).options(joinedload(User.children)).filter(User.role == UserRole.PARENT).all()
    # Принудительно загружаем все связанные данные пока сессия открыта
    for parent in parents:
        _ = parent.children  # Триггерим загрузку
    db.close()
    return parents

def get_user_by_id(user_id: int):
    """Возвращает пользователя по его ID."""
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    return user

def get_student_balance(student_id: int):
    """Рассчитывает баланс занятий для ученика."""
    db = SessionLocal()
    try:
        total_paid = db.query(sql_func.sum(Payment.lessons_paid)).filter(Payment.student_id == student_id).scalar() or 0
        # Считаем уроки, которые снимают с баланса: посещенные и неуважительные пропуски
        # Перенесенные уроки и уважительные пропуски НЕ снимают с баланса
        deducted_lessons = db.query(Lesson).filter(
            Lesson.student_id == student_id, 
            Lesson.attendance_status.in_([AttendanceStatus.ATTENDED, AttendanceStatus.UNEXCUSED_ABSENCE])
        ).count()
        return total_paid - deducted_lessons
    finally:
        db.close()

# --- Функции для дашборда ---
def get_student_achievements(student_id: int):
    """Получает все достижения студента."""
    db = SessionLocal()
    try:
        achievements = db.query(Achievement).filter(Achievement.student_id == student_id).order_by(Achievement.earned_at.desc()).all()
        return achievements
    finally:
        db.close()

def award_achievement(student_id: int, achievement_type: str, title: str, description: str = None, icon: str = "🏆"):
    """Награждает студента достижением, если у него его еще нет."""
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже такое достижение
        existing = db.query(Achievement).filter(
            Achievement.student_id == student_id,
            Achievement.achievement_type == achievement_type
        ).first()
        
        if not existing:
            new_achievement = Achievement(
                student_id=student_id,
                achievement_type=achievement_type,
                title=title,
                description=description,
                icon=icon
            )
            db.add(new_achievement)
            db.commit()
            return new_achievement
        return None
    finally:
        db.close()

def check_points_achievements(student_id: int):
    """Проверяет достижения по баллам."""
    db = SessionLocal()
    try:
        student = db.query(User).filter(User.id == student_id).first()
        if not student:
            return []
            
        new_achievements = []
        points = student.points
        
        # Проверяем различные уровни баллов
        achievements_data = [
            (50, "points_50", "Начинающий", "Первые 50 баллов!", "🌟"),
            (100, "points_100", "Активист", "100 баллов набрано!", "⭐"),
            (250, "points_250", "Звезда", "250 баллов - отличный результат!", "🌠"),
            (500, "points_500", "Суперзвезда", "500 баллов - невероятно!", "💫"),
            (1000, "points_1000", "Легенда", "1000 баллов - вы легенда!", "🏆"),
        ]
        
        for threshold, ach_type, title, desc, icon in achievements_data:
            if points >= threshold:
                new_ach = award_achievement(student_id, ach_type, title, desc, icon)
                if new_ach:
                    new_achievements.append(new_ach)
        
        return new_achievements
    finally:
        db.close()

def update_study_streak(student_id: int):
    """Обновляет streak дни для студента после урока."""
    db = SessionLocal()
    try:
        student = db.query(User).filter(User.id == student_id).first()
        if not student:
            return []
            
        today = tz_now().date()
        
        if student.last_lesson_date:
            last_date = student.last_lesson_date.date()
            days_diff = (today - last_date).days
            
            if days_diff == 1:  # Урок вчера - продолжаем streak
                student.streak_days += 1
            elif days_diff == 0:  # Урок сегодня - не увеличиваем
                pass
            else:  # Пропуск - обнуляем streak
                student.streak_days = 1
        else:
            student.streak_days = 1
            
        student.last_lesson_date = tz_now().replace(tzinfo=None)
        db.commit()
        
        new_achievements = []
        # Проверяем достижения за streak
        if student.streak_days == 3:
            new_ach = award_achievement(student_id, "streak_3", "Трудяга", "3 дня подряд с уроками!", "🔥")
            if new_ach: new_achievements.append(new_ach)
        elif student.streak_days == 7:
            new_ach = award_achievement(student_id, "streak_7", "Неделя знаний", "7 дней подряд с уроками!", "⚡")
            if new_ach: new_achievements.append(new_ach)
        elif student.streak_days == 14:
            new_ach = award_achievement(student_id, "streak_14", "Две недели силы", "14 дней подряд с уроками!", "💪")
            if new_ach: new_achievements.append(new_ach)
        elif student.streak_days == 30:
            new_ach = award_achievement(student_id, "streak_30", "Месяц упорства", "30 дней подряд с уроками!", "👑")
            if new_ach: new_achievements.append(new_ach)
        
        return new_achievements
            
    finally:
        db.close()

def get_dashboard_stats():
    """Собирает статистику для дашборда репетитора."""
    db = SessionLocal()
    try:
        now = tz_now().replace(tzinfo=None)
        year, month = now.year, now.month

        student_count = db.query(User).filter(User.role == UserRole.STUDENT).count()
        
        lessons_this_month = db.query(Lesson).filter(
            Lesson.attendance_status == AttendanceStatus.ATTENDED,
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
            "lessons_this_month": lessons_this_month,
            "checked_hw_this_month": checked_hw_this_month,
            "payments_sum_this_month": payments_sum_this_month
        }
    finally:
        db.close()

def shift_lessons_after_cancellation(cancelled_lesson_id: int):
    """
    Новая логика переноса уроков при отмене:
    - Все следующие уроки сдвигаются на +1 позицию в цепочке
    - Создается новый урок-заглушка для отработки пропущенной темы (без даты)
    - Отмененный урок становится местом для отработки темы следующего урока
    """
    db = SessionLocal()
    try:
        # Получаем отмененный урок
        cancelled_lesson = db.query(Lesson).filter(Lesson.id == cancelled_lesson_id).first()
        if not cancelled_lesson:
            return False
        
        # Получаем все будущие уроки этого ученика (НЕ включая отмененный)
        future_lessons = db.query(Lesson).filter(
            Lesson.student_id == cancelled_lesson.student_id,
            Lesson.date > cancelled_lesson.date
        ).order_by(Lesson.date.asc()).all()
        
        if not future_lessons:
            # Если нет будущих уроков, создаем урок-заглушку для отработки
            # Используем дату далеко в будущем как маркер "не запланированного" урока
            from datetime import datetime, timedelta
            far_future_date = tz_now() + timedelta(days=3650)  # 10 лет вперед
            
            makeup_lesson = Lesson(
                student_id=cancelled_lesson.student_id,
                topic=cancelled_lesson.topic + " (отработка)",
                date=far_future_date,
                attendance_status=AttendanceStatus.ATTENDED,  # По умолчанию
                mastery_level=TopicMastery.NOT_LEARNED
            )
            db.add(makeup_lesson)
            db.commit()
            print(f"DEBUG: Created makeup lesson for cancelled lesson {cancelled_lesson_id} with no future lessons")
            return True
        
        # Получаем все уроки включая отмененный для правильного сдвига
        all_lessons = db.query(Lesson).filter(
            Lesson.student_id == cancelled_lesson.student_id,
            Lesson.date >= cancelled_lesson.date
        ).order_by(Lesson.date.asc()).all()
        
        print(f"DEBUG: Found {len(all_lessons)} lessons starting from cancelled lesson date")
        print(f"DEBUG: Cancelled lesson ID={cancelled_lesson.id}, date={cancelled_lesson.date.strftime('%d.%m.%Y %H:%M')}")
        
        if len(all_lessons) <= 1:
            print(f"DEBUG: This is the last lesson - no future lessons to shift")
            # Если это последний урок, создаем урок для отработки
            from datetime import datetime, timedelta
            far_future_date = tz_now() + timedelta(days=3650)
            
            makeup_lesson = Lesson(
                student_id=cancelled_lesson.student_id,
                topic=cancelled_lesson.topic,
                date=far_future_date,
                attendance_status=AttendanceStatus.ATTENDED,
                mastery_level=TopicMastery.NOT_LEARNED
            )
            db.add(makeup_lesson)
            db.commit()
            print(f"DEBUG: Last lesson moved to makeup with topic '{cancelled_lesson.topic}'")
            return True
        
        # Сохраняем информацию об уроках
        dates = [lesson.date for lesson in all_lessons]
        cancelled_topic = all_lessons[0].topic
        
        print(f"DEBUG: Original lessons (sorted by date):")
        for i, lesson in enumerate(all_lessons):
            print(f"  {i}: ID={lesson.id} {lesson.topic} - {lesson.date.strftime('%d.%m.%Y %H:%M')}")
        
        # ПРАВИЛЬНАЯ логика: отмененный урок встает на место следующего
        # Все остальные сдвигаются на +1 дату
        
        # Отмененный урок получает дату следующего урока (index 1)
        all_lessons[0].date = dates[1]
        print(f"DEBUG: Cancelled lesson ID={all_lessons[0].id} '{cancelled_topic}' moved from {dates[0].strftime('%d.%m.%Y %H:%M')} to {dates[1].strftime('%d.%m.%Y %H:%M')}")
        
        # Все остальные уроки (кроме последнего) сдвигаются на +1 дату  
        for i in range(1, len(all_lessons) - 1):
            old_date = all_lessons[i].date
            all_lessons[i].date = dates[i + 1]
            print(f"DEBUG: Lesson ID={all_lessons[i].id} '{all_lessons[i].topic}' moved from {old_date.strftime('%d.%m.%Y %H:%M')} to {dates[i + 1].strftime('%d.%m.%Y %H:%M')}")
        
        # Последний урок лишается даты - создаем для него урок-заглушку
        last_lesson = all_lessons[-1]
        last_topic = last_lesson.topic
        
        # Удаляем последний урок из расписания
        db.delete(last_lesson)
        print(f"DEBUG: Deleted last scheduled lesson '{last_topic}'")
        
        # Создаем урок-заглушку для последнего урока (без конкретной даты)
        from datetime import datetime, timedelta
        far_future_date = tz_now() + timedelta(days=3650)
        
        makeup_lesson = Lesson(
            student_id=cancelled_lesson.student_id,
            topic=last_topic,
            date=far_future_date,
            attendance_status=AttendanceStatus.ATTENDED,
            mastery_level=TopicMastery.NOT_LEARNED
        )
        db.add(makeup_lesson)
        print(f"DEBUG: Created makeup lesson for '{last_topic}'")
        
        db.commit()
        
        print(f"DEBUG: Shifted {len(all_lessons)} lessons after cancellation of lesson {cancelled_lesson_id}")
        print(f"DEBUG: Future lessons count: {len(future_lessons)}")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"ERROR in shift_lessons_after_cancellation: {e}")
        return False
    finally:
        db.close()

def update_day_note(student_id: int, tutor_id: int, day: str, note: str):
    """Обновляет заметку для конкретного дня недели"""
    db = SessionLocal()
    try:
        schedule = db.query(WeeklySchedule).filter(
            WeeklySchedule.student_id == student_id,
            WeeklySchedule.tutor_id == tutor_id
        ).first()

        if not schedule:
            schedule = WeeklySchedule(student_id=student_id, tutor_id=tutor_id)
            db.add(schedule)

        # Обновляем заметку для нужного дня
        day_note_field = f"{day.lower()}_note"
        setattr(schedule, day_note_field, note)

        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"ERROR updating day note: {e}")
        return False
    finally:
        db.close()

def get_day_note(student_id: int, tutor_id: int, day: str) -> str:
    """Получает заметку для конкретного дня недели"""
    db = SessionLocal()
    try:
        schedule = db.query(WeeklySchedule).filter(
            WeeklySchedule.student_id == student_id,
            WeeklySchedule.tutor_id == tutor_id
        ).first()

        if not schedule:
            return ""

        day_note_field = f"{day.lower()}_note"
        return getattr(schedule, day_note_field) or ""
    finally:
        db.close()
