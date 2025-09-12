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
    """Создает админского пользователя с кодом доступа marina"""
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже такой пользователь
        existing_admin = db.query(User).filter(User.access_code == 'marina').first()
        if existing_admin:
            print(f"Пользователь с кодом 'marina' уже существует: {existing_admin.full_name}")
            return
        
        # Создаем нового админа
        admin = User(
            full_name='Administrator',
            role=UserRole.TUTOR,
            access_code='marina'
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