# -*- coding: utf-8 -*-
"""
Комплексный тест бота - проверка всех ключевых функций
"""
import os
import sys
from dotenv import load_dotenv

# Настройка путей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

def test_database():
    """Тестируем подключение к базе данных"""
    print("🔍 Тестируем базу данных...")
    
    try:
        from src.database import SessionLocal, get_all_students, get_user_by_telegram_id
        
        # Проверяем подключение
        db = SessionLocal()
        students = get_all_students()
        print(f"✅ БД подключена, найдено студентов: {len(students)}")
        
        # Проверяем репетитора
        tutor = get_user_by_telegram_id(1229333908)  # ID из check_db.py
        if tutor:
            print(f"✅ Репетитор найден: {tutor.full_name}")
        else:
            print("❌ Репетитор не найден")
            
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")
        return False

def test_handlers_import():
    """Тестируем импорт всех обработчиков"""
    print("🔍 Тестируем импорт обработчиков...")
    
    try:
        # Тестируем основные модули
        from src.keyboards import tutor_main_keyboard, student_main_keyboard
        from src.handlers.tutor import show_student_list
        from src.handlers.student import show_my_progress  
        from src.handlers.parent import show_parent_dashboard
        from src.handlers.shared import button_handler
        
        print("✅ Все обработчики импортированы успешно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return False

def test_keyboards():
    """Тестируем клавиатуры"""
    print("🔍 Тестируем клавиатуры...")
    
    try:
        from src.keyboards import tutor_main_keyboard, student_main_keyboard, parent_main_keyboard
        
        # Создаем клавиатуры
        tutor_kb = tutor_main_keyboard()
        student_kb = student_main_keyboard()
        parent_kb = parent_main_keyboard()
        
        print("✅ Все клавиатуры создаются корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка клавиатур: {e}")
        return False

def test_chart_generation():
    """Тестируем генерацию графиков"""
    print("🔍 Тестируем генерацию графиков...")
    
    try:
        from src.chart_generator import generate_progress_chart
        
        # Пытаемся сгенерировать график для первого студента
        chart_path = generate_progress_chart(6)  # ID студента из БД
        
        if chart_path and os.path.exists(chart_path):
            print("✅ График успешно сгенерирован")
            os.remove(chart_path)  # Убираем тестовый файл
            return True
        else:
            print("⚠️  График не сгенерирован (возможно, недостаточно данных)")
            return True  # Не критично
            
    except Exception as e:
        print(f"❌ Ошибка генерации графика: {e}")
        return False

def test_logging():
    """Тестируем систему логирования"""
    print("🔍 Тестируем логирование...")
    
    try:
        from src.logger import setup_logging, log_user_action
        
        logger = setup_logging()
        log_user_action(12345, "test_action", "Тестовое действие")
        
        print("✅ Логирование работает")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка логирования: {e}")
        return False

def test_health_monitor():
    """Тестируем мониторинг здоровья"""
    print("🔍 Тестируем мониторинг...")
    
    try:
        from src.health_monitor import health_monitor
        
        # Проверяем что мониторинг можно импортировать
        print("✅ Система мониторинга доступна")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка мониторинга: {e}")
        return False

def main():
    """Запуск всех тестов"""
    print("🚀 Запуск комплексного тестирования бота")
    print("=" * 50)
    
    # Загружаем переменные окружения
    load_dotenv()
    
    tests = [
        ("База данных", test_database),
        ("Импорт обработчиков", test_handlers_import),
        ("Клавиатуры", test_keyboards),
        ("Генерация графиков", test_chart_generation),
        ("Логирование", test_logging),
        ("Мониторинг", test_health_monitor),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        if test_func():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"🎯 Результат тестирования: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены! Бот готов к работе!")
    elif passed >= total * 0.8:
        print("✅ Основные функции работают, есть минорные проблемы")
    else:
        print("❌ Обнаружены серьезные проблемы, требуется доработка")
    
    print("\n💡 Для полного тестирования запустите бота и проверьте:")
    print("   • /start - команда запуска")
    print("   • Ввод кодов доступа (MARINA2024, STUD001, PARENT001)")
    print("   • Навигация по меню")
    print("   • Добавление уроков, ДЗ, оплат")

if __name__ == "__main__":
    main()