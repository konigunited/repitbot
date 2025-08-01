# -*- coding: utf-8 -*-
import argparse
import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError
from sqlalchemy import select
from database import SessionLocal, User, UserRole

async def send_broadcast_message(bot_token: str, message: str):
    """
    Отправляет сообщение всем ученикам и родителям,
    у которых есть привязанный telegram_id.
    """
    bot = Bot(token=bot_token)
    db = SessionLocal()
    try:
        # Выбираем всех пользователей, кроме репетиторов, у кого есть telegram_id
        query = select(User).where(
            User.role.in_([UserRole.STUDENT, UserRole.PARENT]),
            User.telegram_id.isnot(None)
        )
        users_to_notify = db.scalars(query).all()

        if not users_to_notify:
            print("Не найдено пользователей для рассылки.")
            return

        print(f"Начинаем рассылку для {len(users_to_notify)} пользователей...")
        
        successful_sends = 0
        failed_sends = 0

        for user in users_to_notify:
            try:
                await bot.send_message(chat_id=user.telegram_id, text=message)
                print(f"Сообщение успешно отправлено пользователю: {user.full_name} (ID: {user.telegram_id})")
                successful_sends += 1
            except TelegramError as e:
                print(f"Ошибка при отправке пользователю {user.full_name} (ID: {user.telegram_id}): {e}")
                failed_sends += 1
            await asyncio.sleep(0.1) # Небольшая задержка, чтобы не перегружать API

        print("\n--- Рассылка завершена ---")
        print(f"Успешно отправлено: {successful_sends}")
        print(f"Не удалось отправить: {failed_sends}")

    finally:
        db.close()

if __name__ == "__main__":
    load_dotenv()
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("Необходимо установить переменную окружения TELEGRAM_TOKEN")

    parser = argparse.ArgumentParser(description="Сделать массовую рассылку пользователям бота.")
    parser.add_argument("message", type=str, help="Текст сообщения для рассылки (в кавычках).")
    
    args = parser.parse_args()
    
    asyncio.run(send_broadcast_message(token, args.message))
