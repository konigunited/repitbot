#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отладка потока добавления материала
"""
import asyncio
from unittest.mock import MagicMock, AsyncMock
from src.database import SessionLocal, get_user_by_telegram_id, User, UserRole

async def debug_material_flow():
    """Отлаживаем поток добавления материала"""
    
    # Найдем любого существующего тьютора
    db = SessionLocal()
    test_user = db.query(User).filter(User.role == UserRole.TUTOR).first()
    db.close()
    
    if test_user:
        print(f"Используем тьютора: {test_user.full_name} (ID: {test_user.telegram_id})")
    else:
        print("Нет тьюторов в базе данных!")
        return
    
    # Создаем мок-объекты
    update = MagicMock()
    update.effective_user.id = test_user.telegram_id
    update.callback_query = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.data = "select_grade_5"
    
    context = MagicMock()
    context.user_data = {}
    
    print("=== Шаг 1: tutor_add_material_start ===")
    from src.handlers.tutor import tutor_add_material_start
    
    try:
        result = await tutor_add_material_start(update, context)
        print(f"Результат: {result}")
        print(f"update.callback_query.edit_message_text вызван: {update.callback_query.edit_message_text.called}")
        
        # Проверим что было передано
        if update.callback_query.edit_message_text.called:
            call_args = update.callback_query.edit_message_text.call_args
            print(f"Аргументы: {call_args}")
            
    except Exception as e:
        print(f"Ошибка: {e}")
    
    print("\n=== Шаг 2: tutor_get_material_grade ===")
    from src.handlers.tutor import tutor_get_material_grade
    
    try:
        result = await tutor_get_material_grade(update, context)
        print(f"Результат: {result}")
        print(f"context.user_data после: {context.user_data}")
        
    except Exception as e:
        print(f"Ошибка: {e}")
    
    print("\n=== Проверим константы состояний ===")
    from src.handlers.tutor import ADD_MATERIAL_GRADE, ADD_MATERIAL_TITLE
    print(f"ADD_MATERIAL_GRADE = {ADD_MATERIAL_GRADE}")
    print(f"ADD_MATERIAL_TITLE = {ADD_MATERIAL_TITLE}")

if __name__ == "__main__":
    print("Отлаживаем поток добавления материала...")
    asyncio.run(debug_material_flow())