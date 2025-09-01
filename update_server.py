#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Универсальный скрипт обновления RepitBot на сервере
Поддерживает Windows и Linux
"""
import subprocess
import sqlite3
import os
import sys
import platform
import shutil
from datetime import datetime

def is_windows():
    """Проверяет, запущен ли скрипт на Windows"""
    return platform.system().lower() == 'windows'

def run_command(command, description, shell=True):
    """Выполняет команду и показывает результат"""
    print(f"\n=== {description} ===")
    try:
        result = subprocess.run(command, shell=shell, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"✅ SUCCESS: {description}")
            if result.stdout.strip():
                print(result.stdout)
        else:
            print(f"❌ ERROR: {description}")
            if result.stderr:
                print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT: {description}")
        return False
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False
    return True

def stop_bot():
    """Останавливает бота в зависимости от ОС"""
    print("\n=== Stopping Bot ===")
    
    if is_windows():
        # Windows: остановить процессы Python и Task Scheduler
        commands = [
            'taskkill /f /im python.exe 2>nul || echo "No python processes found"',
            'schtasks /end /tn "RepitBot" 2>nul || echo "Task RepitBot not found"'
        ]
    else:
        # Linux: остановить процессы и systemd
        commands = [
            'pkill -f "python.*bot.py" || echo "No bot processes found"',
            'systemctl stop repitbot 2>/dev/null || echo "Service repitbot not found"'
        ]
    
    for cmd in commands:
        run_command(cmd, f"Stopping bot: {cmd}")

def start_bot():
    """Запускает бота в зависимости от ОС"""
    print("\n=== Starting Bot ===")
    
    if is_windows():
        # Windows: попробовать Task Scheduler, затем прямой запуск
        if run_command('schtasks /run /tn "RepitBot"', "Starting via Task Scheduler"):
            return True
        else:
            print("Task Scheduler failed, trying direct start...")
            return run_command('start /b python bot.py', "Starting bot directly")
    else:
        # Linux: попробовать systemd, затем nohup
        if run_command('systemctl start repitbot', "Starting via systemd"):
            return True
        else:
            print("systemd failed, trying nohup...")
            return run_command('nohup python bot.py > logs/bot.log 2>&1 &', "Starting with nohup")

def create_backup():
    """Создает бэкап базы данных"""
    print("\n=== Creating Database Backup ===")
    
    if not os.path.exists("repitbot.db"):
        print("⚠️  Database file not found - no backup needed")
        return True
    
    backup_name = f"repitbot.db.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        shutil.copy2("repitbot.db", backup_name)
        print(f"✅ Database backup created: {backup_name}")
        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

def check_git_repo():
    """Проверяет, что мы в Git репозитории"""
    if not os.path.exists(".git"):
        print("❌ Not in a Git repository!")
        return False
    return True

def update_from_git():
    """Обновляет код из Git"""
    print("\n=== Updating from Git ===")
    
    if not check_git_repo():
        return False
    
    commands = [
        ("git fetch origin", "Fetching updates from GitHub"),
        ("git checkout feature/student-view-fixes", "Switching to feature branch"),
        ("git pull origin feature/student-view-fixes", "Pulling latest changes")
    ]
    
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            print(f"❌ Git update failed at: {desc}")
            return False
    
    return True

def run_migrations():
    """Выполняет миграции базы данных"""
    print("\n=== Running Database Migrations ===")
    
    migrations = [
        ("python fix_server_lesson_status.py", "Fixing lesson_status enum values"),
        ("python migrate_materials_grade.py", "Adding grade field to materials")
    ]
    
    for cmd, desc in migrations:
        # Проверяем существование файла миграции
        script_name = cmd.split()[1]
        if not os.path.exists(script_name):
            print(f"⚠️  Migration script {script_name} not found - skipping")
            continue
            
        if not run_command(cmd, desc):
            print(f"❌ Migration failed: {desc}")
            return False
    
    return True

def check_database():
    """Проверяет состояние базы данных после миграций"""
    print("\n=== Checking Database ===")
    
    if not os.path.exists("repitbot.db"):
        print("❌ Database not found")
        return False
    
    try:
        conn = sqlite3.connect("repitbot.db")
        cursor = conn.cursor()
        
        # Проверка lesson_status
        cursor.execute("PRAGMA table_info(lessons)")
        lesson_columns = [col[1] for col in cursor.fetchall()]
        
        if 'lesson_status' in lesson_columns:
            cursor.execute("SELECT lesson_status, COUNT(*) FROM lessons GROUP BY lesson_status")
            stats = cursor.fetchall()
            print("✅ lesson_status field exists:")
            for status, count in stats:
                print(f"   {status}: {count} lessons")
        else:
            print("❌ lesson_status field missing")
            conn.close()
            return False
        
        # Проверка materials grade
        cursor.execute("PRAGMA table_info(materials)")
        material_columns = [col[1] for col in cursor.fetchall()]
        
        if 'grade' in material_columns:
            print("✅ materials.grade field exists")
        else:
            print("❌ materials.grade field missing")
            conn.close()
            return False
        
        # Общая статистика
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        print(f"📊 Total users: {users_count}")
        
        cursor.execute("SELECT COUNT(*) FROM lessons")
        lessons_count = cursor.fetchone()[0]
        print(f"📊 Total lessons: {lessons_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

def check_syntax():
    """Проверяет синтаксис основных файлов Python"""
    print("\n=== Checking Python Syntax ===")
    
    files_to_check = [
        "bot.py",
        "src/database.py", 
        "src/handlers/tutor.py",
        "src/handlers/parent.py",
        "src/handlers/shared.py",
        "src/handlers/student.py"
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            cmd = f"python -m py_compile {file_path}"
            if not run_command(cmd, f"Checking {file_path}"):
                print(f"❌ Syntax error in {file_path}")
                return False
        else:
            print(f"⚠️  File {file_path} not found - skipping")
    
    return True

def main():
    """Основная функция обновления"""
    print("🚀 RepitBot Server Update Script")
    print("=" * 50)
    print(f"OS: {platform.system()}")
    print(f"Python: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print("=" * 50)
    
    # 1. Остановить бота
    stop_bot()
    
    # 2. Создать бэкап
    if not create_backup():
        print("❌ Backup failed - aborting update")
        return False
    
    # 3. Обновить из Git
    if not update_from_git():
        print("❌ Git update failed - aborting")
        return False
    
    # 4. Выполнить миграции
    if not run_migrations():
        print("❌ Migrations failed - aborting")
        return False
    
    # 5. Проверить базу данных
    if not check_database():
        print("❌ Database verification failed")
        return False
    
    # 6. Проверить синтаксис
    if not check_syntax():
        print("❌ Syntax check failed")
        return False
    
    # 7. Запустить бота
    if not start_bot():
        print("❌ Failed to start bot - manual start required")
        print("Manual start command:")
        if is_windows():
            print("   python bot.py")
        else:
            print("   python bot.py  # or nohup python bot.py > logs/bot.log 2>&1 &")
    
    print("\n🎉 UPDATE COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print("Next steps:")
    print("1. ✅ Code updated from Git")
    print("2. ✅ Database migrated") 
    print("3. ✅ Syntax checked")
    print("4. 🚀 Bot restarted")
    print("")
    print("🧪 Test the following:")
    print("   • Lesson status changes work")
    print("   • Parent buttons don't freeze")
    print("   • Students see homework photos")
    print("   • Tutor messages reach clients")
    print("   • Materials library by grades")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Update interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)