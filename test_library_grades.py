#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест функциональности библиотеки с классами
"""
import asyncio
from unittest.mock import MagicMock
from src.database import SessionLocal, Material
from src.handlers.tutor import tutor_library_by_grade
from src.handlers.student import student_library_by_grade

async def test_library_functions():
    """Тестируем новые функции библиотеки"""
    
    # Создаем тестовые материалы если их нет
    db = SessionLocal()
    
    # Проверим есть ли материалы
    materials_count = db.query(Material).count()
    print(f"Всего материалов в базе: {materials_count}")
    
    if materials_count == 0:
        # Создаем тестовые материалы
        test_materials = [
            Material(title="Алгебра 5 класс", description="Основы алгебры", grade=5, link="https://example.com/5"),
            Material(title="Геометрия 7 класс", description="Треугольники", grade=7, link="https://example.com/7"),
            Material(title="Математика 9 класс", description="Подготовка к ОГЭ", grade=9, link=None),
        ]
        
        for material in test_materials:
            db.add(material)
        db.commit()
        print("Создали тестовые материалы")
    
    # Проверим материалы по классам
    for grade in [5, 7, 9]:
        materials = db.query(Material).filter(Material.grade == grade).all()
        print(f"Класс {grade}: {len(materials)} материалов")
        for material in materials:
            print(f"  - [{material.grade}кл] {material.title}")
    
    db.close()
    
    print("\nТестируем callback handlers...")
    
    # Создаем мок-объекты
    update = MagicMock()
    update.callback_query.edit_message_text = MagicMock()
    context = MagicMock()
    
    # Тестируем функцию для тьюторов
    try:
        await tutor_library_by_grade(update, context, "5")
        print("tutor_library_by_grade(grade=5) работает")
    except Exception as e:
        print(f"tutor_library_by_grade(grade=5) ошибка: {e}")
    
    try:
        await tutor_library_by_grade(update, context, "all")
        print("tutor_library_by_grade(grade='all') работает")
    except Exception as e:
        print(f"tutor_library_by_grade(grade='all') ошибка: {e}")
    
    # Тестируем функцию для студентов
    try:
        await student_library_by_grade(update, context, "7")
        print("student_library_by_grade(grade=7) работает")
    except Exception as e:
        print(f"student_library_by_grade(grade=7) ошибка: {e}")
    
    try:
        await student_library_by_grade(update, context, "all")
        print("student_library_by_grade(grade='all') работает")
    except Exception as e:
        print(f"student_library_by_grade(grade='all') ошибка: {e}")

if __name__ == "__main__":
    print("Тестируем библиотеку с классами...")
    asyncio.run(test_library_functions())
    print("Тест завершён!")