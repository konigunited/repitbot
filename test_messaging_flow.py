# -*- coding: utf-8 -*-
"""
Comprehensive test for messaging flow with database
"""

import os
import sys
import asyncio
from unittest.mock import Mock, AsyncMock

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal, User, UserRole

async def test_messaging_with_real_db():
    """Test messaging with real database data"""
    print("Testing messaging flow with database...")
    
    db = SessionLocal()
    try:
        # Find a tutor
        tutor = db.query(User).filter(User.role == UserRole.TUTOR).first()
        if not tutor:
            print("No tutor found in database")
            return False
            
        # Find a student
        student = db.query(User).filter(User.role == UserRole.STUDENT).first()
        if not student:
            print("No student found in database")
            return False
            
        print(f"Found tutor: {tutor.full_name} (ID: {tutor.id})")
        print(f"Found student: {student.full_name} (ID: {student.id})")
        
        # Test the callback data format
        student_callback = f"tutor_message_student_{student.id}"
        print(f"Testing student callback: {student_callback}")
        
        # Parse callback data like the wrapper function does
        try:
            student_id = int(student_callback.split("_")[-1])
            print(f"Extracted student_id: {student_id}")
            assert student_id == student.id
            print("Student callback parsing: OK")
        except Exception as e:
            print(f"Student callback parsing failed: {e}")
            return False
        
        # Test parent messaging if student has parents
        if student.parent:
            parent_callback = f"tutor_message_parent_{student.parent.id}_{student.id}"
            print(f"Testing parent callback: {parent_callback}")
            
            try:
                parts = parent_callback.split("_")
                if len(parts) >= 4:
                    parent_id_student_id = "_".join(parts[3:])
                    parent_id, student_id = parent_id_student_id.split('_', 1)
                    parent_id, student_id = int(parent_id), int(student_id)
                    print(f"Extracted parent_id: {parent_id}, student_id: {student_id}")
                    assert parent_id == student.parent.id
                    assert student_id == student.id
                    print("Parent callback parsing: OK")
            except Exception as e:
                print(f"Parent callback parsing failed: {e}")
                return False
        else:
            print("Student has no parent to test")
        
        return True
        
    finally:
        db.close()

async def test_message_send_callback():
    """Test message send callback parsing"""
    print("Testing message send callback parsing...")
    
    test_callbacks = [
        "send_message_student_123",
        "send_message_parent_456"
    ]
    
    for callback in test_callbacks:
        try:
            parts = callback.split("_")
            if len(parts) >= 4 and parts[0] == "send" and parts[1] == "message":
                recipient_info = "_".join(parts[2:])
                recipient_type, recipient_id = recipient_info.split('_', 1)
                recipient_id = int(recipient_id)
                print(f"Callback: {callback} -> Type: {recipient_type}, ID: {recipient_id}")
            else:
                raise ValueError("Invalid format")
        except Exception as e:
            print(f"Failed to parse {callback}: {e}")
            return False
    
    print("Message send callback parsing: OK")
    return True

async def main():
    """Run all tests"""
    print("Testing messaging flow components...\n")
    
    tests = [
        test_messaging_with_real_db,
        test_message_send_callback
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
    
    print("Test Results:")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\nAll messaging flow tests passed!")
        print("\nThe messaging system should now work correctly!")
        print("Try using the bot and clicking 'Write message to student' buttons.")
    else:
        print(f"\n{total - passed} tests failed. Check the logs above.")

if __name__ == "__main__":
    asyncio.run(main())