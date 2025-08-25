#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исправление значений enum для lesson_status на сервере.
Версия без эмодзи для совместимости с серверными консолями.
"""
import sqlite3
import os

# Путь к базе данных
DB_PATH = "repitbot.db"

def fix_enum_values():
    """Исправляет значения enum в поле lesson_status."""
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database {DB_PATH} not found")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Fixing enum values in lesson_status field...")
        
        # Показываем текущие значения
        cursor.execute("SELECT lesson_status, COUNT(*) FROM lessons GROUP BY lesson_status")
        current_stats = cursor.fetchall()
        print("Current values:")
        for status, count in current_stats:
            print(f"  {status}: {count} lessons")
        
        # Исправляем строковые значения на enum значения
        cursor.execute("""
            UPDATE lessons 
            SET lesson_status = 'NOT_CONDUCTED' 
            WHERE lesson_status = 'not_conducted'
        """)
        
        cursor.execute("""
            UPDATE lessons 
            SET lesson_status = 'CONDUCTED' 
            WHERE lesson_status = 'conducted'
        """)
        
        conn.commit()
        print("Enum values fixed successfully!")
        
        # Показываем исправленные значения
        cursor.execute("SELECT lesson_status, COUNT(*) FROM lessons GROUP BY lesson_status")
        fixed_stats = cursor.fetchall()
        print("Fixed values:")
        for status, count in fixed_stats:
            status_name = "Conducted" if status == "CONDUCTED" else "Not conducted"
            print(f"  {status} ({status_name}): {count} lessons")
        
        return True
        
    except sqlite3.Error as e:
        print(f"ERROR fixing enum values: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = fix_enum_values()
    if success:
        print("SUCCESS: Enum value fix completed successfully!")
    else:
        print("ERROR: Fix completed with errors!")