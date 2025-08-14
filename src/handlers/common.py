# -*- coding: utf-8 -*-
import re
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from ..database import (get_user_by_telegram_id, SessionLocal, User, UserRole)
from ..keyboards import tutor_main_keyboard, student_main_keyboard, parent_main_keyboard

# --- Helper Functions ---
def generate_access_code(length=8):
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def check_user_role(update: Update, required_role: UserRole) -> bool:
    """Проверяет роль пользователя"""
    user = get_user_by_telegram_id(update.effective_user.id)
    return user and user.role == required_role

# --- Basic Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_by_telegram_id(update.effective_user.id)
    if user:
        await show_main_menu(update, context)
    else:
        await update.message.reply_text(
            "👋 Здравствуйте! Я бот-помощник для репетитора.\n\n"
            "Введите ваш уникальный код доступа, чтобы начать."
        )

async def handle_access_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, есть ли уже пользователь в системе
    user = get_user_by_telegram_id(update.effective_user.id)
    if user:
        # Пользователь уже зарегистрирован, показываем меню
        await show_main_menu(update, context)
        return
    
    # Проверяем, похож ли текст на код доступа (только буквы и цифры, 6-10 символов)
    code = update.message.text.strip().upper()
    if not re.match(r'^[A-Z0-9]{6,10}$', code):
        await update.message.reply_text(
            "❌ Неверный формат кода доступа.\n"
            "Код должен содержать только буквы и цифры (6-10 символов)."
        )
        return

    # Ищем пользователя с таким кодом доступа
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.access_code == code).first()
        if user:
            # Привязываем Telegram ID к пользователю
            user.telegram_id = update.effective_user.id
            user.username = update.effective_user.username
            db.commit()
            
            await update.message.reply_text(
                f"✅ Добро пожаловать, {user.full_name}!\n"
                f"Ваша роль: {user.role.value}"
            )
            await show_main_menu(update, context)
        else:
            await update.message.reply_text(
                "❌ Неверный код доступа. Проверьте правильность ввода и попробуйте еще раз."
            )
    finally:
        db.close()

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if not user:
        await update.message.reply_text("Пожалуйста, введите код доступа для начала работы.")
        return

    # Определяем, откуда пришел запрос
    if update.message:
        message = update.message
    elif update.callback_query:
        message = update.callback_query.message
        await update.callback_query.answer()
    else:
        return

    if user.role == UserRole.TUTOR:
        await message.reply_text(
            f"👨‍🏫 Главное меню репетитора\n"
            f"Добро пожаловать, {user.full_name}!",
            reply_markup=tutor_main_keyboard()
        )
    elif user.role == UserRole.STUDENT:
        await message.reply_text(
            f"👨‍🎓 Главное меню ученика\n"
            f"Добро пожаловать, {user.full_name}!",
            reply_markup=student_main_keyboard()
        )
    elif user.role == UserRole.PARENT:
        await message.reply_text(
            f"👨‍👩‍👧‍👦 Главное меню родителя\n"
            f"Добро пожаловать, {user.full_name}!",
            reply_markup=parent_main_keyboard()
        )

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Операция отменена.",
        reply_markup=ReplyKeyboardRemove()
    )
    await show_main_menu(update, context)
    return ConversationHandler.END