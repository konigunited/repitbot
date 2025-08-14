# -*- coding: utf-8 -*-
"""
Тест безопасной навигации после генерации графиков
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

async def test_safe_edit_function():
    """Тестируем функцию safe_edit_or_reply"""
    print("Testing safe_edit_or_reply function...")
    
    try:
        from src.handlers.parent import safe_edit_or_reply
        
        # Мокаем объекты
        class MockUpdate:
            def __init__(self, has_text=True):
                self.callback_query = MockCallbackQuery(has_text)
                self.effective_chat = MockChat()
        
        class MockCallbackQuery:
            def __init__(self, has_text):
                self.message = MockMessage(has_text)
            
            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                if not self.message.text:
                    raise Exception("There is no text in the message to edit")
                print(f"  edit_message_text: {text[:50]}...")
        
        class MockMessage:
            def __init__(self, has_text):
                self.text = "Some text" if has_text else None
            
            async def delete(self):
                print("  message deleted")
            
            async def reply_text(self, text, reply_markup=None, parse_mode=None):
                print(f"  reply_text: {text[:50]}...")
        
        class MockChat:
            async def send_message(self, text, reply_markup=None, parse_mode=None):
                print(f"  send_message: {text[:50]}...")
        
        # Тест 1: Сообщение с текстом (должно редактироваться)
        print("Test 1: Message with text")
        update1 = MockUpdate(has_text=True)
        await safe_edit_or_reply(update1, "Test message with text")
        
        # Тест 2: Сообщение без текста (фото) - должно удаляться и создаваться новое
        print("Test 2: Message without text (photo)")
        update2 = MockUpdate(has_text=False)
        await safe_edit_or_reply(update2, "Test message after photo")
        
        print("SUCCESS: safe_edit_or_reply works correctly")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_navigation_after_chart():
    """Симулируем навигацию после отправки графика"""
    print("Testing navigation after chart generation...")
    
    try:
        from src.handlers.parent import show_child_menu
        from src.database import get_user_by_telegram_id
        
        # Проверяем родителя
        parent = get_user_by_telegram_id(7722156884)
        if not parent:
            print("ERROR: Parent not found")
            return False
        
        # Мокаем объекты для сценария "после графика"
        class MockUpdate:
            def __init__(self):
                self.callback_query = MockCallbackQuery()
                self.effective_user = MockUser()
                self.effective_chat = MockChat()
        
        class MockCallbackQuery:
            def __init__(self):
                self.data = "parent_child_6"
                self.message = MockMessage(has_text=False)  # Симулируем фото-сообщение
            
            async def answer(self):
                print("  callback answered")
        
        class MockMessage:
            def __init__(self, has_text):
                self.text = "Some text" if has_text else None  # None = фото сообщение
            
            async def delete(self):
                print("  photo message deleted")
            
            async def reply_text(self, text, reply_markup=None, parse_mode=None):
                print(f"  new message sent: {text[:50]}...")
        
        class MockUser:
            def __init__(self):
                self.id = 7722156884
        
        class MockChat:
            async def send_message(self, text, reply_markup=None, parse_mode=None):
                print(f"  fallback message sent: {text[:50]}...")
        
        class MockContext:
            pass
        
        # Тестируем переход после графика
        update = MockUpdate()
        context = MockContext()
        
        print("Simulating navigation from photo message to child menu...")
        await show_child_menu(update, context)
        
        print("SUCCESS: Navigation after chart works")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=== Safe Navigation Test ===")
    load_dotenv()
    
    tests = [
        ("Safe edit function", test_safe_edit_function),
        ("Navigation after chart", test_navigation_after_chart)
    ]
    
    passed = 0
    total = len(tests)
    
    import asyncio
    for test_name, test_func in tests:
        print(f"\n{test_name.upper()}:")
        try:
            success = asyncio.run(test_func())
            if success:
                passed += 1
                print("PASSED")
            else:
                print("FAILED")
        except Exception as e:
            print(f"FAILED: {e}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: Safe navigation is implemented!")
        print("The 'There is no text in the message to edit' error should be fixed.")
    else:
        print("WARNING: Some navigation issues remain")

if __name__ == "__main__":
    main()