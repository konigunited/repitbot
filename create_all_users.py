# create_all_users.py
import random
import string
import sys
import os

# Добавляем src в sys.path, чтобы корректно импортировать database
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.database import SessionLocal, engine, Base, User, UserRole

def generate_access_code(length=8):
    """Генерирует случайный уникальный код доступа."""
    db = SessionLocal()
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if not db.query(User).filter(User.access_code == code).first():
            db.close()
            return code

def create_all_user_types():
    """Создает пользователей всех типов: Репетитор, Родитель и Ученик."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Создаем Репетитора (Админа)
        tutor_user = db.query(User).filter(User.role == UserRole.TUTOR).first()
        if not tutor_user:
            tutor_code = generate_access_code()
            tutor_user = User(
                full_name="Главный Репетитор",
                role=UserRole.TUTOR,
                access_code=tutor_code
            )
            db.add(tutor_user)
            print(f"Создан Репетитор (Админ). Код доступа: {tutor_code}")
        else:
            print(f"Репетитор (Админ) уже существует. Код доступа: {tutor_user.access_code}")

        # 2. Создаем Родителя
        parent_user = db.query(User).filter(User.full_name == "Тестовый Родитель").first()
        if not parent_user:
            parent_code = generate_access_code()
            parent_user = User(
                full_name="Тестовый Родитель",
                role=UserRole.PARENT,
                access_code=parent_code
            )
            db.add(parent_user)
            print(f"Создан Родитель. Код доступа: {parent_code}")
        else:
            print(f"Родитель 'Тестовый Родитель' уже существует. Код доступа: {parent_user.access_code}")

        # 3. Создаем Ученика и связываем с Родителем
        student_user = db.query(User).filter(User.full_name == "Тестовый Ученик").first()
        if not student_user:
            student_code = generate_access_code()
            student_user = User(
                full_name="Тестовый Ученик",
                role=UserRole.STUDENT,
                access_code=student_code,
                parent_id=parent_user.id  # Связываем с родителем
            )
            db.add(student_user)
            print(f"Создан Ученик. Код доступа: {student_code}")
            print(f"Ученик '{student_user.full_name}' связан с родителем '{parent_user.full_name}'.")
        else:
            # Если ученик уже есть, убедимся, что он связан с родителем
            if student_user.parent_id != parent_user.id:
                student_user.parent_id = parent_user.id
                print(f"Ученик '{student_user.full_name}' обновлен и связан с родителем '{parent_user.full_name}'.")
            print(f"Ученик 'Тестовый Ученик' уже существует. Код доступа: {student_user.access_code}")


        db.commit()

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        db.rollback()
    finally:
        db.close()
        print("\nГотово! Теперь можно запускать бота и использовать эти коды для входа.")

if __name__ == "__main__":
    create_all_user_types()
