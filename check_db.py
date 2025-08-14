# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from database import SessionLocal, User, UserRole

def check_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Всего пользователей в БД: {len(users)}")
        print("=" * 50)
        for user in users:
            print(f"ID: {user.id}")
            print(f"Telegram ID: {user.telegram_id}")
            print(f"Имя: {user.full_name}")
            print(f"Роль: {user.role}")
            print(f"Код доступа: {user.access_code}")
            print("-" * 30)
        tutors = db.query(User).filter(User.role == UserRole.TUTOR).all()
        print(f"\nРепетиторов найдено: {len(tutors)}")
        for tutor in tutors:
            print(f"Репетитор: {tutor.full_name} (Telegram ID: {tutor.telegram_id})")
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()