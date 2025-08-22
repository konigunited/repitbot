# -*- coding: utf-8 -*-
"""
Скрипт миграции для добавления поля second_parent_id в таблицу users.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from sqlalchemy import text
from src.database import engine, SessionLocal

def migrate_add_second_parent():
    """Добавляет поле second_parent_id в таблицу users."""
    db = SessionLocal()
    try:
        # Проверяем существует ли уже колонка
        check_query = text("""
            SELECT COUNT(*) 
            FROM PRAGMA_TABLE_INFO('users') 
            WHERE name='second_parent_id'
        """)
        
        result = db.execute(check_query).scalar()
        
        if result > 0:
            print("Поле second_parent_id уже существует в таблице users")
            return True
            
        # Добавляем новую колонку
        alter_query = text("""
            ALTER TABLE users 
            ADD COLUMN second_parent_id INTEGER 
            REFERENCES users(id)
        """)
        
        db.execute(alter_query)
        db.commit()
        
        print("Поле second_parent_id успешно добавлено в таблицу users")
        
        # Проверяем что поле добавлено
        verify_query = text("SELECT COUNT(*) FROM PRAGMA_TABLE_INFO('users') WHERE name='second_parent_id'")
        verify_result = db.execute(verify_query).scalar()
        
        if verify_result > 0:
            print("Миграция успешно завершена!")
            return True
        else:
            print("Ошибка: поле не было добавлено")
            return False
            
    except Exception as e:
        db.rollback()
        print(f"Ошибка при выполнении миграции: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("Запуск миграции базы данных...")
    success = migrate_add_second_parent()
    
    if success:
        print("Миграция завершена успешно!")
    else:
        print("Миграция завершена с ошибками!")
        sys.exit(1)