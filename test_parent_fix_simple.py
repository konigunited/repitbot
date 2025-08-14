# -*- coding: utf-8 -*-
"""
Простой тест исправления родительских функций без символов Unicode
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

def test_parent_functions():
    """Тестируем родительские функции"""
    print("Testing parent functions after fix...")
    
    try:
        from src.handlers.parent import show_child_menu, show_parent_dashboard
        from src.keyboards import parent_child_menu_keyboard
        from src.database import get_user_by_telegram_id
        
        print("OK: Parent functions imported successfully")
        
        # Проверяем создание клавиатуры
        keyboard = parent_child_menu_keyboard(6)
        print("OK: Parent child menu keyboard created")
        
        # Проверяем что родитель существует  
        parent = get_user_by_telegram_id(200000001)  # Из check_db.py
        if parent:
            print(f"OK: Parent found: {parent.full_name}")
        else:
            print("WARNING: Parent not found")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    print("=== Testing Parent Function Fix ===")
    load_dotenv()
    
    success = test_parent_functions()
    
    print("\n" + "="*40)
    if success:
        print("SUCCESS: Parent functions should work now!")
        print("\nTo test manually:")
        print("1. Start bot: python bot.py")
        print("2. Use parent code: PARENT001")
        print("3. Try clicking on child buttons")
    else:
        print("FAILED: Check errors above")

if __name__ == "__main__":
    main()