# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal, User, UserRole, Lesson, Homework, Payment, Material, HomeworkStatus, TopicMastery
from datetime import datetime, timedelta

def create_test_data():
    print("Создаем тестовые данные...")
    
    db = SessionLocal()
    try:
        # Находим созданных пользователей
        tutor = db.query(User).filter(User.role == UserRole.TUTOR).first()
        students = db.query(User).filter(User.role == UserRole.STUDENT).all()
        
        if not tutor or not students:
            print("Сначала создайте пользователей командой: python recreate_users.py")
            return
            
        print(f"Найден репетитор: {tutor.full_name}")
        print(f"Найдено учеников: {len(students)}")
        
        # Создаем уроки для первого ученика
        student = students[0]
        print(f"Создаем уроки для: {student.full_name}")
        
        lessons_data = [
            ("Алгебра: Квадратные уравнения", -7, "Решение квадратных уравнений", True, TopicMastery.MASTERED),
            ("Геометрия: Треугольники", -5, "Свойства треугольников", True, TopicMastery.LEARNED),
            ("Алгебра: Системы уравнений", -3, "Методы решения систем", True, TopicMastery.LEARNED),
            ("Геометрия: Окружность", -1, "Свойства окружности", False, TopicMastery.NOT_LEARNED),
            ("Алгебра: Функции", 0, "Линейные и квадратичные функции", False, TopicMastery.NOT_LEARNED),
        ]
        
        created_lessons = []
        for topic, days_offset, skills, attended, mastery in lessons_data:
            lesson_date = datetime.now() + timedelta(days=days_offset)
            lesson = Lesson(
                student_id=student.id,
                topic=topic,
                date=lesson_date,
                skills_developed=skills,
                is_attended=attended,
                mastery_level=mastery
            )
            db.add(lesson)
            created_lessons.append(lesson)
        
        # Добавляем баллы за посещенные уроки
        attended_count = sum(1 for _, _, _, attended, _ in lessons_data if attended)
        student.points += attended_count * 10  # 10 баллов за урок
        
        # Добавляем баллы за освоенные темы
        mastered_count = sum(1 for _, _, _, _, mastery in lessons_data if mastery == TopicMastery.MASTERED)
        student.points += mastered_count * 25  # 25 баллов за освоенную тему
        
        db.flush()  # Чтобы получить ID уроков
        
        # Создаем домашние задания
        hw_data = [
            (0, "Решить задачи 1-5 из учебника", HomeworkStatus.CHECKED),
            (1, "Построить графики функций", HomeworkStatus.CHECKED), 
            (2, "Выполнить упражнения по теме", HomeworkStatus.SUBMITTED),
            (3, "Подготовить доклад о свойствах окружности", HomeworkStatus.PENDING),
        ]
        
        for i, (lesson_idx, description, status) in enumerate(hw_data):
            if lesson_idx < len(created_lessons):
                deadline = datetime.now() + timedelta(days=3+i)
                homework = Homework(
                    lesson_id=created_lessons[lesson_idx].id,
                    description=description,
                    deadline=deadline,
                    status=status
                )
                if status == HomeworkStatus.CHECKED:
                    homework.checked_at = datetime.now() - timedelta(days=1)
                    student.points += 15  # 15 баллов за проверенное ДЗ
                
                db.add(homework)
        
        # Создаем оплаты
        payments_data = [
            (8, -30),  # 8 уроков 30 дней назад
            (4, -15),  # 4 урока 15 дней назад  
            (6, -5),   # 6 уроков 5 дней назад
        ]
        
        for lessons_paid, days_ago in payments_data:
            payment_date = datetime.now() + timedelta(days=days_ago)
            payment = Payment(
                student_id=student.id,
                lessons_paid=lessons_paid,
                payment_date=payment_date
            )
            db.add(payment)
        
        # Создаем материалы
        materials_data = [
            ("Алгебра 9 класс", "https://example.com/algebra9", "Учебник по алгебре для 9 класса"),
            ("Геометрия формулы", "https://example.com/geometry", "Справочник основных формул"),
            ("Тесты по математике", "https://example.com/tests", "Сборник тестовых заданий"),
        ]
        
        for title, link, description in materials_data:
            material = Material(
                title=title,
                link=link, 
                description=description
            )
            db.add(material)
        
        # Устанавливаем streak для ученика
        student.streak_days = 3
        student.last_lesson_date = datetime.now() - timedelta(days=1)
        
        db.commit()
        
        print(f"\n=== ТЕСТОВЫЕ ДАННЫЕ СОЗДАНЫ ===")
        print(f"Ученик: {student.full_name}")
        print(f"Баллы: {student.points}")
        print(f"Уроков создано: {len(created_lessons)}")
        print(f"ДЗ создано: {len(hw_data)}")
        print(f"Оплат создано: {len(payments_data)}")
        print(f"Материалов создано: {len(materials_data)}")
        print(f"Текущий streak: {student.streak_days} дней")
        
        print("\n=== ТЕПЕРЬ МОЖЕТЕ ТЕСТИРОВАТЬ ===")
        print(f"Код ученика: {student.access_code}")
        print("Функции для проверки:")
        print("- 📚 Мои уроки (должны отображаться)")
        print("- 🏆 Достижения (могут быть)")
        print("- 💰 Баланс уроков (с историей)")
        print("- 📊 Мой прогресс (со статистикой)")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_data()