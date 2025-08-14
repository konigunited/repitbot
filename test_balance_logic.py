# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal, Lesson, User, UserRole, AttendanceStatus, get_student_balance

def test_balance_logic():
    """Тестирует логику расчета баланса для разных статусов посещаемости."""
    print("Тестируем логику расчета баланса...")
    
    db = SessionLocal()
    try:
        # Найдем первого студента
        student = db.query(User).filter(User.role == UserRole.STUDENT).first()
        if not student:
            print("Студент не найден")
            return
            
        print(f"Студент: {student.full_name}")
        
        # Найдем его уроки
        lessons = db.query(Lesson).filter(Lesson.student_id == student.id).limit(3).all()
        print(f"Тестируем на {len(lessons)} уроках")
        
        if len(lessons) < 3:
            print("Недостаточно уроков для теста")
            return
        
        # Сохраним оригинальные статусы
        original_statuses = [(lesson.id, lesson.attendance_status) for lesson in lessons]
        
        # Начальный баланс
        initial_balance = get_student_balance(student.id)
        print(f"Начальный баланс: {initial_balance}")
        
        # Тест 1: Все уроки посещены
        print("\n=== Тест 1: Все уроки посещены ===")
        for lesson in lessons:
            lesson.attendance_status = AttendanceStatus.ATTENDED
        db.commit()
        balance = get_student_balance(student.id)
        print(f"Баланс с 3 посещенными уроками: {balance}")
        
        # Тест 2: Один урок - уважительная причина
        print("\n=== Тест 2: Один урок - уважительная причина ===")
        lessons[0].attendance_status = AttendanceStatus.EXCUSED_ABSENCE
        db.commit()
        balance = get_student_balance(student.id)
        print(f"Баланс с 1 уважительным пропуском: {balance} (должен быть на +1 больше)")
        
        # Тест 3: Один урок - неуважительный пропуск
        print("\n=== Тест 3: Один урок - неуважительный пропуск ===")
        lessons[0].attendance_status = AttendanceStatus.UNEXCUSED_ABSENCE
        db.commit()
        balance = get_student_balance(student.id)
        print(f"Баланс с 1 неуважительным пропуском: {balance} (должен быть как с посещенным)")
        
        # Тест 4: Все пропуски по уважительной причине
        print("\n=== Тест 4: Все пропуски по уважительной причине ===")
        for lesson in lessons:
            lesson.attendance_status = AttendanceStatus.EXCUSED_ABSENCE
        db.commit()
        balance = get_student_balance(student.id)
        print(f"Баланс с 3 уважительными пропусками: {balance} (должен быть на +3 больше начального)")
        
        # Восстанавливаем оригинальные статусы
        print("\n=== Восстанавливаем оригинальные статусы ===")
        for lesson_id, original_status in original_statuses:
            lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
            lesson.attendance_status = original_status
        db.commit()
        
        final_balance = get_student_balance(student.id)
        print(f"Финальный баланс: {final_balance}")
        
        print("\nТест завершен успешно!")
        
    except Exception as e:
        print(f"Ошибка теста: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_balance_logic()