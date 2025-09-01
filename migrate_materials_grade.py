#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Миграция для добавления поля grade в таблицу materials.
"""
import sqlite3
import os

# Путь к базе данных
DB_PATH = "repitbot.db"

def migrate():
    """Добавляет поле grade в таблицу materials."""
    if not os.path.exists(DB_PATH):
        print(f"ERROR: База данных {DB_PATH} не найдена")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Проверяем, существует ли уже поле grade
        cursor.execute("PRAGMA table_info(materials)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'grade' in columns:
            print("OK: Поле grade уже существует в таблице materials")
            return True
        
        print("Добавляем поле grade в таблицу materials...")
        
        # Добавляем новое поле с дефолтным значением
        cursor.execute("""
            ALTER TABLE materials 
            ADD COLUMN grade INTEGER DEFAULT NULL
        """)
        
        conn.commit()
        print("OK: Миграция успешно выполнена!")
        
        # Показываем статистику
        cursor.execute("SELECT COUNT(*) FROM materials")
        total_materials = cursor.fetchone()[0]
        print(f"Обновлено материалов: {total_materials}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"ERROR при выполнении миграции: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = migrate()
    if success:
        print("SUCCESS: Миграция materials.grade завершена успешно!")
    else:
        print("ERROR: Миграция завершилась с ошибкой!")