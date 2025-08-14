# -*- coding: utf-8 -*-
"""
Скрипт для создания комплексных тестовых данных для RepitBot
Репетитор: Марина
"""

import os
import sys
import json
from datetime import datetime, timedelta
from random import choice, randint

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database import (
    engine, Base, SessionLocal, User, Lesson, Homework, Payment, Material, Achievement,
    UserRole, HomeworkStatus, TopicMastery, AttendanceStatus
)

def create_tables():
    """Создание всех таблиц"""
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы созданы")

def create_test_data():
    """Создание тестовых данных"""
    db = SessionLocal()
    
    try:
        # 1. Создаем репетитора Марину
        tutor = User(
            telegram_id=123456789,
            username="marina_tutor",
            full_name="Марина Александровна",
            role=UserRole.TUTOR,
            access_code="MARINA2024",
            points=0
        )
        db.add(tutor)
        db.flush()  # Получаем ID
        print(f"✅ Создан репетитор: {tutor.full_name}")

        # 2. Создаем родителей
        parents = []
        parents_data = [
            {
                "telegram_id": 200000001,
                "username": "elena_mom", 
                "full_name": "Елена Викторовна Смирнова",
                "access_code": "PARENT001"
            },
            {
                "telegram_id": 200000002,
                "username": "sergey_dad",
                "full_name": "Сергей Николаевич Петров", 
                "access_code": "PARENT002"
            },
            {
                "telegram_id": 200000003,
                "username": "anna_mama",
                "full_name": "Анна Дмитриевна Козлова",
                "access_code": "PARENT003"
            },
            {
                "telegram_id": 200000004,
                "username": "vladimir_papa",
                "full_name": "Владимир Сергеевич Морозов",
                "access_code": "PARENT004"
            }
        ]
        
        for parent_data in parents_data:
            parent = User(
                telegram_id=parent_data["telegram_id"],
                username=parent_data["username"],
                full_name=parent_data["full_name"],
                role=UserRole.PARENT,
                access_code=parent_data["access_code"],
                points=0
            )
            db.add(parent)
            parents.append(parent)
        
        db.flush()
        print(f"✅ Создано {len(parents)} родителей")

        # 3. Создаем студентов с привязкой к родителям
        students = []
        students_data = [
            {
                "telegram_id": 300000001,
                "username": "masha_student",
                "full_name": "Маша Смирнова",
                "access_code": "STUD001",
                "parent_index": 0,  # Елена Викторовна
                "points": 245,
                "streak_days": 5,
                "total_study_hours": 1200
            },
            {
                "telegram_id": 300000002,
                "username": "alex_student", 
                "full_name": "Александр Петров",
                "access_code": "STUD002",
                "parent_index": 1,  # Сергей Николаевич
                "points": 180,
                "streak_days": 3,
                "total_study_hours": 950
            },
            {
                "telegram_id": 300000003,
                "username": "dasha_student",
                "full_name": "Дарья Козлова", 
                "access_code": "STUD003",
                "parent_index": 2,  # Анна Дмитриевна
                "points": 320,
                "streak_days": 8,
                "total_study_hours": 1580
            },
            {
                "telegram_id": 300000004,
                "username": "nikita_student",
                "full_name": "Никита Морозов",
                "access_code": "STUD004", 
                "parent_index": 3,  # Владимир Сергеевич
                "points": 95,
                "streak_days": 1,
                "total_study_hours": 420
            },
            {
                "telegram_id": 300000005,
                "username": "katya_student",
                "full_name": "Екатерина Иванова",
                "access_code": "STUD005",
                "parent_index": None,  # Без родителя
                "points": 410,
                "streak_days": 12,
                "total_study_hours": 2100
            }
        ]

        for student_data in students_data:
            student = User(
                telegram_id=student_data["telegram_id"],
                username=student_data["username"],
                full_name=student_data["full_name"],
                role=UserRole.STUDENT,
                access_code=student_data["access_code"],
                parent_id=parents[student_data["parent_index"]].id if student_data["parent_index"] is not None else None,
                points=student_data["points"],
                streak_days=student_data["streak_days"],
                total_study_hours=student_data["total_study_hours"],
                last_lesson_date=datetime.now() - timedelta(days=randint(0, 3))
            )
            db.add(student)
            students.append(student)
        
        db.flush()
        print(f"✅ Создано {len(students)} студентов")

        # 4. Создаем материалы для библиотеки
        materials_data = [
            {
                "title": "Основы алгебры для 8 класса",
                "link": "https://drive.google.com/file/d/algebra8/view",
                "description": "Подробный конспект по основам алгебры с примерами и задачами"
            },
            {
                "title": "Геометрия: треугольники и их свойства", 
                "link": "https://drive.google.com/file/d/geometry_triangles/view",
                "description": "Теория и практические задания по треугольникам"
            },
            {
                "title": "Функции и их графики",
                "link": "https://drive.google.com/file/d/functions/view", 
                "description": "Изучение линейных и квадратичных функций"
            },
            {
                "title": "Системы уравнений",
                "link": "https://drive.google.com/file/d/systems/view",
                "description": "Методы решения систем линейных уравнений"
            },
            {
                "title": "Подготовка к ОГЭ: задачи части 1",
                "link": "https://drive.google.com/file/d/oge_part1/view",
                "description": "Типовые задачи первой части ОГЭ с решениями"
            }
        ]
        
        for material_data in materials_data:
            material = Material(
                title=material_data["title"],
                link=material_data["link"], 
                description=material_data["description"],
                created_at=datetime.now() - timedelta(days=randint(1, 30))
            )
            db.add(material)
        
        db.flush()
        print(f"✅ Создано {len(materials_data)} материалов")

        # 5. Создаем платежи для студентов
        for student in students:
            payment_count = randint(2, 4)
            for i in range(payment_count):
                payment = Payment(
                    student_id=student.id,
                    lessons_paid=choice([4, 6, 8, 10]),
                    payment_date=datetime.now() - timedelta(days=randint(1, 90))
                )
                db.add(payment)
        
        db.flush()
        print("✅ Созданы платежи для студентов")

        # 6. Создаем уроки с разнообразными статусами
        topics = [
            "Линейные уравнения", "Квадратичные функции", "Системы уравнений",
            "Неравенства", "Геометрия: треугольники", "Окружности", 
            "Тригонометрия", "Логарифмы", "Производные", "Интегралы",
            "Комбинаторика", "Вероятность", "Статистика", "Прогрессии"
        ]
        
        skills_examples = [
            "Решение уравнений методом подстановки",
            "Построение графиков функций", 
            "Доказательство теорем",
            "Применение формул сокращенного умножения",
            "Решение текстовых задач",
            "Работа с координатной плоскостью"
        ]

        for student in students:
            lesson_count = randint(8, 15)
            for i in range(lesson_count):
                lesson_date = datetime.now() - timedelta(days=randint(1, 120))
                
                # Разнообразные статусы посещения
                attendance_weights = [
                    (AttendanceStatus.ATTENDED, 70),
                    (AttendanceStatus.EXCUSED_ABSENCE, 15), 
                    (AttendanceStatus.UNEXCUSED_ABSENCE, 10),
                    (AttendanceStatus.RESCHEDULED, 5)
                ]
                
                attendance_status = choice([status for status, _ in attendance_weights])
                
                lesson = Lesson(
                    topic=choice(topics),
                    date=lesson_date,
                    student_id=student.id,
                    skills_developed=choice(skills_examples),
                    mastery_level=choice(list(TopicMastery)),
                    mastery_comment="Хорошо усваивает материал" if randint(1, 10) > 3 else "Нужна дополнительная практика",
                    attendance_status=attendance_status,
                    is_attended=(attendance_status == AttendanceStatus.ATTENDED),
                    original_date=lesson_date - timedelta(days=randint(1, 7)) if attendance_status == AttendanceStatus.RESCHEDULED else None,
                    is_rescheduled=(attendance_status == AttendanceStatus.RESCHEDULED)
                )
                db.add(lesson)
        
        db.flush()
        print("✅ Созданы уроки для всех студентов")

        # 7. Создаем домашние задания
        hw_descriptions = [
            "Решить примеры 1-15 на странице 87",
            "Построить графики функций из задания 3.2",
            "Изучить теорему о свойствах треугольника",
            "Выполнить тест по системам уравнений", 
            "Решить задачи на проценты №45-52",
            "Подготовиться к контрольной работе"
        ]
        
        submission_examples = [
            "Все задачи решены, есть вопросы по задаче №7",
            "Выполнил основную часть, задача 12 вызывает затруднения",
            "Готов к проверке",
            "Не успел доделать последние 2 задачи",
            "Все сделал, прикрепляю фото решений"
        ]

        lessons = db.query(Lesson).all()
        for lesson in lessons[:randint(len(lessons)//2, len(lessons))]:
            homework = Homework(
                lesson_id=lesson.id,
                description=choice(hw_descriptions),
                file_link=f"https://drive.google.com/homework_{randint(1000, 9999)}" if randint(1, 3) == 1 else None,
                photo_file_ids=json.dumps([f"BAAC123_{randint(100,999)}", f"BAAC456_{randint(100,999)}"]) if randint(1, 4) == 1 else None,
                status=choice(list(HomeworkStatus)),
                deadline=lesson.date + timedelta(days=randint(3, 7)),
                submission_text=choice(submission_examples) if randint(1, 3) > 1 else None,
                submission_photo_file_ids=json.dumps([f"STUD789_{randint(100,999)}"]) if randint(1, 3) == 1 else None,
                checked_at=datetime.now() - timedelta(days=randint(1, 30)) if randint(1, 2) == 1 else None
            )
            db.add(homework)
        
        db.flush() 
        print("✅ Созданы домашние задания")

        # 8. Создаем достижения для студентов
        achievement_types = [
            ("first_lesson", "Первый урок", "Начало большого пути!", "🎯"),
            ("points_50", "Начинающий", "Первые 50 баллов!", "🌟"),
            ("points_100", "Активист", "100 баллов набрано!", "⭐"), 
            ("points_250", "Звезда", "250 баллов - отличный результат!", "🌠"),
            ("streak_3", "Трудяга", "3 дня подряд с уроками!", "🔥"),
            ("streak_7", "Неделя знаний", "7 дней подряд с уроками!", "⚡"),
            ("hw_master", "Мастер ДЗ", "10 домашних заданий выполнено!", "📚"),
            ("perfect_month", "Идеальный месяц", "Месяц без пропусков!", "👑")
        ]

        for student in students:
            # Каждому студенту даем несколько достижений
            achievement_count = randint(2, 5)
            selected_achievements = sorted(achievement_types, key=lambda x: randint(1, 100))[:achievement_count]
            
            for ach_type, title, desc, icon in selected_achievements:
                achievement = Achievement(
                    student_id=student.id,
                    achievement_type=ach_type,
                    title=title,
                    description=desc,
                    icon=icon,
                    earned_at=datetime.now() - timedelta(days=randint(1, 60))
                )
                db.add(achievement)
        
        db.flush()
        print("✅ Созданы достижения для студентов")

        # 9. Коммитим все изменения
        db.commit()
        print("\n🎉 Все тестовые данные успешно созданы!")
        
        # Выводим статистику
        print(f"\n📊 СТАТИСТИКА:")
        print(f"👩‍🏫 Репетиторов: 1 (Марина Александровна)")
        print(f"👨‍👩‍👧‍👦 Родителей: {len(parents)}")
        print(f"👨‍🎓 Студентов: {len(students)}")
        print(f"📚 Материалов: {len(materials_data)}")
        print(f"📅 Уроков: ~{len(students) * 10}")
        print(f"📝 Домашних заданий: ~{len(lessons)//2}")
        print(f"💰 Платежей: ~{len(students) * 3}")
        print(f"🏆 Достижений: ~{len(students) * 3}")

    except Exception as e:
        print(f"❌ Ошибка при создании данных: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Создание комплексных тестовых данных для RepitBot...")
    print("Репетитор: Марина Александровна")
    print("-" * 50)
    
    create_tables()
    create_test_data()
    
    print("\nГотово! Теперь можно запускать бота для тестирования.")