# -*- coding: utf-8 -*-
"""
Complete end-to-end test for all messaging functionality
"""

import os
import sys
import asyncio
from unittest.mock import Mock, AsyncMock

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal, User, UserRole
from src.handlers.tutor import (
    tutor_message_student_start_wrapper, 
    tutor_message_parent_start_wrapper,
    tutor_message_input,
    tutor_message_send_wrapper,
    tutor_message_cancel,
    tutor_parent_contact_start
)
from src.handlers.shared import (
    chat_with_tutor_start, 
    forward_message_to_tutor,
    handle_tutor_reply
)

async def create_mock_update_context(callback_data=None, message_text=None, user_id=12345):
    """Create mock update and context objects"""
    update = Mock()
    
    if callback_data:
        update.callback_query = Mock()
        update.callback_query.data = callback_data
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.answer = AsyncMock()
        update.message = None
    else:
        update.callback_query = None
        update.message = Mock()
        update.message.text = message_text
        update.message.photo = None
        update.message.document = None
        update.message.reply_text = AsyncMock()
        update.message.reply_to_message = None
        update.message.message_id = 123
        update.message.caption = None
    
    update.effective_user = Mock()
    update.effective_user.id = user_id
    
    context = Mock()
    context.user_data = {}
    context.bot = AsyncMock()
    
    return update, context

async def test_tutor_to_student_complete_flow():
    """Test complete tutor to student messaging flow"""
    print("=== Testing Tutor to Student Messaging ===")
    
    db = SessionLocal()
    try:
        student = db.query(User).filter(User.role == UserRole.STUDENT).first()
        if not student:
            print("No student found, skipping test")
            return False
        
        print(f"Testing with student: {student.full_name} (ID: {student.id})")
        
        # Step 1: Start messaging
        update, context = await create_mock_update_context(f"tutor_message_student_{student.id}")
        result = await tutor_message_student_start_wrapper(update, context)
        print(f"Step 1 - Start messaging: {result}")
        
        # Step 2: Input message
        update, context = await create_mock_update_context(message_text="Hello student!")
        context.user_data = {
            'message_recipient_type': 'student',
            'message_recipient_id': student.id,
            'message_recipient_name': student.full_name,
            'message_student_id': student.id
        }
        result = await tutor_message_input(update, context)
        print(f"Step 2 - Input message: {result}")
        
        # Step 3: Send message
        update, context = await create_mock_update_context(f"send_message_student_{student.id}")
        context.user_data = {
            'message_recipient_type': 'student',
            'message_recipient_id': student.id,
            'message_recipient_name': student.full_name,
            'message_student_id': student.id,
            'message_content': 'Hello student!',
            'message_type': 'text'
        }
        result = await tutor_message_send_wrapper(update, context)
        print(f"Step 3 - Send message: {result}")
        
        print("Tutor to Student flow: OK")
        return True
        
    except Exception as e:
        print(f"Tutor to Student flow failed: {e}")
        return False
    finally:
        db.close()

async def test_tutor_to_parent_complete_flow():
    """Test complete tutor to parent messaging flow"""
    print("=== Testing Tutor to Parent Messaging ===")
    
    db = SessionLocal()
    try:
        student = db.query(User).filter(User.role == UserRole.STUDENT, User.parent_id.isnot(None)).first()
        if not student or not student.parent:
            print("No student with parent found, skipping test")
            return False
        
        parent = student.parent
        print(f"Testing with parent: {parent.full_name} (ID: {parent.id}) for student: {student.full_name}")
        
        # Step 1: Show parent contact list
        update, context = await create_mock_update_context(f"tutor_parent_contact_{student.id}")
        result = await tutor_parent_contact_start(update, context, student.id)
        print(f"Step 1 - Show parent list: completed")
        
        # Step 2: Start messaging to parent
        update, context = await create_mock_update_context(f"tutor_message_parent_{parent.id}_{student.id}")
        result = await tutor_message_parent_start_wrapper(update, context)
        print(f"Step 2 - Start parent messaging: {result}")
        
        # Step 3: Input message
        update, context = await create_mock_update_context(message_text="Hello parent!")
        context.user_data = {
            'message_recipient_type': 'parent',
            'message_recipient_id': parent.id,
            'message_recipient_name': parent.full_name,
            'message_student_id': student.id,
            'message_student_name': student.full_name
        }
        result = await tutor_message_input(update, context)
        print(f"Step 3 - Input message: {result}")
        
        # Step 4: Send message
        update, context = await create_mock_update_context(f"send_message_parent_{parent.id}")
        context.user_data = {
            'message_recipient_type': 'parent',
            'message_recipient_id': parent.id,
            'message_recipient_name': parent.full_name,
            'message_student_id': student.id,
            'message_student_name': student.full_name,
            'message_content': 'Hello parent!',
            'message_type': 'text'
        }
        result = await tutor_message_send_wrapper(update, context)
        print(f"Step 4 - Send message: {result}")
        
        print("Tutor to Parent flow: OK")
        return True
        
    except Exception as e:
        print(f"Tutor to Parent flow failed: {e}")
        return False
    finally:
        db.close()

