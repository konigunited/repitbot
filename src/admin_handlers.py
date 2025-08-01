# -*- coding: utf-8 -*-
from telegram import Update
from telegram.ext import ContextTypes
from .database import SessionLocal, User, UserRole
import random
import string

def generate_access_code(length=8):
    """Генерирует случайный код доступа."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for i in range(length))

async def add_tutor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавляет нового репетитора в базу данных."""
    # Проверка, что команду вызывает администратор (можно добавить ID администратора)
    # if update.effective_user.id != YOUR_ADMIN_ID:
    #     await update.message.reply_text("У вас нет прав для выполнения этой команды.")
    #     return

    try:
        # Пример: /add_tutor "Иванов Иван Иванович"
        full_name = " ".join(context.args)
        if not full_name:
            await update.message.reply_text("Пожалуйста, укажите ФИО репетитора. \nПример: /add_tutor \"Иванов Иван Иванович\"")
            return

        db = SessionLocal()
        
        # Проверяем, не существует ли уже такой репетитор
        existing_tutor = db.query(User).filter(User.full_name == full_name, User.role == UserRole.TUTOR).first()
        if existing_tutor:
            await update.message.reply_text(f"Репетитор с именем '{full_name}' уже существует.")
            return

        access_code = generate_access_code()
        
        new_tutor = User(
            full_name=full_name,
            role=UserRole.TUTOR,
            access_code=access_code
        )
        
        db.add(new_tutor)
        db.commit()
        
        await update.message.reply_text(
            f"✅ Репетитор '{full_name}' успешно добавлен.\n"
            f"🔑 Уникальный код доступа: `{access_code}`\n\n"
            "Передайте этот код репетитору для входа в систему."
        )
        
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {e}")
    finally:
        db.close()

async def add_parent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавляет нового родителя в базу данных."""
    try:
        full_name = " ".join(context.args)
        if not full_name:
            await update.message.reply_text("Пожалуйста, укажите ФИО родителя. \nПример: /add_parent \"Петрова Мария Ивановна\"")
            return

        db = SessionLocal()
        
        existing_parent = db.query(User).filter(User.full_name == full_name, User.role == UserRole.PARENT).first()
        if existing_parent:
            await update.message.reply_text(f"Родитель с именем '{full_name}' уже существует.")
            return

        access_code = generate_access_code()
        
        new_parent = User(
            full_name=full_name,
            role=UserRole.PARENT,
            access_code=access_code
        )
        
        db.add(new_parent)
        db.commit()
        
        await update.message.reply_text(
            f"✅ Родитель '{full_name}' успешно добавлен.\n"
            f"🔑 Уникальный код доступа: `{access_code}`\n\n"
            "Передайте этот код родителю. Он понадобится репетитору для привязки ученика."
        )
        
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {e}")
    finally:
        db.close()
