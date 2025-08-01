# populate_db.py
import os
import sys
import random
from datetime import datetime, timedelta

# --- Настройка пути для импорта ---
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# --- Импорты ---
from faker import Faker
from sqlalchemy.orm import sessionmaker
from src.database import (engine, Base, User, Lesson, Homework, Payment, 
                          UserRole, TopicMastery, HomeworkStatus)

# --- Константы ---
NUM_STUDENTS = 15
NUM_PARENTS = 10
LESSONS_PER_STUDENT_RANGE = (10, 30)
PAYMENTS_PER_STUDENT_RANGE = (2, 5)
LESSON_TOPICS = [
    "Основы алгебры", "Квадратные уравнения", "Тригонометрические функции",
    "Планиметрия: Треугольники", "Стереометрия: Объемы тел", "Логарифмы",
    "Производная и ее применение", "Интегралы", "Теория вероятностей"
]
SKILLS_DEVELOPED = [
    "логическое мышление", "решение уравнений", "анализ функций",
    "пространственное воображение", "работа с формулами"
]

# --- Инициализация ---
Session = sessionmaker(bind=engine)
fake = Faker('ru_RU') # Используем русский язык для имен

def generate_access_code(length=8):
    """Генерирует случайный уникальный код доступа."""
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def populate_database():
    """
    Очищает старые данные (кроме репетитора) и заполняет базу данных
    фейковыми учениками, родителями, уроками и платежами.
    """
    session = Session()
    Base.metadata.create_all(engine)

    print("Начинаю заполнение базы данных...")

    try:
        # --- 1. Очистка старых данных ---
        print("1. Очистка старых данных (ученики, родители, уроки)...")
        session.query(Homework).delete()
        session.query(Lesson).delete()
        session.query(Payment).delete()
        session.query(User).filter(User.role.in_([UserRole.STUDENT, UserRole.PARENT])).delete()
        session.commit()
        print("   ...Очистка завершена.")

        # --- 2. Получение или создание Репетитора ---
        tutor = session.query(User).filter(User.role == UserRole.TUTOR).first()
        if not tutor:
            tutor = User(
                full_name="Главный Репетитор",
                role=UserRole.TUTOR,
                access_code=generate_access_code()
            )
            session.add(tutor)
            print(f"   Создан главный репетитор, код: {tutor.access_code}")
        
        # --- 3. Создание Родителей ---
        parents = []
        print(f"2. Создание {NUM_PARENTS} родителей...")
        for _ in range(NUM_PARENTS):
            parent = User(
                full_name=fake.name(),
                role=UserRole.PARENT,
                access_code=generate_access_code()
            )
            parents.append(parent)
        session.add_all(parents)
        session.commit() # Коммит, чтобы получить ID родителей
        print("   ...Родители созданы.")

        # --- 4. Создание Учеников ---
        students = []
        print(f"3. Создание {NUM_STUDENTS} учеников...")
        for _ in range(NUM_STUDENTS):
            student = User(
                full_name=fake.name(),
                role=UserRole.STUDENT,
                access_code=generate_access_code(),
                parent_id=random.choice(parents).id, # Связываем со случайным родителем
                points=random.randint(50, 500)
            )
            students.append(student)
        session.add_all(students)
        session.commit() # Коммит, чтобы получить ID учеников
        print("   ...Ученики созданы.")

        # --- 5. Создание Истории для каждого ученика ---
        print("4. Генерация истории уроков, ДЗ и оплат...")
        for student in students:
            # Создаем платежи
            for _ in range(random.randint(*PAYMENTS_PER_STUDENT_RANGE)):
                payment = Payment(
                    student_id=student.id,
                    lessons_paid=random.choice([4, 8, 12]),
                    payment_date=fake.date_time_between(start_date="-6M", end_date="now")
                )
                session.add(payment)

            # Создаем уроки и ДЗ
            num_lessons = random.randint(*LESSONS_PER_STUDENT_RANGE)
            for i in range(num_lessons):
                lesson_date = datetime.now() - timedelta(days=random.randint(1, 180))
                is_attended = random.random() > 0.1 # 90% шанс, что урок посещен
                
                lesson = Lesson(
                    student_id=student.id,
                    topic=random.choice(LESSON_TOPICS),
                    date=lesson_date,
                    skills_developed=", ".join(random.sample(SKILLS_DEVELOPED, k=2)),
                    mastery_level=random.choice(list(TopicMastery)),
                    is_attended=is_attended
                )
                session.add(lesson)
                session.flush() # Получаем ID урока для ДЗ

                # С шансом 70% добавляем домашку
                if random.random() > 0.3:
                    hw_status = random.choice(list(HomeworkStatus))
                    checked_at_date = None
                    if hw_status == HomeworkStatus.CHECKED:
                        checked_at_date = lesson_date + timedelta(days=random.randint(2, 5))

                    homework = Homework(
                        lesson_id=lesson.id,
                        description=f"Решить задачи №{random.randint(1, 5)} со стр. {random.randint(10, 90)}",
                        deadline=lesson_date + timedelta(days=7),
                        status=hw_status,
                        checked_at=checked_at_date
                    )
                    session.add(homework)
        
        session.commit()
        print("   ...История сгенерирована.")
        print("\n[SUCCESS] База данных успешно заполнена фейковыми данными!")

    except Exception as e:
        print(f"\n[ERROR] Произошла ошибка: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    populate_database()
