#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
import os

DB_PATH = "repitbot.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if lesson_status column exists
        cursor.execute("PRAGMA table_info(lessons)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'lesson_status' in columns:
            print("lesson_status column already exists")
            return True
        
        print("Adding lesson_status column...")
        
        # Add new column with default value
        cursor.execute("""
            ALTER TABLE lessons 
            ADD COLUMN lesson_status VARCHAR(20) DEFAULT 'not_conducted'
        """)
        
        # Update existing lessons
        cursor.execute("""
            UPDATE lessons 
            SET lesson_status = 'conducted' 
            WHERE attendance_status = 'attended' 
            AND date < datetime('now')
        """)
        
        cursor.execute("""
            UPDATE lessons 
            SET lesson_status = 'not_conducted' 
            WHERE date >= datetime('now')
        """)
        
        conn.commit()
        print("Migration completed successfully!")
        
        # Show stats
        cursor.execute("SELECT lesson_status, COUNT(*) FROM lessons GROUP BY lesson_status")
        stats = cursor.fetchall()
        print("Lesson status statistics:")
        for status, count in stats:
            print(f"  {status}: {count} lessons")
        
        return True
        
    except sqlite3.Error as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()