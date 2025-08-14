# -*- coding: utf-8 -*-
"""
Простой тестовый скрипт для проверки работы кнопок бота.
Тестирует callback_query обработку для репетитора.
"""
import asyncio
import logging
from telegram import Update, CallbackQuery, User, Message, Chat
from telegram.ext import ContextTypes, Application
from unittest.mock import MagicMock, AsyncMock

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_button_callbacks():
    """Тестирует обработку callback_query"""
    try:
        # Импортируем обработчик
        from src.handlers.enhanced_tutor import handle_tutor_callbacks
        from src.database import get_user_by_telegram_id
        
        # Проверяем, есть ли пользователь-репетитор в БД
        tutor_user = get_user_by_telegram_id(1229333908)  # ID Марины из БД
        if not tutor_user:
            print("ERROR: Репетитор не найден в БД. Проверьте создание тестовых данных.")
            return
            
        print(f"SUCCESS: Найден репетитор: {tutor_user.full_name} (ID: {tutor_user.telegram_id})")
        
        # Создаем мок объекты для тестирования
        user = User(id=tutor_user.telegram_id, first_name="Test", is_bot=False)
        chat = Chat(id=tutor_user.telegram_id, type="private")
        message = Message(message_id=1, date=None, chat=chat)
        
        # Создаем мок callback_query
        callback_query = MagicMock(spec=CallbackQuery)
        callback_query.id = "test_callback"
        callback_query.from_user = user
        callback_query.chat_instance = "test"
        callback_query.data = "test_button"
        callback_query.message = message
        
        # Мокаем методы callback_query
        callback_query.answer = AsyncMock()
        callback_query.edit_message_text = AsyncMock()
        
        # Создаем мок Update
        update = Update(
            update_id=1,
            effective_user=user,
            callback_query=callback_query
        )
        
        # Создаем мок Context
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        
        print("TESTING: Тестируем обработку test_button callback...")
        
        # Вызываем обработчик
        await handle_tutor_callbacks(update, context)
        
        # Проверяем, что методы были вызваны
        assert callback_query.answer.called, "callback_query.answer() не был вызван"
        assert callback_query.edit_message_text.called, "callback_query.edit_message_text() не был вызван"
        
        print("SUCCESS: Тест callback обработки прошел успешно!")
        
        # Проверяем аргументы edit_message_text
        call_args = callback_query.edit_message_text.call_args
        if call_args:
            message_text = call_args[0][0]  # Первый позиционный аргумент
            print(f"MESSAGE: {message_text}")
        
        print("SUCCESS: ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        
    except Exception as e:
        print(f"ERROR: Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Главная функция тестирования"""
    print("START: Запуск тестов callback обработки...")
    await test_button_callbacks()

if __name__ == "__main__":
    asyncio.run(main())