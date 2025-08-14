# -*- coding: utf-8 -*-
"""
Тест генерации графиков
"""
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

def test_chart_generation():
    """Тестируем генерацию графиков"""
    print("Testing chart generation...")
    
    try:
        from src.chart_generator import generate_progress_chart
        from src.database import SessionLocal, User, Lesson, AttendanceStatus
        from datetime import datetime
        
        # Проверяем студента ID 6
        db = SessionLocal()
        student = db.query(User).filter(User.id == 6).first()
        
        if not student:
            print("ERROR: Student ID 6 not found")
            return False
        
        print(f"Testing chart for student: {student.full_name} (ID: {student.id})")
        
        # Проверяем есть ли у студента уроки
        lessons = db.query(Lesson).filter(Lesson.student_id == 6).all()
        print(f"Found {len(lessons)} lessons for student")
        
        if len(lessons) == 0:
            # Создаем тестовый урок
            test_lesson = Lesson(
                student_id=6,
                date=datetime.now(),
                topic="Тестовый урок для графика",
                attendance_status=AttendanceStatus.ATTENDED,
                skills_developed="Тестовые навыки"
            )
            db.add(test_lesson)
            db.commit()
            print("Created test lesson for chart generation")
        
        db.close()
        
        # Пытаемся сгенерировать график
        chart_path = generate_progress_chart(6)
        
        if chart_path and os.path.exists(chart_path):
            print(f"SUCCESS: Chart generated at {chart_path}")
            
            # Проверяем размер файла
            file_size = os.path.getsize(chart_path)
            print(f"Chart file size: {file_size} bytes")
            
            # Удаляем тестовый файл
            os.remove(chart_path)
            print("Test chart file cleaned up")
            
            return True
        else:
            print("ERROR: Chart generation failed")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_matplotlib_availability():
    """Проверяем наличие matplotlib"""
    print("Testing matplotlib availability...")
    
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        print("SUCCESS: matplotlib is available")
        
        # Тестируем создание простого графика
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot([1, 2, 3], [1, 4, 2])
        ax.set_title('Test Chart')
        
        test_path = "test_chart.png"
        plt.savefig(test_path)
        plt.close()
        
        if os.path.exists(test_path):
            os.remove(test_path)
            print("SUCCESS: matplotlib chart creation works")
            return True
        else:
            print("ERROR: matplotlib chart save failed")
            return False
            
    except Exception as e:
        print(f"ERROR: matplotlib not working: {e}")
        return False

def main():
    print("=== Chart Generation Test ===")
    load_dotenv()
    
    tests = [
        ("matplotlib availability", test_matplotlib_availability),
        ("chart generation", test_chart_generation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name.upper()}:")
        if test_func():
            passed += 1
            print("PASSED")
        else:
            print("FAILED")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: Chart generation should work!")
    else:
        print("WARNING: Chart generation has issues")

if __name__ == "__main__":
    main()