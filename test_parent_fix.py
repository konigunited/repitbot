# -*- coding: utf-8 -*-
"""
Тест исправления родительских функций
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

def test_parent_functions():
    """Тестируем родительские функции"""
    print("Testing parent functions after fix...")
    
    try:
        # Импортируем все необходимые функции
        from src.handlers.parent import show_child_menu, show_parent_dashboard
        from src.keyboards import parent_child_menu_keyboard
        from src.database import get_user_by_telegram_id
        
        print("✓ Parent functions imported successfully")
        
        # Проверяем создание клавиатуры
        keyboard = parent_child_menu_keyboard(6)  # ID ученика из БД
        print("✓ Parent child menu keyboard created")
        
        # Проверяем что родитель существует
        parent = get_user_by_telegram_id(7722156884)  # ID из логов
        if parent:
            print(f"✓ Parent found: {parent.full_name}")
        else:
            print("! Parent not found - may need to create test parent")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def check_button_handler():
    """Проверяем что button_handler правильно настроен"""
    print("\nTesting button handler mapping...")
    
    try:
        from src.handlers.shared import button_handler
        
        # Проверяем что в action_map есть нужная запись
        import inspect
        source = inspect.getsource(button_handler)
        
        if "parent_child_" in source:
            print("✓ parent_child_ mapping found in button_handler")
        else:
            print("✗ parent_child_ mapping NOT found")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ Error checking button handler: {e}")
        return False

def main():
    print("=== Testing Parent Function Fix ===")
    load_dotenv()
    
    success = True
    success &= test_parent_functions()
    success &= check_button_handler()
    
    print("\n" + "="*40)
    if success:
        print("✓ All tests passed! Parent functions should work now.")
        print("\nTo test manually:")
        print("1. Start bot: python bot.py")
        print("2. Use parent code: PARENT001") 
        print("3. Try clicking on child buttons")
    else:
        print("✗ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()