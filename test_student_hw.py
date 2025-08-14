# -*- coding: utf-8 -*-
import os
import sys
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal, Homework, Lesson, User, UserRole, HomeworkStatus

def test_student_homework_view():
    """Тестирует просмотр ДЗ студентом"""
    print("Тестируем просмотр ДЗ студентом...")
    
    db = SessionLocal()
    try:
        # Найдем студента
        student = db.query(User).filter(User.role == UserRole.STUDENT).first()
        if not student:
            print("Студент не найден")
            return
            
        print(f"Студент найден: {student.full_name}")
        
        # Найдем его ДЗ
        homeworks = db.query(Homework).join(Lesson).filter(
            Lesson.student_id == student.id
        ).all()
        
        print(f"Найдено ДЗ: {len(homeworks)}")
        
        for hw in homeworks:
            print(f"\nДЗ ID: {hw.id}")
            print(f"Тема урока: {hw.lesson.topic}")
            print(f"Описание: {hw.description[:50]}...")
            print(f"Статус: {hw.status}")
            
            if hw.photo_file_ids:
                try:
                    photos = json.loads(hw.photo_file_ids)
                    print(f"Фото от репетитора: {len(photos)}")
                except:
                    print("Ошибка чтения фото репетитора")
                    
            if hw.submission_text:
                print(f"Ответ студента: {hw.submission_text[:30]}...")
                
            if hw.submission_photo_file_ids:
                try:
                    photos = json.loads(hw.submission_photo_file_ids)
                    print(f"Фото от студента: {len(photos)}")
                except:
                    print("Ошибка чтения фото студента")
        
        print("\nТест завершен успешно!")
        
    except Exception as e:
        print(f"Ошибка теста: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_student_homework_view()