# create_users.py
import random
import string
import sys
import os

# Добавляем src в sys.path, чтобы корректно импортировать database
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from database import SessionLocal, engine, Base, User, UserRole

def generate_access_code(length=8):
    """Генерирует случайный уникальный код доступа."""
    db = SessionLocal()
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if not db.query(User).filter(User.access_code == code).first():
            db.close()
            return code

def create_initial_users():
    """Создает начальных пользователей: Репетитора и Родителя, если их еще нет."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Проверяем и создаем Репетитора
    tutor = db.query(User).filter(User.role == UserRole.TUTOR).first()
    if not tutor:
        tutor_code = generate_access_code()
        new_tutor = User(
            full_name="Главный Репетитор",
            role=UserRole.TUTOR,
            access_code=tutor_code
        )
        db.add(new_tutor)
        print(f"Создан Репетитор. Код доступа: {tutor_code}")
    else:
        print(f"Репетитор уже существует. Код доступа: {tutor.access_code}")

    # Проверяем и создаем Родителя
    parent = db.query(User).filter(User.role == UserRole.PARENT).first()
    if not parent:
        parent_code = generate_access_code()
        new_parent = User(
            full_name="Иван Петров (Родитель)",
            role=UserRole.PARENT,
            access_code=parent_code
        )
        db.add(new_parent)
        print(f"Создан Родитель. Код доступа: {parent_code}")
    else:
        print(f"Родитель уже существует. Код доступа: {parent.access_code}")

    db.commit()
    db.close()
    print("\nГотово! Теперь можно запускать бота и использовать эти коды.")

if __name__ == "__main__":
    create_initial_users()
