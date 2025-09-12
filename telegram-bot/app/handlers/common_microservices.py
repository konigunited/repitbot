# -*- coding: utf-8 -*-
"""
Telegram Bot - Common Handlers (Microservices Version)
Общие обработчики с интеграцией микросервисов
"""
import re
import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

# Импорты микросервисных клиентов
from ..services.user_service_client import (
    get_user_by_telegram_id, 
    validate_access_code,
    check_user_service_health
)
from ..services.auth_service_client import (
    authenticate_user_by_access_code,
    check_auth_service_health,
    token_manager
)

# Импорты для fallback режима
from ...src.database import get_user_by_telegram_id as fallback_get_user
from ...src.keyboards import tutor_main_keyboard, student_main_keyboard, parent_main_keyboard

logger = logging.getLogger(__name__)

# Feature flags для переключения между микросервисами и монолитом
ENABLE_MICROSERVICES = True  # В будущем можно вынести в переменные окружения
FALLBACK_TO_MONOLITH = True

async def check_microservices_health() -> dict:
    """Проверка здоровья микросервисов"""
    try:
        user_health = await check_user_service_health()
        auth_health = await check_auth_service_health()
        
        return {
            'user_service': user_health,
            'auth_service': auth_health,
            'all_healthy': user_health and auth_health
        }
    except Exception as e:
        logger.error(f"Failed to check microservices health: {e}")
        return {
            'user_service': False,
            'auth_service': False,
            'all_healthy': False
        }

def generate_access_code(length=8):
    """Генерация кода доступа (совместимость с монолитом)"""
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

async def check_user_role(update: Update, required_role: str) -> bool:
    """Проверяет роль пользователя"""
    try:
        if ENABLE_MICROSERVICES:
            user_data = await get_user_by_telegram_id(update.effective_user.id)
            return user_data and user_data.get('role') == required_role
        else:
            # Fallback к монолиту
            user = fallback_get_user(update.effective_user.id)
            return user and user.role.value == required_role
    except Exception as e:
        logger.error(f"Failed to check user role: {e}")
        # При ошибке возвращаем False для безопасности
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        # Сначала проверяем микросервисы
        if ENABLE_MICROSERVICES:
            user_data = await get_user_by_telegram_id(update.effective_user.id)
            
            if user_data:
                logger.info(f"User {user_data['id']} found in microservices")
                await show_main_menu_microservices(update, context, user_data)
                return
            else:
                logger.info(f"User with telegram_id {update.effective_user.id} not found in microservices")
        
        # Fallback к монолиту
        if FALLBACK_TO_MONOLITH:
            user = fallback_get_user(update.effective_user.id)
            if user:
                logger.info(f"User {user.id} found in monolith (fallback)")
                await show_main_menu_monolith(update, context, user)
                return
        
        # Пользователь не найден
        await update.message.reply_text(
            "👋 Здравствуйте! Я бот-помощник для репетитора.\n\n"
            "Введите ваш уникальный код доступа, чтобы начать."
        )
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при запуске. Попробуйте еще раз."
        )

