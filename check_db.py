# check_db.py
import sys
import os

# Добавляем src в sys.path для импорта моделей
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.database import SessionLocal, User

def check_users_in_db():
    """Читает и выводит всех пользователей и их коды доступа из БД."""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        if not users:
            print("База данных пуста. Пользователи не найдены.")
            print("Пожалуйста, запустите 'python create_all_users.py' для создания пользователей.")
            return

        print("--- Актуальные пользователи в базе данных ---")
        for user in users:
            print(f"Имя: {user.full_name:<20} | Роль: {user.role.name:<10} | Код доступа: {user.access_code}")
        print("---------------------------------------------")
        print("\nИспользуйте один из этих кодов для входа в бота.")

    finally:
        db.close()

if __name__ == "__main__":
    check_users_in_db()
