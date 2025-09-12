#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для исправления кода доступа админа на верхний регистр
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database import SessionLocal, User

def fix_admin_code():
    """Исправляет код доступа админа на верхний регистр"""
    db = SessionLocal()
    try:
        # Ищем пользователя с кодом marina
        admin = db.query(User).filter(User.access_code == 'marina').first()
        if admin:
            admin.access_code = 'MARINA'
            db.commit()
            print("✅ Код доступа обновлен на 'MARINA'")
        else:
            print("❌ Пользователь с кодом 'marina' не найден")
        
        # Показываем всех пользователей
        users = db.query(User).all()
        print("\nВсе пользователи в базе:")
        for user in users:
            print(f"- {user.full_name}: {user.access_code} ({user.role.value})")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_admin_code()