async def handle_access_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кода доступа с поддержкой микросервисов"""
    try:
        # Проверяем, есть ли уже пользователь в системе
        if ENABLE_MICROSERVICES:
            user_data = await get_user_by_telegram_id(update.effective_user.id)
            if user_data:
                await show_main_menu_microservices(update, context, user_data)
                return
        
        if FALLBACK_TO_MONOLITH:
            user = fallback_get_user(update.effective_user.id)
            if user:
                await show_main_menu_monolith(update, context, user)
                return
        
        # Проверяем формат кода доступа
        code = update.message.text.strip().upper()
        if not re.match(r'^[A-Z0-9]{6,10}$', code):
            await update.message.reply_text(
                "❌ Неверный формат кода доступа.\n"
                "Код должен содержать только буквы и цифры (6-10 символов)."
            )
            return
        
        # Аутентификация через микросервисы
        if ENABLE_MICROSERVICES:
            auth_result = await authenticate_user_by_access_code(
                code, 
                update.effective_user.id,
                update.effective_user.username
            )
            
            if auth_result:
                # Получаем данные пользователя
                user_data = await get_user_by_telegram_id(update.effective_user.id)
                
                if user_data:
                    await update.message.reply_text(
                        f"✅ Добро пожаловать, {user_data['full_name']}!\n"
                        f"Ваша роль: {user_data['role']}"
                    )
                    await show_main_menu_microservices(update, context, user_data)
                    return
            else:
                logger.warning(f"Microservices authentication failed for code {code[:3]}***")
        
        # Fallback к валидации через монолит
        if FALLBACK_TO_MONOLITH:
            result = await validate_access_code(
                code, 
                update.effective_user.id,
                update.effective_user.username
            )
            
            if result.get('success'):
                # Перезагружаем пользователя
                user = fallback_get_user(update.effective_user.id)
                if user:
                    await update.message.reply_text(
                        f"✅ Добро пожаловать, {user.full_name}!\n"
                        f"Ваша роль: {user.role.value}"
                    )
                    await show_main_menu_monolith(update, context, user)
                    return
        
        # Неверный код доступа
        await update.message.reply_text(
            "❌ Неверный код доступа. Проверьте правильность ввода и попробуйте еще раз."
        )
        
    except Exception as e:
        logger.error(f"Error in handle_access_code: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при проверке кода доступа. Попробуйте позже."
        )

async def show_main_menu_microservices(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
    """Показ главного меню через микросервисы"""
    try:
        # Определяем, откуда пришел запрос
        if update.message:
            message = update.message
        elif update.callback_query:
            message = update.callback_query.message
            await update.callback_query.answer()
        else:
            return
        
        role = user_data.get('role')
        full_name = user_data.get('full_name', 'Пользователь')
        
        if role == 'tutor':
            await message.reply_text(
                f"👨‍🏫 Главное меню репетитора\n"
                f"Добро пожаловать, {full_name}!",
                reply_markup=tutor_main_keyboard()
            )
        elif role == 'student':
            await message.reply_text(
                f"👨‍🎓 Главное меню ученика\n"
                f"Добро пожаловать, {full_name}!",
                reply_markup=student_main_keyboard()
            )
        elif role == 'parent':
            await message.reply_text(
                f"👨‍👩‍👧‍👦 Главное меню родителя\n"
                f"Добро пожаловать, {full_name}!",
                reply_markup=parent_main_keyboard()
            )
        else:
            await message.reply_text(
                f"👋 Добро пожаловать, {full_name}!\n"
                "Роль не определена. Обратитесь к администратору."
            )
            
        logger.info(f"Showed main menu for user {user_data['id']} via microservices")
        
    except Exception as e:
        logger.error(f"Error showing main menu (microservices): {e}")
        await update.message.reply_text(
            "❌ Ошибка при загрузке главного меню."
        )

async def show_main_menu_monolith(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """Показ главного меню через монолит (fallback)"""
    try:
        # Определяем, откуда пришел запрос
        if update.message:
            message = update.message
        elif update.callback_query:
            message = update.callback_query.message
            await update.callback_query.answer()
        else:
            return
        
        role = user.role.value
        full_name = user.full_name
        
        if role == 'tutor':
            await message.reply_text(
                f"👨‍🏫 Главное меню репетитора\n"
                f"Добро пожаловать, {full_name}!",
                reply_markup=tutor_main_keyboard()
            )
        elif role == 'student':
            await message.reply_text(
                f"👨‍🎓 Главное меню ученика\n"
                f"Добро пожаловать, {full_name}!",
                reply_markup=student_main_keyboard()
            )
        elif role == 'parent':
            await message.reply_text(
                f"👨‍👩‍👧‍👦 Главное меню родителя\n"
                f"Добро пожаловать, {full_name}!",
                reply_markup=parent_main_keyboard()
            )
        
        logger.info(f"Showed main menu for user {user.id} via monolith (fallback)")
        
    except Exception as e:
        logger.error(f"Error showing main menu (monolith): {e}")
        await update.message.reply_text(
            "❌ Ошибка при загрузке главного меню."
        )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Универсальная функция показа главного меню"""
    try:
        # Пытаемся получить пользователя через микросервисы
        if ENABLE_MICROSERVICES:
            user_data = await get_user_by_telegram_id(update.effective_user.id)
            if user_data:
                await show_main_menu_microservices(update, context, user_data)
                return
        
        # Fallback к монолиту
        if FALLBACK_TO_MONOLITH:
            user = fallback_get_user(update.effective_user.id)
            if user:
                await show_main_menu_monolith(update, context, user)
                return
        
        # Пользователь не найден
        await update.message.reply_text(
            "Пожалуйста, введите код доступа для начала работы."
        )
        
    except Exception as e:
        logger.error(f"Error in show_main_menu: {e}")
        await update.message.reply_text(
            "❌ Ошибка при загрузке меню. Попробуйте еще раз."
        )

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена разговора"""
    await update.message.reply_text(
        "❌ Операция отменена.",
        reply_markup=ReplyKeyboardRemove()
    )
    await show_main_menu(update, context)
    return ConversationHandler.END

# === Дополнительные функции для мониторинга ===

async def show_service_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ статуса микросервисов (для администраторов)"""
    try:
        # Проверяем права доступа
        if not await check_user_role(update, 'tutor'):
            await update.message.reply_text("❌ Недостаточно прав для просмотра статуса сервисов.")
            return
        
        health = await check_microservices_health()
        
        status_message = "📊 **Статус микросервисов:**\n\n"
        
        if health['user_service']:
            status_message += "✅ User Service: Работает\n"
        else:
            status_message += "❌ User Service: Недоступен\n"
        
        if health['auth_service']:
            status_message += "✅ Auth Service: Работает\n"
        else:
            status_message += "❌ Auth Service: Недоступен\n"
        
        status_message += f"\n🔄 Fallback режим: {'Включен' if FALLBACK_TO_MONOLITH else 'Отключен'}"
        status_message += f"\n🎯 Микросервисы: {'Включены' if ENABLE_MICROSERVICES else 'Отключены'}"
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error showing service status: {e}")
        await update.message.reply_text("❌ Ошибка при получении статуса сервисов.")

