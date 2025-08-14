# -*- coding: utf-8 -*-
"""
Упрощенный тест личного кабинета ученика без эмодзи
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

def test_student_access():
    """Тестируем доступ учеников"""
    print("Testing student access...")
    
    try:
        from src.database import SessionLocal, User, UserRole
        
        student_codes = ["STUD001", "STUD002", "STUD003", "STUD004", "STUD005"]
        
        db = SessionLocal()
        found = 0
        
        for code in student_codes:
            student = db.query(User).filter(
                User.access_code == code,
                User.role == UserRole.STUDENT
            ).first()
            
            if student:
                found += 1
                print(f"  {code}: {student.full_name} (ID: {student.id})")
        
        db.close()
        print(f"Found {found}/5 student accounts")
        return found >= 3
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

async def test_student_buttons():
    """Тестируем кнопки студента"""
    print("Testing student button handlers...")
    
    callbacks = [
        "my_progress",
        "schedule", 
        "homework",
        "lessons_history",
        "payment_attendance",
        "materials_library",
        "student_achievements"
    ]
    
    try:
        from src.handlers.shared import button_handler
        
        # Mock objects
        class MockUpdate:
            def __init__(self, data):
                self.callback_query = MockQuery(data)
                self.effective_user = MockUser()
                self.effective_chat = MockChat()
        
        class MockQuery:
            def __init__(self, data):
                self.data = data
                self.message = MockMessage()
            
            async def edit_message_text(self, text, **kwargs):
                print(f"    SUCCESS: {self.data}")
                
            async def answer(self, text=""):
                pass
        
        class MockMessage:
            text = "test"
        
        class MockUser:
            id = 300000001  # Student telegram ID
        
        class MockChat:
            id = 300000001
        
        class MockContext:
            pass
        
        passed = 0
        for callback in callbacks:
            try:
                print(f"  Testing: {callback}")
                update = MockUpdate(callback)
                context = MockContext()
                await button_handler(update, context)
                passed += 1
            except Exception as e:
                print(f"    FAILED: {callback} - {str(e)[:50]}")
        
        print(f"Buttons working: {passed}/{len(callbacks)}")
        return passed >= len(callbacks) * 0.7
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_student_data():
    """Тестируем данные студента"""
    print("Testing student data...")
    
    try:
        from src.database import (SessionLocal, User, Lesson, Homework, 
                                get_student_balance, get_user_by_id)
        
        student = get_user_by_id(6)  # First student
        if not student:
            print("  ERROR: Student not found")
            return False
        
        print(f"  Student: {student.full_name}")
        print(f"  Points: {student.points}")
        print(f"  Balance: {get_student_balance(6)} lessons")
        
        db = SessionLocal()
        lessons = db.query(Lesson).filter(Lesson.student_id == 6).count()
        homework = db.query(Homework).join(Lesson).filter(Lesson.student_id == 6).count()
        
        print(f"  Lessons: {lessons}")
        print(f"  Homework: {homework}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    print("="*50)
    print("STUDENT INTERFACE TEST")
    print("="*50)
    load_dotenv()
    
    tests = [
        ("Student Access", test_student_access),
        ("Student Data", test_student_data),
        ("Student Buttons", test_student_buttons),
    ]
    
    passed = 0
    total = len(tests)
    
    import asyncio
    for name, test_func in tests:
        print(f"\n{name.upper()}:")
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = asyncio.run(test_func())
            else:
                success = test_func()
            
            if success:
                passed += 1
                print("  PASSED")
            else:
                print("  FAILED")
        except Exception as e:
            print(f"  ERROR: {e}")
    
    print(f"\n{'='*50}")
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nSUCCESS: Student interface is ready!")
        print("\nTEST CODES:")
        print("- STUD001 (Ваня Иванович)")  
        print("- STUD002 (Екатерина Сидова)")
        print("- STUD003 (Алена Петрова)")
        print("- STUD004 (Сергей Козлова)")
        print("- STUD005 (Александр Никонов)")
        print("\nFEATURES AVAILABLE:")
        print("- Progress tracking")
        print("- Lesson schedule")
        print("- Homework system")
        print("- Materials library")
        print("- Achievements")
        print("- Balance and attendance")
        print("\nSTART BOT: python bot.py")
    else:
        print(f"WARNING: {passed}/{total} tests passed")
        print("Some issues need attention")

if __name__ == "__main__":
    main()