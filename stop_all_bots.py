# -*- coding: utf-8 -*-
import subprocess
import sys
import time
import os

def kill_python_processes():
    """Останавливает все процессы Python кроме текущего"""
    current_pid = os.getpid()
    print(f"Текущий PID: {current_pid}")
    
    try:
        # Получаем список всех Python процессов
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
            capture_output=True, text=True, encoding='cp866'
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            killed_count = 0
            
            for line in lines[1:]:  # Пропускаем заголовок
                if line:
                    parts = line.split('","')
                    if len(parts) >= 2:
                        pid_str = parts[1].strip('"')
                        if pid_str.isdigit():
                            pid = int(pid_str)
                            if pid != current_pid:
                                try:
                                    subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                                                 capture_output=True)
                                    print(f"Остановлен процесс Python PID: {pid}")
                                    killed_count += 1
                                except:
                                    pass
            
            print(f"Остановлено процессов: {killed_count}")
            
        else:
            print("Не удалось получить список процессов")
            
    except Exception as e:
        print(f"Ошибка: {e}")

def main():
    print("=== ОСТАНОВКА ВСЕХ БОТОВ ===")
    kill_python_processes()
    
    print("\nОжидание 5 секунд...")
    time.sleep(5)
    
    print("\nОчистка webhook...")
    try:
        subprocess.run([sys.executable, 'clear_webhook.py'], check=True)
        print("Webhook очищен")
    except:
        print("Не удалось очистить webhook")
    
    print("\n=== ГОТОВО ===")
    print("Теперь можно запустить бота: python bot.py")

if __name__ == "__main__":
    main()