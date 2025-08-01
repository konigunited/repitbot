import sys
import os

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import engine, Base, SessionLocal, Material, User, UserRole
from src.handlers import generate_access_code

def populate_database():
    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Add a new material if none exist
    if not db.query(Material).first():
        new_material = Material(
            title="Test Material",
            link="https://example.com",
            description="This is a test material."
        )
        db.add(new_material)
        print("Database populated with a test material.")

    # Create tutor if not exists
    tutor = db.query(User).filter(User.role == UserRole.TUTOR).first()
    if not tutor:
        tutor_code = generate_access_code()
        new_tutor = User(
            full_name="Главный Репетитор",
            role=UserRole.TUTOR,
            access_code=tutor_code
        )
        db.add(new_tutor)
        print(f"Создан репетитор. ФИО: 'Главный Репетитор', Код доступа: {tutor_code}")
    else:
        print(f"Репетитор уже существует. Код доступа: {tutor.access_code}")


    db.commit()
    db.close()

if __name__ == "__main__":
    populate_database()