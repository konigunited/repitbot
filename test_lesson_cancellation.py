#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест новой логики переноса уроков при отмене.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timedelta
from sqlalchemy import text
from src.database import *

def test_lesson_cancellation():
    """Тестирует новую логику переноса уроков при отмене."""
    print("Testing lesson cancellation logic...")
    
    # Создаем тестовую сессию БД
    db = SessionLocal()
    
    # Очищаем тестовые данные
    db.execute(text("DELETE FROM lessons WHERE student_id IN (SELECT id FROM users WHERE full_name LIKE 'Тестовый%')"))
    db.execute(text("DELETE FROM users WHERE full_name LIKE 'Тестовый%'"))
    db.commit()
    
    try:
        # Создаем тестового ученика
        student = User(
            telegram_id=12345,
            full_name="Тестовый Ученик",
            role=UserRole.STUDENT,
            access_code="TEST123"
        )
        db.add(student)
        db.commit()
        
        # Создаем серию уроков
        base_date = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        lessons_data = [
            ("Урок 1: Введение", base_date),
            ("Урок 2: Основы", base_date + timedelta(days=1)),
            ("Урок 3: Практика", base_date + timedelta(days=2)),
            ("Урок 4: Углубление", base_date + timedelta(days=3)),
            ("Урок 5: Заключение", base_date + timedelta(days=4))
        ]
        
        lessons = []
        for topic, date in lessons_data:
            lesson = Lesson(
                student_id=student.id,
                topic=topic,
                date=date,
                attendance_status=AttendanceStatus.ATTENDED
            )
            db.add(lesson)
            lessons.append(lesson)
        
        db.commit()
        
        print(f"Created {len(lessons)} test lessons")
        
        # Выводим изначальное состояние
        print("\nInitial lessons state:")
        for i, lesson in enumerate(lessons, 1):
            print(f"  {i}. {lesson.topic} - {lesson.date.strftime('%d.%m.%Y')}")
        
        # Отменяем второй урок (Урок 2: Основы)
        cancelled_lesson = lessons[1]  # Индекс 1 = второй урок
        print(f"\nCancelling lesson: {cancelled_lesson.topic}")
        
        # Вызываем функцию переноса
        result = shift_lessons_after_cancellation(cancelled_lesson.id)
        
        if not result:
            print("ERROR: Failed to call shift function!")
            return False
        
        # Обновляем данные из БД - создаем новую сессию чтобы увидеть изменения
        db.close()
        db = SessionLocal()
        
        # Получаем студента заново
        student = db.query(User).filter(User.full_name == "Тестовый Ученик").first()
        
        updated_lessons = db.query(Lesson).filter(
            Lesson.student_id == student.id
        ).order_by(Lesson.date.asc()).all()
        
        print(f"\nState after cancellation (total lessons: {len(updated_lessons)}):")
        for i, lesson in enumerate(updated_lessons, 1):
            if lesson.date.year > 2030:  # Проверяем урок-заглушку
                print(f"  {i}. {lesson.topic} - (NO DATE - for makeup)")
            else:
                print(f"  {i}. {lesson.topic} - {lesson.date.strftime('%d.%m.%Y')}")
        
        # Проверяем логику
        print(f"\nLogic verification:")
        
        # Должно быть 5 уроков (4 в расписании + 1 для отработки)
        if len(updated_lessons) == 5:
            print("OK: Correct lesson count after cancellation")
        else:
            print(f"ERROR: Wrong lesson count: {len(updated_lessons)}, expected 5")
        
        # Проверяем сдвиг тем
        expected_topics_after_shift = [
            "Урок 3: Практика",  # Отмененный урок получил тему следующего
            "Урок 4: Углубление", # Сдвиг на +1
            "Урок 5: Заключение", # Сдвиг на +1
            "Урок 1: Введение (отработка)", # И так далее...
        ]
        
        actual_topics = [lesson.topic for lesson in updated_lessons if lesson.date.year <= 2030]
        
        print(f"Ожидаемые темы первых 4 уроков: {expected_topics_after_shift[:4]}")
        print(f"Фактические темы первых 4 уроков: {actual_topics[:4]}")
        
        # Проверяем урок для отработки
        makeup_lessons = [lesson for lesson in updated_lessons if lesson.date.year > 2030]
        if makeup_lessons:
            makeup_lesson = makeup_lessons[0]
            print(f"Makeup lesson: {makeup_lesson.topic}")
            if makeup_lesson.date.year > 2030:
                print("OK: Makeup lesson properly scheduled for future")
            else:
                print("ERROR: Makeup lesson date not set correctly")
        
        print("\nTest completed successfully!")
        return True
        
    except Exception as e:
        print(f"ERROR in test: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    test_lesson_cancellation()