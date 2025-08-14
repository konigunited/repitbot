# -*- coding: utf-8 -*-
import os
import asyncio
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update, context):
    await update.message.reply_text("Бот запущен! Отправьте фото для теста.")

async def handle_photo(update, context):
    if update.message.photo:
        photo = update.message.photo[-1]
        await update.message.reply_text(f"Получено фото! file_id: {photo.file_id}")
    else:
        await update.message.reply_text("Это не фото")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("Простой тест-бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()