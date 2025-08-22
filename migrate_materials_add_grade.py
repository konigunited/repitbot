#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Миграция для добавления поля grade в таблицу materials
"""
import sqlite3
import os

def migrate_add_grade_to_materials():
    """Добавляет поле grade в таблицу materials если его нет"""
    # Путь к базе данных
    db_path = os.path.join(os.path.dirname(__file__), "repitbot.db")
    
    if not os.path.exists(db_path):
        print(f"База данных {db_path} не найдена!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем есть ли уже поле grade
        cursor.execute("PRAGMA table_info(materials)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'grade' in columns:
            print("Поле 'grade' уже существует в таблице materials")
            return
        
        print("Добавляем поле 'grade' в таблицу materials...")
        
        # Добавляем поле grade со значением по умолчанию 5
        cursor.execute("ALTER TABLE materials ADD COLUMN grade INTEGER DEFAULT 5")
        
        # Также изменяем поле link чтобы оно могло быть NULL
        cursor.execute("""
            CREATE TABLE materials_new (
                id INTEGER PRIMARY KEY,
                title VARCHAR NOT NULL,
                link VARCHAR,
                description TEXT,
                grade INTEGER NOT NULL DEFAULT 5,
                created_at DATETIME DEFAULT (datetime('now'))
            )
        """)
        
        # Копируем данные из старой таблицы
        cursor.execute("""
            INSERT INTO materials_new (id, title, link, description, grade, created_at)
            SELECT id, title, link, description, 
                   CASE WHEN grade IS NULL THEN 5 ELSE grade END as grade, 
                   created_at 
            FROM materials
        """)
        
        # Удаляем старую таблицу и переименовываем новую
        cursor.execute("DROP TABLE materials")
        cursor.execute("ALTER TABLE materials_new RENAME TO materials")
        
        conn.commit()
        print("Миграция завершена успешно!")
        print("Все существующие материалы получили класс '5' по умолчанию")
        
    except Exception as e:
        print(f"Ошибка миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_add_grade_to_materials()