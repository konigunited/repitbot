# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal, engine
from sqlalchemy import text

def migrate_homework_photos():
    """Добавляет поля для фотографий в таблицу homeworks"""
    print("Добавляем поля для фотографий в домашние задания...")
    
    db = SessionLocal()
    try:
        # Добавляем новые поля в таблицу homeworks
        migrations = [
            "ALTER TABLE homeworks ADD COLUMN photo_file_ids TEXT",
            "ALTER TABLE homeworks ADD COLUMN submission_text TEXT", 
            "ALTER TABLE homeworks ADD COLUMN submission_photo_file_ids TEXT"
        ]
        
        for migration in migrations:
            try:
                db.execute(text(migration))
                print(f"Выполнено: {migration}")
            except Exception as e:
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"Поле уже существует: {migration}")
                else:
                    print(f"Ошибка: {migration} - {e}")
        
        db.commit()
        print("Миграция завершена! Теперь домашние задания поддерживают фотографии.")
        
    except Exception as e:
        print(f"Ошибка миграции: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_homework_photos()