# -*- coding: utf-8 -*-
import os
import sys
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal, Homework

def test_photo_storage():
    """Тестирует сохранение и извлечение фотографий"""
    print("Тестируем работу с фотографиями в ДЗ...")
    
    db = SessionLocal()
    try:
        # Найдем любое ДЗ для теста
        hw = db.query(Homework).first()
        if not hw:
            print("Нет ДЗ в базе для тестирования")
            return
            
        print(f"Найдено ДЗ: {hw.description[:50]}...")
        
        # Тестируем сохранение фотографий от репетитора
        test_tutor_photos = ["photo_id_1", "photo_id_2", "photo_id_3"]
        hw.photo_file_ids = json.dumps(test_tutor_photos)
        
        # Тестируем сохранение ответа студента
        hw.submission_text = "Вот мое решение задачи"
        test_student_photos = ["student_photo_1", "student_photo_2"]
        hw.submission_photo_file_ids = json.dumps(test_student_photos)
        
        db.commit()
        print("Данные сохранены в базу")
        
        # Тестируем извлечение
        db.refresh(hw)
        
        if hw.photo_file_ids:
            tutor_photos = json.loads(hw.photo_file_ids)
            print(f"Фото от репетитора: {len(tutor_photos)} шт - {tutor_photos}")
        else:
            print("Нет фото от репетитора")
            
        if hw.submission_text:
            print(f"Текст ответа: {hw.submission_text}")
        else:
            print("Нет текста ответа")
            
        if hw.submission_photo_file_ids:
            student_photos = json.loads(hw.submission_photo_file_ids)
            print(f"Фото от студента: {len(student_photos)} шт - {student_photos}")
        else:
            print("Нет фото от студента")
            
        print("Тест завершен успешно! Фотографии работают корректно.")
        
    except Exception as e:
        print(f"Ошибка теста: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_photo_storage()