# === Утилиты для feature flags ===

def enable_microservices(enabled: bool = True):
    """Включение/отключение микросервисов"""
    global ENABLE_MICROSERVICES
    ENABLE_MICROSERVICES = enabled
    logger.info(f"Microservices {'enabled' if enabled else 'disabled'}")

def enable_fallback(enabled: bool = True):
    """Включение/отключение fallback режима"""
    global FALLBACK_TO_MONOLITH
    FALLBACK_TO_MONOLITH = enabled
    logger.info(f"Fallback mode {'enabled' if enabled else 'disabled'}")

async def get_current_user_universal(telegram_id: int) -> dict:
    """Универсальная функция получения пользователя"""
    try:
        # Пытаемся через микросервисы
        if ENABLE_MICROSERVICES:
            user_data = await get_user_by_telegram_id(telegram_id)
            if user_data:
                return {
                    'source': 'microservices',
                    'user': user_data
                }
        
        # Fallback к монолиту
        if FALLBACK_TO_MONOLITH:
            user = fallback_get_user(telegram_id)
            if user:
                return {
                    'source': 'monolith',
                    'user': {
                        'id': user.id,
                        'telegram_id': user.telegram_id,
                        'username': user.username,
                        'full_name': user.full_name,
                        'role': user.role.value,
                        'access_code': user.access_code,
                        'points': user.points,
                        'streak_days': user.streak_days,
                        'total_study_hours': user.total_study_hours
                    }
                }
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting user {telegram_id}: {e}")
        return None