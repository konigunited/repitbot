#!/usr/bin/env python3
import subprocess
import sys
import os

def kill_python_processes():
    """Убивает все процессы Python кроме текущего"""
    current_pid = os.getpid()
    
    try:
        # Для Windows
        if sys.platform == "win32":
            # Получаем список всех Python процессов
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                capture_output=True, text=True, encoding='cp866'
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # Пропускаем заголовок
                    if line:
                        parts = line.split('","')
                        if len(parts) >= 2:
                            pid = parts[1].strip('"')
                            if pid.isdigit() and int(pid) != current_pid:
                                try:
                                    subprocess.run(['taskkill', '/F', '/PID', pid], 
                                                 capture_output=True)
                                    print(f"Убит процесс Python с PID: {pid}")
                                except:
                                    pass
        else:
            # Для Linux/Mac
            result = subprocess.run(['pgrep', 'python'], capture_output=True, text=True)
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid.isdigit() and int(pid) != current_pid:
                        try:
                            subprocess.run(['kill', '-9', pid], capture_output=True)
                            print(f"Убит процесс Python с PID: {pid}")
                        except:
                            pass
                            
        print("Все процессы Python завершены")
        
    except Exception as e:
        print(f"Ошибка при завершении процессов: {e}")

if __name__ == "__main__":
    kill_python_processes()