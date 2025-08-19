#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест добавления ученика и родителя через ConversationHandler.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime
from sqlalchemy import text
from src.database import *

def test_add_student_functions():
    """Тестирует функции добавления ученика и родителя."""
    print("Testing student and parent creation functions...")
    
    db = SessionLocal()
    
    # Очищаем тестовые данные
    db.execute(text("DELETE FROM users WHERE full_name LIKE 'Test%'"))
    db.commit()
    
    try:
        # Тест 1: Создание ученика без родителя
        print("\n1. Testing student creation without parent...")
        
        student_code = "TEST_STUDENT_001"
        student = User(
            full_name="Test Student 1",
            role=UserRole.STUDENT,
            access_code=student_code,
            parent_id=None,
            points=0,
            streak_days=0,
            total_study_hours=0
        )
        db.add(student)
        db.commit()
        
        print(f"   Created student: {student.full_name} with code: {student.access_code}")
        
        # Тест 2: Создание родителя и ученика
        print("\n2. Testing parent and student creation...")
        
        parent_code = "TEST_PARENT_001"
        parent = User(
            full_name="Test Parent 1",
            role=UserRole.PARENT,
            access_code=parent_code,
            points=0,
            streak_days=0,
            total_study_hours=0
        )
        db.add(parent)
        db.flush()  # Получаем ID родителя
        
        student2_code = "TEST_STUDENT_002"
        student2 = User(
            full_name="Test Student 2",
            role=UserRole.STUDENT,
            access_code=student2_code,
            parent_id=parent.id,
            points=0,
            streak_days=0,
            total_study_hours=0
        )
        db.add(student2)
        db.commit()
        
        print(f"   Created parent: {parent.full_name} with code: {parent.access_code}")
        print(f"   Created student: {student2.full_name} with code: {student2.access_code}")
        print(f"   Student linked to parent ID: {parent.id}")
        
        # Проверяем связь
        db.refresh(student2)
        print(f"   Verification - Student parent_id: {student2.parent_id}")
        
        # Тест 3: Добавление родителя к существующему ученику
        print("\n3. Testing adding parent to existing student...")
        
        parent2_code = "TEST_PARENT_002"
        parent2 = User(
            full_name="Test Parent 2",
            role=UserRole.PARENT,
            access_code=parent2_code,
            points=0,
            streak_days=0,
            total_study_hours=0
        )
        db.add(parent2)
        db.flush()
        
        # Обновляем первого студента, добавляя родителя
        student.parent_id = parent2.id
        db.commit()
        
        print(f"   Added parent to existing student: {student.full_name}")
        print(f"   Parent: {parent2.full_name} with code: {parent2.access_code}")
        
        # Проверка итоговых результатов
        print("\n4. Final verification...")
        
        all_students = db.query(User).filter(
            User.role == UserRole.STUDENT,
            User.full_name.like('Test%')
        ).all()
        
        all_parents = db.query(User).filter(
            User.role == UserRole.PARENT,
            User.full_name.like('Test%')
        ).all()
        
        print(f"   Total test students created: {len(all_students)}")
        print(f"   Total test parents created: {len(all_parents)}")
        
        for student in all_students:
            parent_info = "No parent"
            if student.parent_id:
                parent = db.query(User).filter(User.id == student.parent_id).first()
                if parent:
                    parent_info = f"Parent: {parent.full_name}"
            print(f"   - {student.full_name} ({student.access_code}) - {parent_info}")
        
        print("\nTest completed successfully!")
        return True
        
    except Exception as e:
        print(f"ERROR in test: {e}")
        return False
    finally:
        db.close()

def test_access_codes_unique():
    """Тестирует уникальность кодов доступа."""
    print("\nTesting access code uniqueness...")
    
    db = SessionLocal()
    try:
        # Получаем все коды доступа
        codes = db.query(User.access_code).all()
        codes_list = [code[0] for code in codes]
        
        unique_codes = set(codes_list)
        
        print(f"   Total access codes: {len(codes_list)}")
        print(f"   Unique codes: {len(unique_codes)}")
        
        if len(codes_list) == len(unique_codes):
            print("   All access codes are unique")
            return True
        else:
            print("   Found duplicate access codes!")
            return False
            
    finally:
        db.close()

if __name__ == "__main__":
    print("Testing student and parent creation functionality...\n")
    
    success1 = test_add_student_functions()
    success2 = test_access_codes_unique()
    
    if success1 and success2:
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed!")