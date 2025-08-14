# -*- coding: utf-8 -*-
"""
Скрипт для миграции базы данных - добавляет новые столбцы в таблицы
"""
import sqlite3
import os

def migrate_database():
    # Путь к базе данных
    db_path = os.path.join(os.path.dirname(__file__), "repitbot.db")
    
    if not os.path.exists(db_path):
        print("База данных не найдена!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # --- Миграция таблицы users ---
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [column[1] for column in cursor.fetchall()]
        print(f"Текущие столбцы в таблице users: {user_columns}")
        
        new_user_columns = [
            ("streak_days", "INTEGER DEFAULT 0"),
            ("last_lesson_date", "DATETIME"),
            ("total_study_hours", "INTEGER DEFAULT 0")
        ]
        
        for column_name, column_type in new_user_columns:
            if column_name not in user_columns:
                print(f"Добавляем столбец {column_name} в users...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                print(f"+ Столбец {column_name} добавлен")
            else:
                print(f"+ Столбец {column_name} уже существует")

        # --- Миграция таблицы lessons ---
        cursor.execute("PRAGMA table_info(lessons)")
        lesson_columns = [column[1] for column in cursor.fetchall()]
        print(f"Текущие столбцы в таблице lessons: {lesson_columns}")

        new_lesson_columns = [
            ("attendance_status", "VARCHAR DEFAULT 'attended' NOT NULL"),
            ("original_date", "DATETIME"),
            ("is_rescheduled", "BOOLEAN DEFAULT 0 NOT NULL")
        ]

        for column_name, column_type in new_lesson_columns:
            if column_name not in lesson_columns:
                print(f"Добавляем столбец {column_name} в lessons...")
                cursor.execute(f"ALTER TABLE lessons ADD COLUMN {column_name} {column_type}")
                print(f"+ Столбец {column_name} добавлен")
            else:
                print(f"+ Столбец {column_name} уже существует")

        # --- Создание таблицы achievements ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY,
                student_id INTEGER NOT NULL,
                achievement_type VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                description TEXT,
                icon VARCHAR DEFAULT '🏆',
                earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES users(id)
            )
        """)
        print("+ Таблица achievements создана/проверена")
        
        conn.commit()
        print("Миграция завершена успешно!")
        
    except Exception as e:
        print(f"Ошибка при миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()