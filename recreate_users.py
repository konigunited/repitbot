# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal, User, UserRole, engine, Base, Achievement, Lesson, Homework, Payment, Material
from sqlalchemy import text
import random
import string

def generate_access_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def recreate_users():
    print("Пересоздаем пользователей...")
    
    # Удаляем все данные
    db = SessionLocal()
    try:
        # Удаляем все записи из всех таблиц
        db.execute(text("DELETE FROM achievements"))
        db.execute(text("DELETE FROM homeworks")) 
        db.execute(text("DELETE FROM lessons"))
        db.execute(text("DELETE FROM payments"))
        db.execute(text("DELETE FROM materials"))
        db.execute(text("DELETE FROM users"))
        db.commit()
        print("Все старые данные удалены")
        
        # Создаем нового репетитора
        tutor_code = generate_access_code()
        tutor = User(
            full_name="Анна Петровна",
            role=UserRole.TUTOR,
            access_code=tutor_code,
            points=0,
            streak_days=0,
            total_study_hours=0
        )
        db.add(tutor)
        
        # Создаем родителя
        parent_code = generate_access_code()
        parent = User(
            full_name="Иванов Петр Сергеевич", 
            role=UserRole.PARENT,
            access_code=parent_code,
            points=0,
            streak_days=0,
            total_study_hours=0
        )
        db.add(parent)
        db.flush()  # Чтобы получить ID родителя
        
        # Создаем учеников
        students_data = [
            ("Иванов Максим", parent.id),
            ("Петрова Анна", None),
            ("Сидоров Александр", None)
        ]
        
        student_codes = []
        for name, parent_id in students_data:
            code = generate_access_code()
            student = User(
                full_name=name,
                role=UserRole.STUDENT, 
                access_code=code,
                parent_id=parent_id,
                points=0,
                streak_days=0,
                total_study_hours=0
            )
            db.add(student)
            student_codes.append((name, code))
        
        db.commit()
        
        print("\n=== НОВЫЕ ПОЛЬЗОВАТЕЛИ СОЗДАНЫ ===")
        print(f"РЕПЕТИТОР: Анна Петровна")
        print(f"Код доступа: {tutor_code}")
        print()
        print(f"РОДИТЕЛЬ: Иванов Петр Сергеевич")
        print(f"Код доступа: {parent_code}")
        print()
        print("УЧЕНИКИ:")
        for name, code in student_codes:
            print(f"{name} - {code}")
        print("\n=== ИНСТРУКЦИЯ ===")
        print("1. Остановите бота (Ctrl+C)")
        print("2. Запустите бота заново: python bot.py")
        print("3. В Telegram напишите /start")
        print("4. Введите один из кодов доступа выше")
        print("5. Наслаждайтесь новым функционалом!")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    recreate_users()