# -*- coding: utf-8 -*-
"""
Прямой тест функции генерации графика для родителей
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

async def test_parent_chart_function():
    """Тестируем функцию parent_generate_chart напрямую"""
    print("Testing parent_generate_chart function...")
    
    try:
        from src.handlers.parent import parent_generate_chart, check_parent_access
        from src.database import get_user_by_telegram_id
        
        # Мокаем объекты update и context
        class MockUpdate:
            def __init__(self):
                self.callback_query = MockCallbackQuery()
                self.effective_user = MockUser()
                self.effective_chat = MockChat()
        
        class MockCallbackQuery:
            def __init__(self):
                self.data = "parent_chart_6"
                self.message = MockMessage()
            
            async def edit_message_text(self, text, reply_markup=None):
                print(f"MockCallbackQuery.edit_message_text: {text}")
            
            async def answer(self, text=""):
                print(f"MockCallbackQuery.answer: {text}")
        
        class MockMessage:
            async def delete(self):
                print("MockMessage.delete called")
        
        class MockUser:
            def __init__(self):
                self.id = 7722156884  # ID родителя из логов
        
        class MockChat:
            def __init__(self):
                self.id = 7722156884
        
        class MockBot:
            async def send_photo(self, chat_id, photo, caption, reply_markup=None, parse_mode=None):
                print(f"MockBot.send_photo called:")
                print(f"  chat_id: {chat_id}")
                print(f"  caption: {caption}")
                if parse_mode:
                    print(f"  parse_mode: {parse_mode}")
                return True
        
        class MockContext:
            def __init__(self):
                self.bot = MockBot()
        
        # Проверяем что родитель существует
        parent = get_user_by_telegram_id(7722156884)
        if not parent:
            print("ERROR: Parent not found")
            return False
        
        print(f"Parent found: {parent.full_name}")
        
        # Создаем мок-объекты
        update = MockUpdate()
        context = MockContext()
        
        # Вызываем функцию
        await parent_generate_chart(update, context)
        
        print("SUCCESS: Function executed without errors")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=== Direct Parent Chart Function Test ===")
    load_dotenv()
    
    import asyncio
    success = asyncio.run(test_parent_chart_function())
    
    if success:
        print("SUCCESS: parent_generate_chart function works!")
    else:
        print("ERROR: parent_generate_chart function has issues")

if __name__ == "__main__":
    main()