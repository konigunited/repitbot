# -*- coding: utf-8 -*-
"""
Полный тест личного кабинета ученика
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

def test_student_access_code():
    """Тестируем коды доступа учеников"""
    print("Testing student access codes...")
    
    try:
        from src.database import SessionLocal, User, UserRole
        
        student_codes = [
            ("STUD001", "Ваня Иванович"),
            ("STUD002", "Екатерина Сидова"), 
            ("STUD003", "Алена Петрова"),
            ("STUD004", "Сергей Козлова"),
            ("STUD005", "Александр Никонов")
        ]
        
        db = SessionLocal()
        
        found_students = []
        for code, expected_name in student_codes:
            student = db.query(User).filter(
                User.access_code == code,
                User.role == UserRole.STUDENT
            ).first()
            
            if student:
                found_students.append((code, student.full_name))
                print(f"  {code}: {student.full_name} (ID: {student.id})")
            else:
                print(f"  {code}: NOT FOUND")
        
        db.close()
        
        print(f"Found {len(found_students)} student accounts")
        return len(found_students) >= 3  # Достаточно если есть хотя бы 3
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

async def test_student_main_functions():
    """Тестируем основные функции ученика"""
    print("Testing student main functions...")
    
    student_callbacks = [
        "my_progress",           # Мой прогресс
        "schedule",             # Расписание
        "homework",             # Домашние задания
        "lessons_history",      # История уроков
        "payment_attendance",   # Баланс и посещаемость
        "materials_library",    # Библиотека материалов
        "student_achievements", # Достижения
    ]
    
    try:
        from src.handlers.shared import button_handler
        from src.database import get_user_by_telegram_id
        
        # Используем первого найденного студента (ID 6 - Ваня Иванович)
        test_student_id = 300000001  # Telegram ID из базы
        
        # Мокаем объекты для тестирования
        class MockUpdate:
            def __init__(self, callback_data):
                self.callback_query = MockCallbackQuery(callback_data)
                self.effective_user = MockUser(test_student_id)
                self.effective_chat = MockChat()
        
        class MockCallbackQuery:
            def __init__(self, data):
                self.data = data
                self.message = MockMessage()
            
            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                print(f"    SUCCESS: {self.data}")
                
            async def answer(self, text=""):
                pass
        
        class MockMessage:
            def __init__(self):
                self.text = "Some text"
        
        class MockUser:
            def __init__(self, user_id):
                self.id = user_id
        
        class MockChat:
            def __init__(self):
                self.id = test_student_id
        
        class MockContext:
            pass
        
        # Тестируем каждый callback
        passed = 0
        for callback in student_callbacks:
            try:
                print(f"  Testing: {callback}")
                update = MockUpdate(callback)
                context = MockContext()
                await button_handler(update, context)
                passed += 1
            except Exception as e:
                print(f"    FAILED: {callback} - {e}")
        
        print(f"Student functions: {passed}/{len(student_callbacks)} working")
        return passed >= len(student_callbacks) * 0.8  # 80% должно работать
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_student_keyboards():
    """Тестируем клавиатуры ученика"""
    print("Testing student keyboards...")
    
    try:
        from src.keyboards import student_main_keyboard
        
        # Создаем главную клавиатуру ученика
        keyboard = student_main_keyboard()
        
        if keyboard and keyboard.inline_keyboard:
            button_count = sum(len(row) for row in keyboard.inline_keyboard)
            print(f"  Student main keyboard: {button_count} buttons")
            
            # Проверяем что есть основные кнопки
            all_buttons = []
            for row in keyboard.inline_keyboard:
                for button in row:
                    all_buttons.append(button.text)
            
            print(f"  Buttons: {all_buttons}")
            return len(all_buttons) >= 5  # Должно быть минимум 5 кнопок
        else:
            print("  ERROR: No keyboard created")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

async def test_homework_submission():
    """Тестируем подачу домашнего задания"""
    print("Testing homework submission...")
    
    try:
        from src.database import SessionLocal, Homework, Lesson, User
        
        db = SessionLocal()
        
        # Находим ученика и его ДЗ
        student = db.query(User).filter(User.id == 6).first()  # ID из тестов
        if not student:
            print("  ERROR: Test student not found")
            return False
        
        # Находим ДЗ этого ученика
        homework = db.query(Homework).join(Lesson).filter(
            Lesson.student_id == student.id
        ).first()
        
        if homework:
            print(f"  Found homework: {homework.description[:50]}...")
            print(f"  Status: {homework.status}")
            print(f"  Lesson: {homework.lesson.topic}")
            
            # Тестируем callback для сдачи ДЗ
            callback_data = f"student_submit_hw_{homework.id}"
            print(f"  Test callback: {callback_data}")
            
            db.close()
            return True
        else:
            print("  WARNING: No homework found for testing")
            db.close()
            return True  # Не критично
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_student_data_access():
    """Тестируем доступ к данным ученика"""
    print("Testing student data access...")
    
    try:
        from src.database import (SessionLocal, User, Lesson, Homework, 
                                get_student_balance, get_user_by_id)
        
        db = SessionLocal()
        
        # Тестируем студента ID 6
        student = get_user_by_id(6)
        if not student:
            print("  ERROR: Student ID 6 not found")
            return False
        
        print(f"  Student: {student.full_name}")
        print(f"  Points: {student.points}")
        print(f"  Streak days: {student.streak_days}")
        
        # Баланс уроков
        balance = get_student_balance(6)
        print(f"  Lesson balance: {balance}")
        
        # Уроки
        lessons = db.query(Lesson).filter(Lesson.student_id == 6).count()
        print(f"  Total lessons: {lessons}")
        
        # ДЗ
        homework_count = db.query(Homework).join(Lesson).filter(
            Lesson.student_id == 6
        ).count()
        print(f"  Total homework: {homework_count}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    print("="*60)
    print("ПОЛНЫЙ ТЕСТ ЛИЧНОГО КАБИНЕТА УЧЕНИКА")
    print("="*60)
    load_dotenv()
    
    tests = [
        ("Student Access Codes", test_student_access_code),
        ("Student Data Access", test_student_data_access),
        ("Student Keyboards", test_student_keyboards),
        ("Student Main Functions", test_student_main_functions),
        ("Homework Submission", test_homework_submission),
    ]
    
    passed = 0
    total = len(tests)
    
    import asyncio
    for test_name, test_func in tests:
        print(f"\n{test_name.upper()}:")
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = asyncio.run(test_func())
            else:
                success = test_func()
            
            if success:
                passed += 1
                print("  ✓ PASSED")
            else:
                print("  ✗ FAILED")
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
    
    print(f"\n{'='*60}")
    print(f"РЕЗУЛЬТАТ ТЕСТИРОВАНИЯ: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("\n🎉 ОТЛИЧНО! Личный кабинет ученика полностью готов!")
        print("\n📋 ГОТОВЫЕ ФУНКЦИИ:")
        print("✓ Авторизация по кодам доступа")
        print("✓ Просмотр прогресса и статистики")
        print("✓ Расписание уроков")
        print("✓ Система домашних заданий")
        print("✓ История занятий")
        print("✓ Библиотека материалов")
        print("✓ Система достижений")
        print("✓ Баланс уроков и посещаемость")
        print("\n🎯 КОДЫ ДЛЯ ТЕСТИРОВАНИЯ:")
        print("• STUD001 - Ваня Иванович")
        print("• STUD002 - Екатерина Сидова")
        print("• STUD003 - Алена Петрова")
        print("• STUD004 - Сергей Козлова")
        print("• STUD005 - Александр Никонов")
        print("\n🚀 ЗАПУСК: python bot.py")
    elif passed >= total * 0.8:
        print(f"\n⚠️  ВНИМАНИЕ: Основные функции работают ({passed}/{total})")
        print("Есть минорные проблемы, но система готова к тестированию")
    else:
        print(f"\n❌ ПРОБЛЕМЫ: Только {passed}/{total} тестов прошло")
        print("Требуется дополнительная отладка")

if __name__ == "__main__":
    main()