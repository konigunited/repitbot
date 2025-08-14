# -*- coding: utf-8 -*-
import sqlite3
import os

# Путь к базе данных
db_path = os.path.join(os.path.dirname(__file__), "repitbot.db")

def migrate_attendance_status():
    """Добавляет поле attendance_status к существующим урокам."""
    print("Начинаем миграцию для attendance_status...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем, есть ли уже поле attendance_status
        cursor.execute("PRAGMA table_info(lessons)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'attendance_status' not in columns:
            print("Добавляем поле attendance_status...")
            cursor.execute("ALTER TABLE lessons ADD COLUMN attendance_status TEXT DEFAULT 'attended'")
            print("Поле attendance_status добавлено.")
        else:
            print("Поле attendance_status уже существует.")
        
        # Обновляем существующие записи на основе is_attended
        print("Обновляем существующие записи...")
        cursor.execute("""
            UPDATE lessons 
            SET attendance_status = CASE 
                WHEN is_attended = 1 THEN 'ATTENDED'
                ELSE 'ATTENDED'
            END
        """)
        
        conn.commit()
        print(f"Миграция завершена успешно. Обновлено {cursor.rowcount} записей.")
        
    except Exception as e:
        print(f"Ошибка миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_attendance_status()