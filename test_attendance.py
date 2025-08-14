# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal, Lesson, User, UserRole, AttendanceStatus, get_student_balance

def test_attendance_system():
    """Тестирует новую систему посещаемости."""
    print("Тестируем систему посещаемости...")
    
    db = SessionLocal()
    try:
        # Найдем первого студента
        student = db.query(User).filter(User.role == UserRole.STUDENT).first()
        if not student:
            print("Студент не найден")
            return
            
        print(f"Студент: {student.full_name}")
        
        # Найдем его уроки
        lessons = db.query(Lesson).filter(Lesson.student_id == student.id).all()
        print(f"Найдено уроков: {len(lessons)}")
        
        for lesson in lessons:
            print(f"\nУрок: {lesson.topic}")
            print(f"Дата: {lesson.date}")
            print(f"Старый статус (is_attended): {lesson.is_attended}")
            print(f"Новый статус (attendance_status): {lesson.attendance_status}")
        
        # Проверим баланс студента
        balance = get_student_balance(student.id)
        print(f"\nБаланс студента: {balance}")
        
        # Поменяем статус одного урока на неуважительный пропуск
        if lessons:
            first_lesson = lessons[0]
            old_status = first_lesson.attendance_status
            first_lesson.attendance_status = AttendanceStatus.UNEXCUSED_ABSENCE
            first_lesson.is_attended = False
            db.commit()
            
            print(f"\nИзменен статус урока '{first_lesson.topic}':")
            print(f"Было: {old_status}")
            print(f"Стало: {first_lesson.attendance_status}")
            
            # Проверим новый баланс
            new_balance = get_student_balance(student.id)
            print(f"Новый баланс студента: {new_balance}")
            
            # Вернем обратно
            first_lesson.attendance_status = old_status
            first_lesson.is_attended = (old_status == AttendanceStatus.ATTENDED)
            db.commit()
            print(f"Статус восстановлен")
        
        print("\nТест завершен успешно!")
        
    except Exception as e:
        print(f"Ошибка теста: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_attendance_system()