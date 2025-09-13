# -*- coding: utf-8 -*-
"""
Test script for the messaging system functionality
"""

import os
import sys
import asyncio
from unittest.mock import Mock, AsyncMock

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.handlers.tutor import (
    tutor_message_student_start_wrapper, 
    tutor_message_parent_start_wrapper,
    tutor_message_input,
    tutor_message_send_wrapper,
    tutor_message_cancel
)
from src.handlers.shared import (
    chat_with_tutor_start, 
    forward_message_to_tutor,
    handle_tutor_reply
)

async def test_tutor_message_student_wrapper():
    """Test the tutor message student wrapper function"""
    print("Testing tutor_message_student_start_wrapper...")
    
    # Mock update and context
    update = Mock()
    update.callback_query = Mock()
    update.callback_query.data = "tutor_message_student_123"
    update.callback_query.edit_message_text = AsyncMock()
    update.effective_user = Mock()
    update.effective_user.id = 12345
    
    context = Mock()
    context.user_data = {}
    
    try:
        result = await tutor_message_student_start_wrapper(update, context)
        print(f"tutor_message_student_start_wrapper returned: {result}")
        return True
    except Exception as e:
        print(f" tutor_message_student_start_wrapper failed: {e}")
        return False

async def test_tutor_message_parent_wrapper():
    """Test the tutor message parent wrapper function"""
    print("Testing tutor_message_parent_start_wrapper...")
    
    # Mock update and context
    update = Mock()
    update.callback_query = Mock()
    update.callback_query.data = "tutor_message_parent_456_123"
    update.callback_query.edit_message_text = AsyncMock()
    update.effective_user = Mock()
    update.effective_user.id = 12345
    
    context = Mock()
    context.user_data = {}
    
    try:
        result = await tutor_message_parent_start_wrapper(update, context)
        print(f" tutor_message_parent_start_wrapper returned: {result}")
        return True
    except Exception as e:
        print(f" tutor_message_parent_start_wrapper failed: {e}")
        return False

async def test_message_send_wrapper():
    """Test the message send wrapper function"""
    print("Testing tutor_message_send_wrapper...")
    
    # Mock update and context
    update = Mock()
    update.callback_query = Mock()
    update.callback_query.data = "send_message_student_123"
    update.callback_query.edit_message_text = AsyncMock()
    update.effective_user = Mock()
    update.effective_user.id = 12345
    
    context = Mock()
    context.user_data = {
        'message_content': 'Test message',
        'message_type': 'text',
        'message_recipient_type': 'student',
        'message_recipient_id': 123
    }
    context.bot = AsyncMock()
    
    try:
        result = await tutor_message_send_wrapper(update, context)
        print(f" tutor_message_send_wrapper returned: {result}")
        return True
    except Exception as e:
        print(f" tutor_message_send_wrapper failed: {e}")
        return False

async def test_student_chat_start():
    """Test student chat with tutor start"""
    print("Testing chat_with_tutor_start...")
    
    # Mock update and context
    update = Mock()
    update.callback_query = Mock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.answer = AsyncMock()
    update.effective_user = Mock()
    update.effective_user.id = 12345
    
    context = Mock()
    
    try:
        result = await chat_with_tutor_start(update, context)
        print(f" chat_with_tutor_start returned: {result}")
        return True
    except Exception as e:
        print(f" chat_with_tutor_start failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("Testing messaging system components...\n")
    
    tests = [
        test_tutor_message_student_wrapper,
        test_tutor_message_parent_wrapper,
        test_message_send_wrapper,
        test_student_chat_start
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f" Test {test.__name__} crashed: {e}")
            results.append(False)
        print()
    
    print("Test Results:")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\nAll messaging system tests passed!")
    else:
        print(f"\n{total - passed} tests failed. Check the logs above.")

if __name__ == "__main__":
    asyncio.run(main())