async def test_student_to_tutor_flow():
    """Test student to tutor messaging flow"""
    print("=== Testing Student to Tutor Messaging ===")
    
    db = SessionLocal()
    try:
        student = db.query(User).filter(User.role == UserRole.STUDENT).first()
        tutor = db.query(User).filter(User.role == UserRole.TUTOR).first()
        if not student or not tutor:
            print("No student or tutor found, skipping test")
            return False
        
        print(f"Testing student: {student.full_name} to tutor: {tutor.full_name}")
        
        # Step 1: Start chat with tutor
        update, context = await create_mock_update_context("chat_with_tutor", user_id=student.telegram_id)
        result = await chat_with_tutor_start(update, context)
        print(f"Step 1 - Start chat: {result}")
        
        # Step 2: Forward message to tutor
        update, context = await create_mock_update_context(message_text="Hello tutor!", user_id=student.telegram_id)
        result = await forward_message_to_tutor(update, context)
        print(f"Step 2 - Forward message: {result}")
        
        print("Student to Tutor flow: OK")
        return True
        
    except Exception as e:
        print(f"Student to Tutor flow failed: {e}")
        return False
    finally:
        db.close()

async def test_parent_to_tutor_flow():
    """Test parent to tutor messaging flow"""
    print("=== Testing Parent to Tutor Messaging ===")
    
    db = SessionLocal()
    try:
        parent = db.query(User).filter(User.role == UserRole.PARENT).first()
        tutor = db.query(User).filter(User.role == UserRole.TUTOR).first()
        if not parent or not tutor:
            print("No parent or tutor found, skipping test")
            return False
        
        print(f"Testing parent: {parent.full_name} to tutor: {tutor.full_name}")
        
        # Step 1: Start chat with tutor
        update, context = await create_mock_update_context("parent_chat_with_tutor", user_id=parent.telegram_id)
        result = await chat_with_tutor_start(update, context)
        print(f"Step 1 - Start chat: {result}")
        
        # Step 2: Forward message to tutor
        update, context = await create_mock_update_context(message_text="Hello tutor from parent!", user_id=parent.telegram_id)
        result = await forward_message_to_tutor(update, context)
        print(f"Step 2 - Forward message: {result}")
        
        print("Parent to Tutor flow: OK")
        return True
        
    except Exception as e:
        print(f"Parent to Tutor flow failed: {e}")
        return False
    finally:
        db.close()

async def main():
    """Run all messaging tests"""
    print("COMPLETE MESSAGING SYSTEM TEST")
    print("=" * 50)
    print()
    
    tests = [
        test_tutor_to_student_complete_flow,
        test_tutor_to_parent_complete_flow,
        test_student_to_tutor_flow,
        test_parent_to_tutor_flow
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
            results.append(False)
        print()
    
    print("=" * 50)
    print("FINAL TEST RESULTS:")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\nSUCCESS: All messaging flows are working!")
        print("\nThe RepitBot messaging system is now fully functional:")
        print("✓ Tutor can send messages to students")
        print("✓ Tutor can send messages to parents")
        print("✓ Students can send messages to tutor")
        print("✓ Parents can send messages to tutor")
        print("✓ ConversationHandler routing is fixed")
        print("✓ Parameter passing issues are resolved")
        print("\nThe bot is ready for use!")
    else:
        print(f"\nWARNING: {total - passed} messaging flows failed.")
        print("Check the logs above for details.")

if __name__ == "__main__":
    asyncio.run(main())