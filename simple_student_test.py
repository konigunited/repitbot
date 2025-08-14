# -*- coding: utf-8 -*-
import os
import asyncio
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Simple imports for testing
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.handlers import show_homework_menu, student_view_homework, button_handler
from src.keyboards import STUDENT_BUTTONS

async def simple_start(update, context):
    await update.message.reply_text(
        "🧪 Простой тест-бот для проверки студенческого ДЗ!\n"
        "Напишите /homework для просмотра ДЗ"
    )

async def test_homework(update, context):
    # Имитируем студента
    update.effective_user.id = 1  # ID тестового студента в базе
    await show_homework_menu(update, context)

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", simple_start))
    app.add_handler(CommandHandler("homework", test_homework))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🧪 Простой тест-бот запущен для проверки ДЗ...")
    print("Команды: /start, /homework")
    app.run_polling()

if __name__ == "__main__":
    main()