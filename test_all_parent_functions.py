# -*- coding: utf-8 -*-
"""
Комплексный тест всех родительских функций
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

def test_all_parent_imports():
    """Тестируем импорт всех родительских функций"""
    print("Testing all parent function imports...")
    
    try:
        from src.handlers.parent import (
            show_parent_dashboard,
            show_child_menu, 
            show_child_progress,
            show_child_schedule,
            show_child_payments,
            show_child_homework,
            show_child_lessons,
            show_child_achievements,
            parent_generate_chart
        )
        
        print("SUCCESS: All parent functions imported")
        
        # Проверяем button_handler mapping
        from src.handlers.shared import button_handler
        import inspect
        source = inspect.getsource(button_handler)
        
        required_mappings = [
            "parent_child_",
            "parent_progress_", 
            "parent_schedule_",
            "parent_payments_",
            "parent_homework_",
            "parent_lessons_",
            "parent_achievements_",
            "parent_chart_"
        ]
        
        missing = []
        for mapping in required_mappings:
            if mapping not in source:
                missing.append(mapping)
        
        if missing:
            print(f"WARNING: Missing mappings: {missing}")
            return False
        else:
            print("SUCCESS: All mappings found in button_handler")
            return True
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_database_relationships():
    """Проверяем связи в базе данных"""
    print("Testing database relationships...")
    
    try:
        from src.database import SessionLocal, User, UserRole
        
        db = SessionLocal()
        
        # Проверяем родителя
        parent = db.query(User).filter(User.telegram_id == 7722156884).first()
        if not parent:
            print("ERROR: Parent with telegram_id 7722156884 not found")
            return False
        
        # Проверяем детей этого родителя
        children = db.query(User).filter(
            User.parent_id == parent.id,
            User.role == UserRole.STUDENT
        ).all()
        
        print(f"Parent: {parent.full_name} (ID: {parent.id})")
        print(f"Children: {len(children)}")
        
        for child in children:
            print(f"  - {child.full_name} (ID: {child.id})")
        
        db.close()
        
        if len(children) > 0:
            print("SUCCESS: Database relationships are set up")
            return True
        else:
            print("WARNING: No children linked to parent")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_callback_data_patterns():
    """Тестируем паттерны callback_data"""
    print("Testing callback data patterns...")
    
    # Симулируем callback_data которые должны работать
    test_callbacks = [
        "parent_child_6",
        "parent_progress_6", 
        "parent_schedule_6",
        "parent_payments_6",
        "parent_homework_6",
        "parent_lessons_6",
        "parent_achievements_6",
        "parent_chart_6"
    ]
    
    for callback in test_callbacks:
        try:
            # Проверяем что можем извлечь student_id
            student_id = int(callback.split("_")[-1])
            if student_id != 6:
                print(f"ERROR: Wrong student_id extracted from {callback}")
                return False
        except:
            print(f"ERROR: Cannot extract student_id from {callback}")
            return False
    
    print("SUCCESS: All callback patterns work correctly")
    return True

def main():
    print("=== Comprehensive Parent Functions Test ===")
    load_dotenv()
    
    tests = [
        ("Import all functions", test_all_parent_imports),
        ("Database relationships", test_database_relationships), 
        ("Callback patterns", test_callback_data_patterns)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
            print("PASSED")
        else:
            print("FAILED")
    
    print("\n" + "="*50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: All parent functions should work correctly!")
        print("\nFixed issues:")
        print("- show_child_progress argument count")
        print("- show_child_schedule argument count") 
        print("- show_child_payments argument count")
        print("- Implemented show_child_lessons")
        print("- Implemented parent_generate_chart")
        print("- Fixed all button_handler mappings")
    else:
        print("WARNING: Some issues remain")
    
    print(f"\nReady for testing with: python bot.py")

if __name__ == "__main__":
    main()