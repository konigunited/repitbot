#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания админского пользователя в базе данных
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database import SessionLocal, User, UserRole

def create_admin_user():
    """Создает админского пользователя с кодом доступа MARINA2024"""
    db = SessionLocal()
    try:
        # Удаляем существующих репетиторов чтобы избежать дублирования
        existing_tutors = db.query(User).filter(User.role == UserRole.TUTOR).all()
        for tutor in existing_tutors:
            print(f"Удаляем существующего репетитора: {tutor.full_name} (код: {tutor.access_code})")
            db.delete(tutor)
        
        # Создаем нового админа
        admin = User(
            full_name='Марина Администратор',
            role=UserRole.TUTOR,
            access_code='MARINA2024'
        )
        
        db.add(admin)
        db.commit()
        
        print("✅ Админский пользователь создан успешно!")
        print(f"Имя: {admin.full_name}")
        print(f"Роль: {admin.role.value}")
        print(f"Код доступа: {admin.access_code}")
        
    except Exception as e:
        print(f"❌ Ошибка при создании админа: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()