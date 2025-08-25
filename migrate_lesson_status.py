#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Миграция для добавления поля lesson_status в таблицу lessons.
"""
import sqlite3
import os

# Путь к базе данных
DB_PATH = "repitbot.db"

def migrate():
    """Добавляет поле lesson_status в таблицу lessons."""
    if not os.path.exists(DB_PATH):
        print(f"❌ База данных {DB_PATH} не найдена")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Проверяем, существует ли уже поле lesson_status
        cursor.execute("PRAGMA table_info(lessons)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'lesson_status' in columns:
            print("✅ Поле lesson_status уже существует в таблице lessons")
            return True
        
        print("🔄 Добавляем поле lesson_status в таблицу lessons...")
        
        # Добавляем новое поле с дефолтным значением 'not_conducted'
        cursor.execute("""
            ALTER TABLE lessons 
            ADD COLUMN lesson_status VARCHAR(20) DEFAULT 'not_conducted'
        """)
        
        # Обновляем уже существующие уроки в прошлом как "проведенные", если они были посещены
        cursor.execute("""
            UPDATE lessons 
            SET lesson_status = 'conducted' 
            WHERE attendance_status = 'attended' 
            AND date < datetime('now')
        """)
        
        # Оставляем будущие уроки как "не проведенные"
        cursor.execute("""
            UPDATE lessons 
            SET lesson_status = 'not_conducted' 
            WHERE date >= datetime('now')
        """)
        
        conn.commit()
        print("✅ Миграция успешно выполнена!")
        
        # Показываем статистику
        cursor.execute("SELECT lesson_status, COUNT(*) FROM lessons GROUP BY lesson_status")
        stats = cursor.fetchall()
        print("📊 Статистика статусов уроков:")
        for status, count in stats:
            status_name = "Проведен" if status == "conducted" else "Не проведен"
            print(f"  {status_name}: {count} уроков")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка при выполнении миграции: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = migrate()
    if success:
        print("🎉 Миграция завершена успешно!")
    else:
        print("💥 Миграция завершилась с ошибкой!")