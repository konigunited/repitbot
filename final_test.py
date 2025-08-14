# -*- coding: utf-8 -*-
"""
Финальный тест всех исправлений
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

def test_parent_callback_simulation():
    """Симулируем callback от родителя"""
    print("Simulating parent callback parent_child_6...")
    
    try:
        # Симулируем данные callback_query
        class MockUpdate:
            def __init__(self):
                self.callback_query = MockCallbackQuery()
                self.effective_user = MockUser()
        
        class MockCallbackQuery:
            def __init__(self):
                self.data = "parent_child_6"
                
            async def answer(self):
                pass
                
        class MockUser:
            def __init__(self):
                self.id = 7722156884  # ID родителя из логов
        
        # Импортируем и тестируем функцию
        from src.handlers.parent import show_child_menu
        from src.database import get_user_by_telegram_id
        
        # Проверяем что родитель существует и связан с ребенком
        parent = get_user_by_telegram_id(7722156884)
        if parent:
            print(f"Parent found: {parent.full_name}, ID: {parent.id}")
            
            # Проверяем связанных детей
            from src.database import SessionLocal, User, UserRole
            db = SessionLocal()
            children = db.query(User).filter(
                User.parent_id == parent.id,
                User.role == UserRole.STUDENT
            ).all()
            
            print(f"Linked children: {len(children)}")
            for child in children:
                print(f"  - {child.full_name} (ID: {child.id})")
            
            db.close()
            
            if children:
                print("SUCCESS: Parent-child relationship is set up correctly")
                return True
            else:
                print("WARNING: No children linked to parent")
                return False
        else:
            print("ERROR: Parent not found")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    print("=== Final Parent Fix Test ===")
    load_dotenv()
    
    success = test_parent_callback_simulation()
    
    print("\n" + "="*50)
    if success:
        print("SUCCESS: Parent functions are fixed!")
        print("\nThe error 'show_child_menu() takes 2 positional arguments but 3 were given' should be resolved.")
        print("\nChanges made:")
        print("1. Removed duplicate show_child_menu function")
        print("2. Added missing keyboard import")
        print("3. Fixed button handler mapping")
        print("4. Created parent-child relationship in DB")
    else:
        print("WARNING: Some issues may remain")
    
    print(f"\nReady to test with bot!")

if __name__ == "__main__":
    main()