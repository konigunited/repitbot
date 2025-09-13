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
    """Создает или обновляет админского пользователя с кодом доступа ADMIN2024"""
    db = SessionLocal()
    try:
        # Ищем существующего админа с кодом ADMIN2024
        existing_admin = db.query(User).filter(
            User.access_code == 'ADMIN2024',
            User.role == UserRole.TUTOR
        ).first()
        
        if existing_admin:
            print(f"Администратор с кодом 'ADMIN2024' уже существует: {existing_admin.full_name}")
            return existing_admin
        
        # Ищем старого админа с кодом marina, MARINA2024 или другими старыми кодами и обновляем его
        old_admin = db.query(User).filter(
            User.access_code.in_(['marina', 'MARINA', 'MARINA2024']),
            User.role == UserRole.TUTOR
        ).first()
        
        if old_admin:
            print(f"Обновляем существующего админа: {old_admin.full_name}")
            old_admin.access_code = 'ADMIN2024'
            old_admin.full_name = 'Марина Администратор'
            db.commit()
            print(f"Код доступа обновлен: {old_admin.access_code}")
            return old_admin
        
        # Создаем нового админа, если не нашли существующего
        admin = User(
            full_name='Марина Администратор',
            role=UserRole.TUTOR,
            access_code='ADMIN2024'
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