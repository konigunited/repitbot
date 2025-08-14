# -*- coding: utf-8 -*-
"""
Тест навигации родительских кнопок
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

async def test_parent_child_navigation():
    """Тестируем переход назад к ребенку"""
    print("Testing parent_child navigation...")
    
    try:
        from src.handlers.parent import show_child_menu
        from src.handlers.shared import button_handler
        from src.database import get_user_by_telegram_id
        
        # Проверяем что родитель существует
        parent = get_user_by_telegram_id(7722156884)
        if not parent:
            print("ERROR: Parent not found")
            return False
        
        print(f"Parent found: {parent.full_name}")
        
        # Мокаем объекты
        class MockUpdate:
            def __init__(self, callback_data):
                self.callback_query = MockCallbackQuery(callback_data)
                self.effective_user = MockUser()
                self.effective_chat = MockChat()
        
        class MockCallbackQuery:
            def __init__(self, data):
                self.data = data
            
            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                print(f"MockCallbackQuery.edit_message_text:")
                print(f"  Text: {text[:100]}...")
                print(f"  Has reply_markup: {reply_markup is not None}")
                
            async def answer(self, text=""):
                if text:
                    print(f"MockCallbackQuery.answer: {text}")
        
        class MockUser:
            def __init__(self):
                self.id = 7722156884  # ID родителя
        
        class MockChat:
            def __init__(self):
                self.id = 7722156884
        
        class MockContext:
            pass
        
        # Тестируем callback parent_child_6
        update = MockUpdate("parent_child_6")
        context = MockContext()
        
        print("Testing callback: parent_child_6")
        await button_handler(update, context)
        
        print("SUCCESS: Navigation button works")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_action_map():
    """Проверяем что в action_map есть все нужные записи"""
    print("Testing action_map...")
    
    try:
        # Читаем исходный код button_handler
        import inspect
        from src.handlers.shared import button_handler
        
        source = inspect.getsource(button_handler)
        
        required_patterns = [
            "parent_child_",
            "parent_progress_", 
            "parent_chart_",
            "parent_schedule_",
            "parent_payments_"
        ]
        
        missing = []
        for pattern in required_patterns:
            if pattern not in source:
                missing.append(pattern)
        
        if missing:
            print(f"ERROR: Missing patterns in button_handler: {missing}")
            return False
        else:
            print("SUCCESS: All parent patterns found in button_handler")
            return True
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    print("=== Parent Navigation Test ===")
    load_dotenv()
    
    tests = [
        ("Action map check", test_action_map),
        ("Parent child navigation", test_parent_child_navigation)
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
                print("PASSED")
            else:
                print("FAILED")
        except Exception as e:
            print(f"FAILED: {e}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: Parent navigation should work!")
    else:
        print("WARNING: Some navigation issues remain")

if __name__ == "__main__":
    main()