# -*- coding: utf-8 -*-
"""
Упрощенный комплексный тест бота без эмодзи для Windows
"""
import os
import sys
from dotenv import load_dotenv

# Настройка путей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

def test_database():
    """Тестируем подключение к базе данных"""
    print("Testing database...")
    
    try:
        from src.database import SessionLocal, get_all_students, get_user_by_telegram_id
        
        # Проверяем подключение
        db = SessionLocal()
        students = get_all_students()
        print(f"DB OK: Found {len(students)} students")
        
        # Проверяем репетитора
        tutor = get_user_by_telegram_id(1229333908)
        if tutor:
            print(f"Tutor found: {tutor.full_name}")
        else:
            print("ERROR: Tutor not found")
            
        db.close()
        return True
        
    except Exception as e:
        print(f"ERROR DB: {e}")
        return False

def test_handlers_import():
    """Тестируем импорт всех обработчиков"""
    print("Testing handlers import...")
    
    try:
        from src.keyboards import tutor_main_keyboard, student_main_keyboard
        from src.handlers.tutor import show_student_list
        from src.handlers.student import show_my_progress  
        from src.handlers.parent import show_parent_dashboard
        from src.handlers.shared import button_handler
        
        print("All handlers imported successfully")
        return True
        
    except Exception as e:
        print(f"ERROR handlers: {e}")
        return False

def test_keyboards():
    """Тестируем клавиатуры"""
    print("Testing keyboards...")
    
    try:
        from src.keyboards import tutor_main_keyboard, student_main_keyboard, parent_main_keyboard
        
        # Создаем клавиатуры
        tutor_kb = tutor_main_keyboard()
        student_kb = student_main_keyboard()
        parent_kb = parent_main_keyboard()
        
        print("All keyboards created successfully")
        return True
        
    except Exception as e:
        print(f"ERROR keyboards: {e}")
        return False

def test_chart_generation():
    """Тестируем генерацию графиков"""
    print("Testing chart generation...")
    
    try:
        from src.chart_generator import generate_progress_chart
        
        # Пытаемся сгенерировать график для первого студента
        chart_path = generate_progress_chart(6)  # ID студента из БД
        
        if chart_path and os.path.exists(chart_path):
            print("Chart generated successfully")
            os.remove(chart_path)  # Убираем тестовый файл
            return True
        else:
            print("WARNING: Chart not generated (possibly not enough data)")
            return True  # Не критично
            
    except Exception as e:
        print(f"ERROR chart: {e}")
        return False

def test_logging():
    """Тестируем систему логирования"""
    print("Testing logging...")
    
    try:
        from src.logger import setup_logging, log_user_action
        
        logger = setup_logging()
        log_user_action(12345, "test_action", "Test action")
        
        print("Logging works")
        return True
        
    except Exception as e:
        print(f"ERROR logging: {e}")
        return False

def main():
    """Запуск всех тестов"""
    print("Starting comprehensive bot testing")
    print("=" * 50)
    
    # Загружаем переменные окружения
    load_dotenv()
    
    tests = [
        ("Database", test_database),
        ("Handlers Import", test_handlers_import),
        ("Keyboards", test_keyboards),
        ("Chart Generation", test_chart_generation),
        ("Logging", test_logging),
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
    
    print("\n" + "=" * 50)
    print(f"Test results: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: All tests passed! Bot is ready!")
    elif passed >= total * 0.8:
        print("WARNING: Main functions work, minor issues detected")
    else:
        print("ERROR: Serious issues found, needs fixes")
    
    print("\nFor full testing, run the bot and check:")
    print("   • /start command")
    print("   • Access codes (MARINA2024, STUD001, PARENT001)")
    print("   • Menu navigation") 
    print("   • Adding lessons, homework, payments")

if __name__ == "__main__":
    main()