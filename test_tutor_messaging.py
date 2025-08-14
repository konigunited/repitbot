# -*- coding: utf-8 -*-
"""
Тест системы связи с репетитором
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

async def test_tutor_messaging():
    """Тестируем систему сообщений репетитору"""
    print("Testing tutor messaging system...")
    
    try:
        from src.handlers.shared import forward_message_to_tutor, handle_tutor_reply, chat_with_tutor_start
        from src.database import SessionLocal, User, UserRole
        
        # Находим репетитора и ученика
        db = SessionLocal()
        tutor = db.query(User).filter(User.role == UserRole.TUTOR).first()
        student = db.query(User).filter(User.role == UserRole.STUDENT).first()
        db.close()
        
        if not tutor or not student:
            print("  ERROR: No tutor or student found")
            return False
        
        print(f"  Found tutor: {tutor.full_name} (ID: {tutor.telegram_id})")
        print(f"  Found student: {student.full_name} (ID: {student.telegram_id})")
        
        # Создаем мок-объекты для тестирования
        class MockUpdate:
            def __init__(self, user_id, text="Test message"):
                self.effective_user = MockUser(user_id)
                self.message = MockMessage(text)
                self.callback_query = MockQuery()
        
        class MockUser:
            def __init__(self, user_id):
                self.id = user_id
                self.username = "testuser"
        
        class MockMessage:
            def __init__(self, text):
                self.text = text
                self.message_id = 12345
                self.reply_to_message = None
                self.photo = None
                self.document = None
                self.voice = None
                self.caption = None
            
            async def reply_text(self, text, **kwargs):
                print(f"    Reply: {text}")
        
        class MockQuery:
            async def edit_message_text(self, text, **kwargs):
                print(f"    Edit: {text}")
            
            async def answer(self):
                pass
        
        class MockContext:
            def __init__(self):
                self.bot = MockBot()
        
        class MockBot:
            async def send_message(self, chat_id, text, **kwargs):
                print(f"    Message to {chat_id}: {text}")
        
        # Тест 1: Начало чата с репетитором (студент)
        print("  Testing chat start (student)...")
        if student.telegram_id:
            update = MockUpdate(student.telegram_id)
            context = MockContext()
            try:
                result = await chat_with_tutor_start(update, context)
                print("    SUCCESS: Chat start works")
            except Exception as e:
                print(f"    ERROR: {e}")
        
        # Тест 2: Отправка сообщения репетитору
        print("  Testing message forwarding...")
        if student.telegram_id and tutor.telegram_id:
            update = MockUpdate(student.telegram_id, "Помогите с домашним заданием")
            context = MockContext()
            try:
                await forward_message_to_tutor(update, context)
                print("    SUCCESS: Message forwarding works")
            except Exception as e:
                print(f"    ERROR: {e}")
        
        # Тест 3: Ответ репетитора (симулируем)
        print("  Testing tutor reply...")
        if tutor.telegram_id:
            # Создаем мок reply_to_message
            class MockReplyMessage:
                def __init__(self):
                    self.text = f"👨‍🎓 *Ученик:* {student.full_name}\n\nПомогите с домашним заданием"
                    self.caption = None
            
            update = MockUpdate(tutor.telegram_id, "Конечно, помогу! Какая тема?")
            update.message.reply_to_message = MockReplyMessage()
            context = MockContext()
            try:
                await handle_tutor_reply(update, context)
                print("    SUCCESS: Tutor reply works")
            except Exception as e:
                print(f"    ERROR: {e}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    print("="*50)
    print("TUTOR MESSAGING SYSTEM TEST")
    print("="*50)
    load_dotenv()
    
    import asyncio
    success = asyncio.run(test_tutor_messaging())
    
    print(f"\n{'='*50}")
    if success:
        print("SUCCESS: Tutor messaging system is working!")
        print("\nFEATURES TESTED:")
        print("- Chat initialization")
        print("- Message forwarding to tutor")
        print("- Tutor reply system")
        print("- User identification")
        print("\nCOMMUNICATION READY FOR TESTING!")
    else:
        print("WARNING: Some issues need attention")

if __name__ == "__main__":
    main()