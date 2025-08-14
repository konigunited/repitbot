# -*- coding: utf-8 -*-
import os
import re
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import Forbidden
from telegram.helpers import escape_markdown
from .database import (SessionLocal, User, UserRole, Lesson, Homework, Payment, Material, Achievement,
                      get_user_by_telegram_id, get_all_students, get_user_by_id,
                      get_lesson_by_id, get_homework_by_id,
                      get_lessons_for_student_by_month, get_payments_for_student_by_month,
                      get_all_materials, get_material_by_id, delete_material_by_id,
                      get_dashboard_stats, HomeworkStatus, TopicMastery, AttendanceStatus, get_student_balance,
                      get_student_achievements, award_achievement, update_study_streak, check_points_achievements)
from .keyboards import (tutor_main_keyboard, student_main_keyboard, parent_main_keyboard,
                       tutor_student_list_keyboard, tutor_student_profile_keyboard,
                       tutor_lesson_list_keyboard, tutor_lesson_details_keyboard,
                       tutor_delete_confirm_keyboard, tutor_edit_lesson_status_keyboard,
                       tutor_check_homework_keyboard, tutor_select_student_for_report_keyboard,
                       tutor_select_month_for_report_keyboard, tutor_library_management_keyboard,
                       tutor_select_material_to_delete_keyboard, student_materials_list_keyboard,
                       parent_child_selection_keyboard, parent_child_menu_keyboard,
                       student_select_homework_keyboard, broadcast_confirm_keyboard,
                       student_lesson_list_keyboard, student_lesson_details_keyboard)
from .chart_generator import generate_progress_chart
from telegram.helpers import escape_markdown
from .calendar_util import create_calendar, CustomCalendar
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

# --- Словари для перевода статусов ---
TOPIC_MASTERY_RU = {
    TopicMastery.NOT_LEARNED: "Не усвоено",
    TopicMastery.LEARNED: "Усвоено",
    TopicMastery.MASTERED: "Закреплено",
}

HOMEWORK_STATUS_RU = {
    HomeworkStatus.PENDING: "В работе",
    HomeworkStatus.SUBMITTED: "Сдано, на проверке",
    HomeworkStatus.CHECKED: "Проверено",
}

ATTENDANCE_STATUS_RU = {
    AttendanceStatus.ATTENDED: "Проведен",
    AttendanceStatus.EXCUSED_ABSENCE: "Отменен (уваж. причина)",
    AttendanceStatus.UNEXCUSED_ABSENCE: "Отменен (неуваж. причина)",
    AttendanceStatus.RESCHEDULED: "Перенесен",
}

# --- Состояния для ConversationHandler ---
ADD_STUDENT_NAME, ADD_PARENT_CODE = range(2)
ADD_PARENT_NAME = range(1)
ADD_PAYMENT_AMOUNT = range(1)
ADD_LESSON_TOPIC, ADD_LESSON_DATE, ADD_LESSON_SKILLS = range(3)
RESCHEDULE_LESSON_DATE = range(1)
EDIT_STUDENT_NAME = range(1)
ADD_HW_DESC, ADD_HW_DEADLINE, ADD_HW_LINK, ADD_HW_PHOTOS = range(4)
CHAT_WITH_TUTOR = range(1)
SELECT_STUDENT_FOR_REPORT, SELECT_MONTH_FOR_REPORT = range(2)
ADD_MATERIAL_TITLE, ADD_MATERIAL_LINK, ADD_MATERIAL_DESC = range(3)
SUBMIT_HOMEWORK_FILE = range(1)
BROADCAST_MESSAGE, BROADCAST_CONFIRM = range(2)
EDIT_LESSON_STATUS, EDIT_LESSON_COMMENT = range(2)


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
    access_code = update.message.text.strip()
    if not access_code.replace(' ', '').isalnum() or len(access_code) < 6 or len(access_code) > 10:
        await update.message.reply_text(
            "Пожалуйста, введите корректный код доступа.\n"
            "Код должен содержать только буквы и цифры (6-10 символов)."
        )
        return
    
    db = SessionLocal()
    user = db.query(User).filter(User.access_code == access_code).first()
    if user:
        user.telegram_id = update.effective_user.id
        user.username = update.effective_user.username
        db.commit()
        await update.message.reply_text("✅ Доступ подтвержден!")
        await show_main_menu(update, context)
    else:
        await update.message.reply_text("❌ Неверный код доступа. Попробуйте еще раз.")
    db.close()

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("Сначала вам нужно войти. Введите код доступа.")
        return

    query = update.callback_query
    if query:
        await query.answer()

    if user.role == UserRole.TUTOR:
        # Используем улучшенный дашборд для репетитора
        from .handlers.enhanced_tutor import show_tutor_dashboard
        return await show_tutor_dashboard(update, context)

    elif user.role == UserRole.STUDENT:
        reply_markup = student_main_keyboard()
        message = f"Добро пожаловать, {user.full_name}!\n\nИспользуйте кнопки ниже для навигации:"
        if query:
            await query.delete_message()
            await context.bot.send_message(chat_id=query.from_user.id, text=message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)
        return
        
    elif user.role == UserRole.PARENT:
        reply_markup = parent_main_keyboard()
        message = f"Добро пожаловать, {user.full_name}!"
    else:
        message = "Не удалось определить вашу роль."
        reply_markup = None

    if query:
        await query.edit_message_text(message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from .logger import log_user_action
    
    query = update.callback_query
    await query.answer()
    data = query.data
    
    print(f"BUTTON_HANDLER: Received callback '{data}' from user {update.effective_user.id}")
    
    # Логируем все нажатия кнопок
    log_user_action(update.effective_user.id, f"BUTTON_CLICK: {data}")
    
    # Проверяем роль пользователя
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if user and user.role == UserRole.TUTOR:
        print(f"DEBUG: User is TUTOR, processing callback '{data}'")
        try:
            from .handlers.enhanced_tutor import handle_tutor_callbacks
            # Перенаправляем все callbacks репетитора в улучшенный handler
            return await handle_tutor_callbacks(update, context)
        except Exception as e:
            print(f"ERROR: Failed to import enhanced_tutor: {e}")
            await query.edit_message_text(f"❌ Ошибка обработки: {e}")
            return
    else:
        print(f"DEBUG: User role: {user.role if user else 'None'}")

    # Карта для сопоставления префиксов callback_data с функциями и именами их ID-параметров.
    # Формат: { "префикс": (функция, "имя_параметра_id") }
    # Если ID не требуется, имя параметра - None.
    action_map = {
        "main_menu": (show_main_menu, None),
        "my_progress": (show_my_progress, None),
        "schedule": (show_schedule, None),
        "homework": (show_homework_menu, None),
        "lessons_history": (show_lesson_history, None),
        "payment_attendance": (show_payment_and_attendance, None),
        "tutor_student_list": (show_student_list, None),
        "tutor_view_student_": (show_student_profile, "student_id"),
        "tutor_analytics_": (show_analytics_chart, "student_id"),
        "tutor_delete_student_": (tutor_delete_student_start, "student_id"),
        "tutor_delete_confirm_": (tutor_delete_student_confirm, "student_id"),
        "tutor_add_parent_": (tutor_add_parent_start, "student_id"),
        "tutor_lessons_list_": (show_tutor_lessons, "student_id"),
        "tutor_lesson_details_": (show_lesson_details, "lesson_id"),
        "tutor_mark_attended_": (tutor_mark_lesson_attended, "lesson_id"),
        "tutor_set_attendance_": (tutor_set_lesson_attendance, "lesson_id_status"),
        "tutor_reschedule_lesson_": (tutor_reschedule_lesson_start, "lesson_id"),
        "tutor_check_hw_": (tutor_check_homework, "lesson_id"),
        "tutor_manage_library": (tutor_manage_library, None),
        "tutor_delete_material_start": (tutor_delete_material_start, None),
        "tutor_delete_material_": (tutor_delete_material_confirm, "material_id"),
        "tutor_view_material_": (show_material_details, "material_id"),
        "materials_library": (show_materials_library, None),
        "student_view_material_": (show_material_details, "material_id"),
        "student_view_hw_": (student_view_homework, "hw_id"),
        "student_view_lesson_": (student_view_lesson_details, "lesson_id"),
        "select_child": (parent_select_child, None),
        "view_child_": (parent_view_child_menu, "child_id"),
        "child_progress_": (parent_view_child_progress, "child_id"),
        "parent_chat_with_tutor": (chat_with_tutor_start, None),
        "chat_with_tutor": (chat_with_tutor_start, None),
        "broadcast_cancel": (broadcast_cancel, None),
        "broadcast_send": (broadcast_send, None),
    }

    for prefix, (func, id_param_name) in action_map.items():
        if data.startswith(prefix):
            params = {}
            if id_param_name:
                try:
                    # Извлекаем ID из конца callback_data
                    item_id = int(data.split("_")[-1])
                    params[id_param_name] = item_id
                except (ValueError, IndexError):
                    # Эта ошибка не должна возникать при правильно сформированных callback_data
                    # Можно добавить логирование для отладки
                    continue
            
            await func(update, context, **params)
            return

    # Обработка более сложных случаев отдельно  
    # Примечание: tutor_set_mastery_ обрабатывается в ConversationHandler для edit_lesson
    # поэтому здесь его не обрабатываем

    if data.startswith("tutor_set_hw_status_"):
        prefix = "tutor_set_hw_status_"
        payload = data[len(prefix):]
        try:
            hw_id_str, status_value = payload.split('_', 1)
            hw_id = int(hw_id_str)
            await tutor_set_homework_status(update, context, hw_id, status_value)
        except ValueError:
            # Можно добавить логирование для отладки
            await query.answer("Ошибка обработки данных.")
        return

    await query.edit_message_text(text=f"Функция для '{data}' еще не реализована.")


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lesson_id = context.user_data.get('lesson_id')
    context.user_data.clear()
    await update.message.reply_text("Действие отменено.")
    if lesson_id:
        # Возвращаемся к карточке урока после отмены
        await show_lesson_details(update, context, lesson_id)
    return ConversationHandler.END

# --- Tutor: Student Management ---
async def show_student_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_user_role(update, UserRole.TUTOR):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
        
    students = get_all_students()
    keyboard = tutor_student_list_keyboard(students)
    message = "У вас пока нет учеников." if not students else "Выберите ученика:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=keyboard)
    else:
        await update.message.reply_text(message, reply_markup=keyboard)

async def show_student_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, student_id: int):
    db = SessionLocal()
    try:
        # Используем joinedload для "жадной" загрузки связанного родителя.
        # Это решает проблему DetachedInstanceError.
        student = db.query(User).options(joinedload(User.parent)).filter(User.id == student_id).first()
        
        if not student:
            await update.callback_query.edit_message_text("Ученик не найден.")
            return
        
        # get_student_balance открывает и закрывает свою сессию, это безопасно.
        balance = get_student_balance(student_id)
        parent_info = student.parent.full_name if student.parent else "Не привязан"
        
        text = (f"*Профиль ученика: {student.full_name}*\n\n"
                f"🏅 *Баллы:* {student.points}\n"
                f"- Код доступа: `{student.access_code}`\n"
                f"- Остаток занятий: *{balance}*\n"
                f"- Родитель: *{parent_info}*\n\n"
                "Выберите действие:")
        keyboard = tutor_student_profile_keyboard(student_id)
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    finally:
        db.close()

async def tutor_add_student_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_user_role(update, UserRole.TUTOR):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return ConversationHandler.END
        
    await update.message.reply_text("Введите ФИО нового ученика:")
    return ADD_STUDENT_NAME

async def tutor_get_student_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['student_name'] = update.message.text
    await update.message.reply_text("Введите ФИО родителя (или 'пропустить' если родителя нет):")
    return ADD_PARENT_CODE

async def tutor_get_parent_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parent_name = update.message.text.strip()
    student_name = context.user_data.get('student_name')
    db = SessionLocal()
    parent = None
    
    if parent_name.lower() != 'пропустить':
        # Создаем нового родителя
        parent_access_code = generate_access_code()
        parent = User(
            full_name=parent_name,
            role=UserRole.PARENT,
            access_code=parent_access_code,
            points=0,
            streak_days=0,
            total_study_hours=0
        )
        db.add(parent)
        db.flush()  # Чтобы получить ID родителя
    
    # Создаем ученика
    student_access_code = generate_access_code()
    new_student = User(
        full_name=student_name,
        role=UserRole.STUDENT,
        access_code=student_access_code,
        parent_id=parent.id if parent else None,
        points=0,
        streak_days=0,
        total_study_hours=0
    )
    db.add(new_student)
    db.commit()
    
    message = f"✅ Ученик *{student_name}* добавлен.\n📱 Код ученика: `{student_access_code}`"
    if parent:
        message += f"\n\n👨‍👩‍👧‍👦 Родитель *{parent.full_name}* создан.\n📱 Код родителя: `{parent.access_code}`"
    
    await update.message.reply_text(message, parse_mode='Markdown')
    context.user_data.clear()
    db.close()
    return ConversationHandler.END

async def tutor_edit_name_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    student_id = int(query.data.split("_")[-1])
    context.user_data['student_id_to_edit'] = student_id
    student = get_user_by_id(student_id)
    await query.edit_message_text(f"Введите новое ФИО для ученика {student.full_name}:")
    return EDIT_STUDENT_NAME

async def tutor_get_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_name = update.message.text
    student_id = context.user_data.get('student_id_to_edit')
    db = SessionLocal()
    student = db.query(User).filter(User.id == student_id).first()
    if student:
        student.full_name = new_name
        db.commit()
        await update.message.reply_text(f"✅ ФИО ученика обновлено.")
    db.close()
    context.user_data.clear()
    await show_main_menu(update, context)
    return ConversationHandler.END

async def tutor_add_parent_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс добавления родителя к существующему ученику"""
    query = update.callback_query
    await query.answer()
    
    student_id = int(query.data.split("_")[-1])
    context.user_data['student_id_for_parent'] = student_id
    
    db = SessionLocal()
    student = db.query(User).filter(User.id == student_id).first()
    db.close()
    
    if not student:
        await query.edit_message_text("❌ Ученик не найден.")
        return ConversationHandler.END
    
    if student.parent_id:
        # У ученика уже есть родитель
        parent = get_user_by_id(student.parent_id)
        await query.edit_message_text(
            f"⚠️ У ученика *{student.full_name}* уже есть родитель:\n"
            f"👨‍👩‍👧‍👦 {parent.full_name}\n"
            f"📱 Код: `{parent.access_code}`",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    await query.edit_message_text(f"Введите ФИО родителя для ученика *{student.full_name}*:", parse_mode='Markdown')
    return ADD_PARENT_NAME

async def tutor_get_parent_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создает родителя и привязывает к ученику"""
    parent_name = update.message.text.strip()
    student_id = context.user_data.get('student_id_for_parent')
    
    db = SessionLocal()
    student = db.query(User).filter(User.id == student_id).first()
    
    if not student:
        await update.message.reply_text("❌ Ученик не найден.")
        db.close()
        context.user_data.clear()
        return ConversationHandler.END
    
    # Создаем нового родителя
    parent_access_code = generate_access_code()
    parent = User(
        full_name=parent_name,
        role=UserRole.PARENT,
        access_code=parent_access_code,
        points=0,
        streak_days=0,
        total_study_hours=0
    )
    db.add(parent)
    db.flush()  # Получаем ID родителя
    
    # Привязываем родителя к ученику
    student.parent_id = parent.id
    db.commit()
    
    message = (f"✅ Родитель добавлен к ученику!\n\n"
               f"👨‍👩‍👧‍👦 Родитель: *{parent.full_name}*\n"
               f"📱 Код родителя: `{parent.access_code}`\n\n"
               f"🎓 Ученик: *{student.full_name}*\n"
               f"📱 Код ученика: `{student.access_code}`")
    
    await update.message.reply_text(message, parse_mode='Markdown')
    
    db.close()
    context.user_data.clear()
    await show_main_menu(update, context)
    return ConversationHandler.END

async def tutor_delete_student_start(update: Update, context: ContextTypes.DEFAULT_TYPE, student_id: int):
    """Запрашивает подтверждение на удаление ученика."""
    query = update.callback_query
    student = get_user_by_id(student_id)
    if not student:
        await query.edit_message_text("Ученик не найден.")
        return

    keyboard = tutor_delete_confirm_keyboard(student_id)
    await query.edit_message_text(
        f"Вы уверены, что хотите удалить ученика *{student.full_name}*?\n\n"
        "⚠️ *Внимание!* Это действие необратимо и приведет к удалению "
        "всей связанной информации: истории уроков, домашних заданий и оплат.",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def tutor_delete_student_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, student_id: int):
    """Окончательно удаляет ученика после подтверждения."""
    query = update.callback_query
    db = SessionLocal()
    try:
        # Используем joinedload для предзагрузки, чтобы избежать доп. запросов
        student = db.query(User).options(
            joinedload(User.student_lessons),
            joinedload(User.payments)
        ).filter(User.id == student_id).first()

        if student:
            name = student.full_name
            # SQLAlchemy благодаря `cascade="all, delete-orphan"` сам удалит связанные
            # уроки, ДЗ и платежи.
            db.delete(student)
            db.commit()
            await query.edit_message_text(f"✅ Ученик *{name}* и все его данные были успешно удалены.", parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ Не удалось найти ученика для удаления.")
    except Exception as e:
        db.rollback()
        # logger.error(f"Ошибка при удалении ученика {student_id}: {e}") # Хорошая практика для будущего
        await query.edit_message_text("Произошла ошибка при удалении. Попробуйте позже.")
    finally:
        db.close()

    # Показываем обновленный список учеников
    await show_student_list(update, context)


# --- Tutor: Lesson & HW Management ---
async def show_tutor_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE, student_id: int):
    student = get_user_by_id(student_id)
    db = SessionLocal()
    lessons = db.query(Lesson).filter(Lesson.student_id == student_id).order_by(Lesson.date.desc()).all()
    db.close()
    keyboard = tutor_lesson_list_keyboard(lessons, student_id)
    await update.callback_query.edit_message_text(f"Уроки ученика {student.full_name}:", reply_markup=keyboard)

def escape_md(text: str) -> str:
    """Escapes special characters for legacy Markdown."""
    if not text:
        return ''
    # Characters to escape for Telegram's legacy Markdown
    escape_chars = r'_*`['
    # Replace each special character with its escaped version
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def show_lesson_details(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int):
    db = SessionLocal()
    try:
        lesson = db.query(Lesson).options(joinedload(Lesson.homeworks)).filter(Lesson.id == lesson_id).first()
        if not lesson:
            await update.callback_query.edit_message_text("Урок не найден.")
            return

        topic = escape_markdown(lesson.topic or "", version=2)
        skills = escape_markdown(lesson.skills_developed or 'Не указаны', version=2)
        mastery_level_ru = TOPIC_MASTERY_RU.get(lesson.mastery_level, "Неизвестно")
        mastery_level = escape_markdown(mastery_level_ru, version=2)
        date_str = escape_markdown(lesson.date.strftime('%d.%m.%Y'), version=2)
        comment = escape_markdown(lesson.mastery_comment or '', version=2)

        attendance_status_ru = ATTENDANCE_STATUS_RU.get(lesson.attendance_status, "Неизвестно")
        attendance_status = escape_markdown(attendance_status_ru, version=2)
        
        text = (f"📚 *Тема:* {topic}\n"
                f"🗓️ *Дата:* {date_str}\n"
                f"👍 *Навыки:* {skills}\n"
                f"🎓 *Статус:* {mastery_level}\n"
                f"👥 *Посещение:* {attendance_status}\n")
        if comment:
            text += f"💬 *Комментарий:* {comment}\n"

        keyboard = tutor_lesson_details_keyboard(lesson)
        
        # Используем edit_message_text, если есть query
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='MarkdownV2')
        else: # Иначе отправляем новое сообщение (например, после отмены диалога)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=keyboard, parse_mode='MarkdownV2')

    finally:
        db.close()


async def tutor_add_lesson_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    student_id = int(query.data.split("_")[-1])
    context.user_data['lesson_student_id'] = student_id
    await query.edit_message_text("Введите тему нового урока:")
    return ADD_LESSON_TOPIC

async def tutor_get_lesson_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['lesson_topic'] = update.message.text
    await update.message.reply_text("Введите дату урока (ДД.ММ.ГГГГ):")
    return ADD_LESSON_DATE

async def tutor_get_lesson_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['lesson_date'] = datetime.strptime(update.message.text, "%d.%m.%Y")
        await update.message.reply_text("Какие навыки развивал урок?")
        return ADD_LESSON_SKILLS
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите дату как ДД.ММ.ГГГГ:")
        return ADD_LESSON_DATE

async def tutor_get_lesson_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    student_id = context.user_data.get('lesson_student_id')
    db = SessionLocal()
    new_lesson = Lesson(
        student_id=student_id,
        topic=context.user_data.get('lesson_topic'),
        date=context.user_data.get('lesson_date'),
        skills_developed=update.message.text
    )
    db.add(new_lesson)
    db.commit()
    db.close()
    await update.message.reply_text("✅ Урок добавлен!")
    context.user_data.clear()
    await show_main_menu(update, context)
    return ConversationHandler.END

async def tutor_edit_lesson_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает диалог редактирования статуса и комментария урока."""
    query = update.callback_query
    lesson_id = int(query.data.split("_")[-1])
    context.user_data['lesson_id'] = lesson_id
    
    keyboard = tutor_edit_lesson_status_keyboard(lesson_id)
    await query.edit_message_text("Выберите новый статус усвоения темы:", reply_markup=keyboard)
    return EDIT_LESSON_STATUS

async def tutor_edit_lesson_get_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает новый статус и спрашивает про комментарий."""
    query = update.callback_query
    # Извлекаем lesson_id и mastery_value из callback_data
    prefix = "tutor_set_mastery_"
    payload = query.data[len(prefix):]
    lesson_id_str, mastery_value = payload.split('_', 1)
    lesson_id = int(lesson_id_str)

    # Сохраняем выбранный статус и lesson_id
    context.user_data['new_mastery_status'] = TopicMastery(mastery_value)
    context.user_data['lesson_id'] = lesson_id
    
    await query.edit_message_text(
        "Статус выбран. Теперь введите комментарий к уровню усвоения.\n"
        "Чтобы пропустить, введите /skip."
    )
    return EDIT_LESSON_COMMENT

async def tutor_edit_lesson_get_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает комментарий, сохраняет все изменения и завершает диалог."""
    comment = update.message.text
    if comment.lower() == '/skip':
        comment = None

    lesson_id = context.user_data.get('lesson_id')
    new_mastery = context.user_data.get('new_mastery_status')

    db = SessionLocal()
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if lesson:
            # Начисляем баллы, если тема закреплена впервые
            if new_mastery == TopicMastery.MASTERED and lesson.mastery_level != TopicMastery.MASTERED:
                lesson.student.points += 25
                await update.message.reply_text("✅ Статус и комментарий обновлены! +25 баллов ученику.")
            else:
                await update.message.reply_text("✅ Статус и комментарий обновлены!")

            lesson.mastery_level = new_mastery
            lesson.mastery_comment = comment
            db.commit()
        else:
            await update.message.reply_text("❌ Урок не найден.")
    finally:
        db.close()

    context.user_data.clear()
    await show_lesson_details(update, context, lesson_id)
    return ConversationHandler.END


async def tutor_add_hw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lesson_id = int(query.data.split("_")[-1])
    context.user_data['hw_lesson_id'] = lesson_id
    await query.edit_message_text("Введите описание домашнего задания:")
    return ADD_HW_DESC

async def tutor_get_hw_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['hw_description'] = update.message.text
    await update.message.reply_text("Введите дедлайн (ДД.ММ.ГГГГ):")
    return ADD_HW_DEADLINE

async def tutor_get_hw_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['hw_deadline'] = datetime.strptime(update.message.text, "%d.%m.%Y")
        await update.message.reply_text("Прикрепите ссылку (или /skip):")
        return ADD_HW_LINK
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите дату как ДД.ММ.ГГГГ:")
        return ADD_HW_DEADLINE

async def tutor_get_hw_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    if link.lower() == '/skip':
        link = None
    
    context.user_data['hw_link'] = link
    await update.message.reply_text(
        "Теперь отправьте фотографии к заданию (можно несколько подряд) или /skip для пропуска:\n\n"
        "Когда закончите отправлять фото, напишите /done"
    )
    context.user_data['hw_photos'] = []  # Список для хранения file_id фотографий
    return ADD_HW_PHOTOS

async def tutor_get_hw_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    if update.message.text:
        if update.message.text.lower() == '/skip':
            return await tutor_finalize_homework(update, context)
        elif update.message.text.lower() == '/done':
            return await tutor_finalize_homework(update, context)
        else:
            await update.message.reply_text("Отправьте фото или напишите /done для завершения, /skip для пропуска.")
            return ADD_HW_PHOTOS
    
    # Если пришло фото
    if update.message.photo:
        # Берем фото самого большого размера
        photo = update.message.photo[-1]
        context.user_data['hw_photos'].append(photo.file_id)
        
        photo_count = len(context.user_data['hw_photos'])
        await update.message.reply_text(
            f"📷 Фото {photo_count} добавлено!\n"
            f"Отправьте еще фото или напишите /done для завершения."
        )
        return ADD_HW_PHOTOS
    
    await update.message.reply_text("Пожалуйста, отправьте фото или напишите /done для завершения.")
    return ADD_HW_PHOTOS

async def tutor_finalize_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    lesson_id = context.user_data.get('hw_lesson_id')
    photos = context.user_data.get('hw_photos', [])
    
    db = SessionLocal()
    new_hw = Homework(
        lesson_id=lesson_id,
        description=context.user_data.get('hw_description'),
        deadline=context.user_data.get('hw_deadline'),
        file_link=context.user_data.get('hw_link'),
        photo_file_ids=json.dumps(photos) if photos else None
    )
    db.add(new_hw)
    db.commit()
    db.close()
    
    photo_text = f" с {len(photos)} фото" if photos else ""
    await update.message.reply_text(f"✅ ДЗ добавлено{photo_text}!")
    context.user_data.clear()
    await show_main_menu(update, context)
    return ConversationHandler.END

async def tutor_check_homework(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int):
    
    db = SessionLocal()
    hw = db.query(Homework).options(joinedload(Homework.lesson).joinedload(Lesson.student)).filter(Homework.lesson_id == lesson_id).first()
    db.close()
    if not hw:
        await update.callback_query.answer("Для этого урока нет ДЗ.")
        return
    
    status_ru = HOMEWORK_STATUS_RU.get(hw.status, "Неизвестно")
    description = escape_markdown(hw.description or "", version=2)
    status_md = escape_markdown(status_ru, version=2)

    # Формируем текст с информацией о прикрепленных материалах
    text = f"📝 *ДЗ:* {description}\n*Статус:* {status_md}\n"
    
    # Показываем фото от репетитора, если есть
    tutor_photos = []
    if hw.photo_file_ids:
        try:
            tutor_photos = json.loads(hw.photo_file_ids)
            text += f"📷 Прикреплено фото от репетитора: {len(tutor_photos)}\n"
        except:
            pass
    
    # Показываем ответ ученика, если есть    
    if hw.submission_text or hw.submission_photo_file_ids:
        text += "\n*Ответ студента:*\n"
        
        if hw.submission_text:
            submission_text_md = escape_markdown(hw.submission_text[:200] + "..." if len(hw.submission_text) > 200 else hw.submission_text, version=2)
            text += f"📝 {submission_text_md}\n"
            
        if hw.submission_photo_file_ids:
            try:
                student_photos = json.loads(hw.submission_photo_file_ids)
                text += f"📷 Фото от студента: {len(student_photos)}\n"
            except:
                pass

    keyboard = tutor_check_homework_keyboard(hw)
    await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='MarkdownV2')
    
    # Отправляем фотографии от репетитора
    if tutor_photos:
        for photo_id in tutor_photos[:3]:  # Показываем максимум 3 фото
            try:
                await update.callback_query.message.reply_photo(photo_id, caption="📷 Фото от репетитора")
            except:
                pass
    
    # Отправляем фотографии от студента  
    if hw.submission_photo_file_ids:
        try:
            student_photos = json.loads(hw.submission_photo_file_ids)
            for photo_id in student_photos[:3]:  # Показываем максимум 3 фото
                try:
                    await update.callback_query.message.reply_photo(photo_id, caption="📷 Ответ студента")
                except:
                    pass
        except:
            pass

# --- Tutor: Payment ---
async def tutor_add_payment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    student_id = int(query.data.split("_")[-1])
    context.user_data['payment_student_id'] = student_id
    await query.edit_message_text("Введите количество оплаченных уроков:")
    return ADD_PAYMENT_AMOUNT

async def tutor_get_payment_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text)
        student_id = context.user_data.get('payment_student_id')
        db = SessionLocal()
        new_payment = Payment(student_id=student_id, lessons_paid=amount)
        db.add(new_payment)
        db.commit()
        db.close()
        await update.message.reply_text(f"✅ Оплата на {amount} уроков добавлена.")
    except ValueError:
        await update.message.reply_text("Введите число.")
        return ADD_PAYMENT_AMOUNT
    
    context.user_data.clear()
    await show_main_menu(update, context)
    return ConversationHandler.END

# --- Student Actions ---
async def show_homework_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем роль пользователя для text-сообщений (reply keyboard)
    if update.message and not check_user_role(update, UserRole.STUDENT):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
    
    query = update.callback_query
    user = get_user_by_telegram_id(update.effective_user.id)
    db = SessionLocal()
    
    # Загружаем ВСЕ домашние задания для студента с предзагрузкой lesson
    all_hw = db.query(Homework).options(joinedload(Homework.lesson)).join(Lesson).filter(
        Lesson.student_id == user.id
    ).order_by(Homework.created_at.desc()).all()
    
    db.close()

    if not all_hw:
        message = "У вас нет домашних заданий."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")]])
        if query:
            await query.edit_message_text(message, reply_markup=keyboard)
        else:
            await update.message.reply_text(message, reply_markup=keyboard)
        return

    # Создаем клавиатуру со всеми ДЗ
    keyboard_buttons = []
    for hw in all_hw:
        status_emoji = {
            HomeworkStatus.PENDING: "⏳",
            HomeworkStatus.SUBMITTED: "📤", 
            HomeworkStatus.CHECKED: "✅"
        }.get(hw.status, "❓")
        
        hw_text = f"{status_emoji} {hw.lesson.topic}"
        if len(hw_text) > 30:
            hw_text = hw_text[:27] + "..."
            
        if hw.status == HomeworkStatus.PENDING:
            # Если не сдано - можно сдать
            callback_data = f"student_submit_hw_{hw.id}"
        else:
            # Если сдано - можно посмотреть
            callback_data = f"student_view_hw_{hw.id}"
            
        keyboard_buttons.append([InlineKeyboardButton(hw_text, callback_data=callback_data)])
    
    keyboard_buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")])
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    message = "📝 *Ваши домашние задания:*\n\n⏳ \\- К сдаче\n📤 \\- Сдано\n✅ \\- Проверено"
    
    if query:
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')


async def student_submit_homework_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    hw_id = int(query.data.split("_")[-1])
    context.user_data['hw_id_to_submit'] = hw_id
    
    hw = get_homework_by_id(hw_id)
    
    await query.edit_message_text(
        f"Вы выбрали:\n*Тема:* {hw.lesson.topic}\n*Задание:* {hw.description}\n\n"
        "Отправьте ваш ответ:\n"
        "• 📝 Текст решения\n"
        "• 📷 Фотографии (можно несколько)\n"
        "• 📄 Документы\n\n"
        "Когда закончите, напишите /done",
        parse_mode='Markdown'
    )
    return SUBMIT_HOMEWORK_FILE

async def student_get_homework_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    hw_id = context.user_data.get('hw_id_to_submit')
    
    # Если пользователь еще не начал отправлять данные, инициализируем
    if 'submission_photos' not in context.user_data:
        context.user_data['submission_photos'] = []
        context.user_data['submission_text'] = ""
    
    if update.message.text:
        if update.message.text.lower() == '/done':
            return await finalize_homework_submission(update, context)
        else:
            # Добавляем текст к ответу
            context.user_data['submission_text'] += update.message.text + "\n"
            await update.message.reply_text(
                f"📝 Текст добавлен!\n"
                f"Можете добавить фото или напишите /done для завершения."
            )
            return SUBMIT_HOMEWORK_FILE
            
    elif update.message.document:
        # Документы пока не поддерживаем в новой версии, но можем добавить
        await update.message.reply_text("📄 Документ получен! Напишите /done для завершения или добавьте еще материалы.")
        return SUBMIT_HOMEWORK_FILE
        
    elif update.message.photo:
        # Добавляем фото к ответу
        photo = update.message.photo[-1]  # Берем самое большое разрешение
        context.user_data['submission_photos'].append(photo.file_id)
        
        photo_count = len(context.user_data['submission_photos'])
        await update.message.reply_text(
            f"📷 Фото {photo_count} добавлено!\n"
            f"Можете добавить еще фото/текст или напишите /done для завершения."
        )
        return SUBMIT_HOMEWORK_FILE

    await update.message.reply_text("Отправьте текст, фото или напишите /done для завершения.")
    return SUBMIT_HOMEWORK_FILE

async def finalize_homework_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    hw_id = context.user_data.get('hw_id_to_submit')
    submission_text = context.user_data.get('submission_text', '').strip()
    submission_photos = context.user_data.get('submission_photos', [])
    
    if not submission_text and not submission_photos:
        await update.message.reply_text("Пожалуйста, добавьте текст или фото перед завершением.")
        return SUBMIT_HOMEWORK_FILE

    db = SessionLocal()
    hw = db.query(Homework).options(joinedload(Homework.lesson).joinedload(Lesson.student)).filter(Homework.id == hw_id).first()
    if hw:
        hw.status = HomeworkStatus.SUBMITTED
        hw.submission_text = submission_text if submission_text else None
        hw.submission_photo_file_ids = json.dumps(submission_photos) if submission_photos else None
        db.commit()
        
        # Уведомление репетитору
        tutor = db.query(User).filter(User.role == UserRole.TUTOR).first()
        if tutor and tutor.telegram_id:
            student_name = hw.lesson.student.full_name
            photo_count = len(submission_photos)
            text_info = "с текстом" if submission_text else ""
            photo_info = f"с {photo_count} фото" if photo_count > 0 else ""
            
            materials_info = " ".join(filter(None, [text_info, photo_info]))
            
            await context.bot.send_message(
                tutor.telegram_id,
                f"📝 Студент {student_name} сдал домашнее задание по теме '{hw.lesson.topic}' {materials_info}.\n"
                "Вы можете проверить его в профиле ученика."
            )
        
        materials_text = ""
        if submission_text and submission_photos:
            materials_text = f" (текст + {len(submission_photos)} фото)"
        elif submission_text:
            materials_text = " (текст)"
        elif submission_photos:
            materials_text = f" ({len(submission_photos)} фото)"
            
        await update.message.reply_text(f"✅ Ваше домашнее задание отправлено на проверку{materials_text}!")
    else:
        await update.message.reply_text("❌ Произошла ошибка, ДЗ не найдено.")
        
    db.close()
    context.user_data.clear()
    await show_main_menu(update, context)
    return ConversationHandler.END

async def student_view_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает детали ДЗ для студента (только для просмотра)"""
    query = update.callback_query
    await query.answer()  # Обязательно отвечаем на callback_query
    
    hw_id = int(query.data.split("_")[-1])
    
    db = SessionLocal()
    hw = db.query(Homework).options(joinedload(Homework.lesson)).filter(Homework.id == hw_id).first()
    db.close()
    
    if not hw:
        await query.edit_message_text("❌ ДЗ не найдено.")
        return
    
    status_emoji = {
        HomeworkStatus.PENDING: "⏳ К сдаче",
        HomeworkStatus.SUBMITTED: "📤 Сдано", 
        HomeworkStatus.CHECKED: "✅ Проверено"
    }.get(hw.status, "❓ Неизвестно")
    
    # Формируем сообщение с деталями ДЗ
    lesson_topic = escape_markdown(hw.lesson.topic, version=2)
    hw_description = escape_markdown(hw.description, version=2)
    status_text = escape_markdown(status_emoji, version=2)
    
    message = f"📝 *Домашнее задание*\n\n"
    message += f"*Урок:* {lesson_topic}\n"
    message += f"*Задание:* {hw_description}\n"
    message += f"*Статус:* {status_text}\n"
    
    if hw.deadline:
        deadline_str = hw.deadline.strftime("%d.%m.%Y")
        message += f"*Дедлайн:* {deadline_str}\n"
    
    # Показываем фото от репетитора, если есть
    tutor_photos = []
    if hw.photo_file_ids:
        try:
            tutor_photos = json.loads(hw.photo_file_ids)
            message += f"📷 *Фото от репетитора:* {len(tutor_photos)}\n"
        except:
            pass
    
    # Показываем ответ студента, если есть
    if hw.submission_text or hw.submission_photo_file_ids:
        message += f"\n*Ваш ответ:*\n"
        
        if hw.submission_text:
            submission_preview = hw.submission_text[:200] + ('...' if len(hw.submission_text) > 200 else '')
            submission_text_md = escape_markdown(submission_preview, version=2)
            message += f"📝 {submission_text_md}\n"
            
        if hw.submission_photo_file_ids:
            try:
                student_photos = json.loads(hw.submission_photo_file_ids)
                message += f"📷 Ваши фото: {len(student_photos)}\n"
            except:
                pass
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад к ДЗ", callback_data="homework")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode='MarkdownV2')
    
    # Отправляем фотографии от репетитора
    if tutor_photos:
        for photo_id in tutor_photos[:3]:  # Показываем максимум 3 фото
            try:
                await query.message.reply_photo(photo_id, caption="📷 Задание от репетитора")
            except:
                pass
    
    # Отправляем фотографии студента
    if hw.submission_photo_file_ids:
        try:
            student_photos = json.loads(hw.submission_photo_file_ids)
            for photo_id in student_photos[:3]:  # Показываем максимум 3 фото
                try:
                    await query.message.reply_photo(photo_id, caption="📷 Ваш ответ")
                except:
                    pass
        except:
            pass


# --- Parent Actions ---
async def parent_select_child(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_user_by_telegram_id(query.from_user.id)
    
    if not user or not user.children:
        await query.edit_message_text("К вашему профилю не привязано ни одного ученика.")
        return

    keyboard = parent_child_selection_keyboard(user.children)
    await query.edit_message_text("Выберите ребенка для просмотра информации:", reply_markup=keyboard)

async def parent_view_child_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, child_id: int):
    query = update.callback_query
    child = get_user_by_id(child_id)
    keyboard = parent_child_menu_keyboard(child_id)
    await query.edit_message_text(f"Меню для {child.full_name}:", reply_markup=keyboard)

async def parent_view_child_progress(update: Update, context: ContextTypes.DEFAULT_TYPE, child_id: int):
    query = update.callback_query
    student = get_user_by_id(child_id)
    
    db = SessionLocal()
    lessons_attended = db.query(Lesson).filter(Lesson.student_id == student.id, Lesson.is_attended == True).count()
    hw_checked = db.query(Homework).join(Lesson).filter(Lesson.student_id == student.id, Homework.status == HomeworkStatus.CHECKED).count()
    topics_mastered = db.query(Lesson).filter(Lesson.student_id == student.id, Lesson.mastery_level == TopicMastery.MASTERED).count()
    balance = get_student_balance(student.id)
    db.close()

    text = (
        f"📊 *Прогресс {student.full_name}*\n\n"
        f"🏅 *Баллы:* {student.points}\n"
        f"💰 *Остаток занятий:* {balance}\n\n"
        f"--- *Достижения* ---\n"
        f"✅ Посещено уроков: *{lessons_attended}*\n"
        f"📝 Сдано ДЗ: *{hw_checked}*\n"
        f"🎓 Освоено тем: *{topics_mastered}*\n"
    )
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(f"⬅️ Назад к меню {student.full_name}", callback_data=f"view_child_{student.id}")]])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')


# --- Chat ---
async def chat_with_tutor_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает диалог с репетитором."""
    # Проверяем роль пользователя для text-сообщений (reply keyboard)
    # Доступ должен быть у учеников и родителей, но не у репетитора
    if update.message and check_user_role(update, UserRole.TUTOR):
        await update.message.reply_text("Вы и так репетитор! 😄")
        return ConversationHandler.END
    
    query = update.callback_query
    message = ("Напишите ваше сообщение репетитору. Вы можете отправить текст, фото или документ.\n"
               "Для отмены введите /cancel.")
    
    if query:
        await query.answer()
        await query.edit_message_text(message)
    else:
        await update.message.reply_text(message)
    
    return CHAT_WITH_TUTOR

async def forward_message_to_tutor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пересылает сообщение от пользователя репетитору с подписью."""
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if not user:
        await update.message.reply_text("Ошибка: пользователь не найден в базе данных.")
        return ConversationHandler.END
    
    db = SessionLocal()
    tutor = db.query(User).filter(User.role == UserRole.TUTOR).first()
    db.close()

    if not tutor or not tutor.telegram_id:
        await update.message.reply_text("Не удалось найти репетитора. Сообщение не отправлено.")
        return ConversationHandler.END

    # Формируем подпись
    user_role_ru = "Родитель" if user.role == UserRole.PARENT else "Ученик"
    caption = (f"Сообщение от *{user_role_ru.lower()}* {escape_markdown(user.full_name, 2)}\n"
               f"ID для ответа: `{user.telegram_id}`")

    try:
        # Пересылаем сообщение пользователя
        forwarded_message = await context.bot.forward_message(
            chat_id=tutor.telegram_id,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
        # Отправляем подпись как отдельное сообщение в ответ на пересланное
        await context.bot.send_message(
            chat_id=tutor.telegram_id,
            text=caption,
            parse_mode='MarkdownV2',
            reply_to_message_id=forwarded_message.message_id
        )
        await update.message.reply_text("✅ Ваше сообщение отправлено репетитору!")
    except Forbidden:
        await update.message.reply_text("Не удалось отправить сообщение: репетитор заблокировал бота.")
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка при отправке: {e}")

    return ConversationHandler.END


async def handle_tutor_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ответ репетитора на сообщение пользователя."""
    # Проверяем, что это действительно ответ
    if not update.message.reply_to_message:
        return
    
    # Проверяем, что отвечающий - репетитор
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user or user.role != UserRole.TUTOR:
        return

    tutor_reply_text = update.message.text
    original_message = update.message.reply_to_message

    # --- Вариант 1: Ответ на пересланное сообщение ---
    if hasattr(original_message, 'forward_from') and original_message.forward_from:
        user_to_reply_id = original_message.forward_from.id
        try:
            await context.bot.send_message(
                chat_id=user_to_reply_id,
                text=f"📩 Сообщение от репетитора:\n\n{tutor_reply_text}"
            )
            await update.message.reply_text("✅ Ответ успешно отправлен.")
        except Forbidden:
            await update.message.reply_text("❌ Не удалось отправить ответ: пользователь заблокировал бота.")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при отправке ответа: {e}")
        return

    # --- Вариант 2: Ответ на сообщение с подписью (содержит ID) ---
    if original_message.text and "ID для ответа:" in original_message.text:
        try:
            # Ищем ID в тексте разными способами
            user_to_reply_id = None
            text = original_message.text
            
            # Способ 1: между ` символами
            if "`" in text:
                parts = text.split("`")
                for part in parts:
                    if part.isdigit():
                        user_to_reply_id = int(part)
                        break
            
            # Способ 2: после "ID для ответа:"
            if not user_to_reply_id and "ID для ответа:" in text:
                match = re.search(r'ID для ответа:\s*(\d+)', text)
                if match:
                    user_to_reply_id = int(match.group(1))
            
            if user_to_reply_id:
                await context.bot.send_message(
                    chat_id=user_to_reply_id,
                    text=f"📩 Сообщение от репетитора:\n\n{tutor_reply_text}"
                )
                await update.message.reply_text("✅ Ответ успешно отправлен.")
            else:
                await update.message.reply_text("❌ Не удалось извлечь ID пользователя из сообщения.")
                
        except Forbidden:
            await update.message.reply_text("❌ Не удалось отправить ответ: пользователь заблокировал бота.")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при отправке ответа: {e}")
        return

# --- Broadcast ---
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает диалог создания рассылки."""
    if not check_user_role(update, UserRole.TUTOR):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Введите сообщение, которое хотите разослать всем пользователям (ученикам и родителям).\n"
        "Для отмены введите /cancel."
    )
    return BROADCAST_MESSAGE

async def broadcast_get_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает сообщение для рассылки и запрашивает подтверждение."""
    # Сохраняем и текст, и message_id для возможного форвардинга
    context.user_data['broadcast_message'] = update.message
    
    keyboard = broadcast_confirm_keyboard()
    await update.message.reply_text(
        "Вы уверены, что хотите отправить это сообщение всем пользователям?",
        reply_markup=keyboard
    )
    return BROADCAST_CONFIRM

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отправляет сохраненное сообщение всем пользователям."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Начинаю рассылку...")

    message_to_send = context.user_data.get('broadcast_message')
    if not message_to_send:
        await query.edit_message_text("Не найдено сообщение для отправки. Попробуйте снова.")
        context.user_data.clear()
        return ConversationHandler.END

    db = SessionLocal()
    # Выбираем всех студентов и родителей, у которых есть telegram_id
    users_to_send = db.query(User).filter(
        or_(User.role == UserRole.STUDENT, User.role == UserRole.PARENT),
        User.telegram_id.isnot(None)
    ).all()
    db.close()

    if not users_to_send:
        await query.edit_message_text(
            "Не найдено ни одного пользователя для рассылки. "
            "Убедитесь, что ученики или родители активировали бота, используя свой код доступа."
        )
        context.user_data.clear()
        return ConversationHandler.END

    success_count = 0
    fail_count = 0

    for user in users_to_send:
        try:
            # Просто пересылаем исходное сообщение
            await context.bot.forward_message(
                chat_id=user.telegram_id,
                from_chat_id=message_to_send.chat_id,
                message_id=message_to_send.message_id
            )
            success_count += 1
            await asyncio.sleep(0.1) # Небольшая задержка, чтобы не попасть под спам-фильтры
        except Forbidden:
            # Пользователь заблокировал бота
            fail_count += 1
        except Exception:
            # Другие возможные ошибки
            fail_count += 1
    
    await query.edit_message_text(
        f"✅ Рассылка завершена!\n\n"
        f"Успешно отправлено: {success_count}\n"
        f"Не удалось отправить: {fail_count}"
    )
    context.user_data.clear()
    return ConversationHandler.END

async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет процесс рассылки."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Рассылка отменена.")
    context.user_data.clear()
    return ConversationHandler.END


# --- Reports ---
async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_user_role(update, UserRole.TUTOR):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return ConversationHandler.END
        
    students = get_all_students()
    if not students:
        await update.message.reply_text("У вас нет учеников.")
        return ConversationHandler.END
    keyboard = tutor_select_student_for_report_keyboard(students)
    await update.message.reply_text("Выберите ученика для отчета:", reply_markup=keyboard)
    return SELECT_STUDENT_FOR_REPORT

async def report_select_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    student_id = int(query.data.split("_")[-1])
    context.user_data['report_student_id'] = student_id
    keyboard = tutor_select_month_for_report_keyboard(student_id)
    await query.edit_message_text("Выберите месяц:", reply_markup=keyboard)
    return SELECT_MONTH_FOR_REPORT

async def report_select_month_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    student_id = context.user_data.get('report_student_id')
    month_offset = int(parts[-1])
    
    target_date = datetime.now() - timedelta(days=month_offset * 30)
    year, month = target_date.year, target_date.month
    
    student = get_user_by_id(student_id)
    lessons = get_lessons_for_student_by_month(student_id, year, month)
    payments = get_payments_for_student_by_month(student_id, year, month)

    month_names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    report_text = (
        f"📊 *Ежемесячный отчет*\n\n"
        f"👤 *Ученик:* {escape_markdown(student.full_name, 2)}\n"
        f"🗓️ *Период:* {month_names[month-1]} {year}\n\n"
        "\\-\\-\\- *Проведенные занятия* \\-\\-\\-\n"
    )

    if not lessons:
        report_text += "В этом месяце занятий не было\\.\n\n"
    else:
        total_attended = sum(1 for lesson in lessons if lesson.is_attended)
        for lesson in lessons:
            if lesson.is_attended:
                mastery_ru = TOPIC_MASTERY_RU.get(lesson.mastery_level, "Неизвестно")
                report_text += f"• *{escape_markdown(lesson.date.strftime('%d.%m.%Y'), 2)}*: {escape_markdown(lesson.topic, 2)} \\(Статус: {escape_markdown(mastery_ru, 2)}\\)\\n"
        report_text += f"\n*Итого проведено занятий:* {total_attended}\n\n"

    report_text += "\\-\\-\\- *Оплаты* \\-\\-\\-\n"
    if not payments:
        report_text += "В этом месяце оплат не было\\.\n"
    else:
        total_paid = sum(p.lessons_paid for p in payments)
        for payment in payments:
            report_text += f"• *{escape_markdown(payment.payment_date.strftime('%d.%m.%Y'), 2)}*: Оплачено {payment.lessons_paid} занятий\n"
        report_text += f"\n*Итого оплачено занятий:* {total_paid}\n"

    await query.edit_message_text(report_text, parse_mode='MarkdownV2')
    context.user_data.clear()
    return ConversationHandler.END

async def report_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("Создание отчета отменено.")
    context.user_data.clear()
    return ConversationHandler.END

# --- Material Management ---
async def tutor_manage_library(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_user_role(update, UserRole.TUTOR):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
        
    materials = get_all_materials()
    keyboard = tutor_library_management_keyboard(materials)
    message = "📚 *Библиотека материалов*\n\nЗдесь вы можете просматривать, добавлять и удалять материалы."
    if not materials:
        message = "📚 *Библиотека материалов*\n\nВ библиотеке пока пусто. Добавьте первый материал."

    # This handler can be called by a ReplyKeyboard button (no query) or an InlineKeyboard button (query)
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def tutor_add_material_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("Введите название материала:")
    return ADD_MATERIAL_TITLE

async def tutor_get_material_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['material_title'] = update.message.text
    await update.message.reply_text("Отправьте ссылку:")
    return ADD_MATERIAL_LINK

async def tutor_get_material_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['material_link'] = update.message.text
    await update.message.reply_text("Введите описание (или /skip):")
    return ADD_MATERIAL_DESC

async def tutor_get_material_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text
    if desc == '/skip': desc = None
    
    db = SessionLocal()
    new_material = Material(
        title=context.user_data['material_title'],
        link=context.user_data['material_link'],
        description=desc
    )
    db.add(new_material)
    db.commit()
    db.close()
    
    await update.message.reply_text("✅ Материал добавлен!")
    context.user_data.clear()
    await show_main_menu(update, context)
    return ConversationHandler.END

async def tutor_delete_material_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    materials = get_all_materials()
    if not materials:
        await update.callback_query.edit_message_text("Библиотека пуста.")
        return
    keyboard = tutor_select_material_to_delete_keyboard(materials)
    await update.callback_query.edit_message_text("Выберите материал для удаления:", reply_markup=keyboard)

async def tutor_delete_material_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, material_id: int):
    delete_material_by_id(material_id)
    await update.callback_query.answer("Материал удален.")
    await tutor_manage_library(update, context)

# --- Gamyfication, Analytics, Calendar, etc. ---
async def tutor_mark_lesson_attended(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int):
    db = SessionLocal()
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson.is_attended:
        lesson.is_attended = True
        lesson.student.points += 10
        db.commit()
        
        # Обновляем streak и проверяем достижения
        streak_achievements = update_study_streak(lesson.student_id)
        points_achievements = check_points_achievements(lesson.student_id)
        
        # Проверяем достижения по количеству уроков
        lessons_count = db.query(Lesson).filter(
            Lesson.student_id == lesson.student_id, 
            Lesson.is_attended == True
        ).count()
        
        if lessons_count == 1:
            award_achievement(lesson.student_id, "first_lesson", "Первый шаг", "Поздравляем с первым уроком!", "🎯")
        elif lessons_count == 10:
            award_achievement(lesson.student_id, "lessons_10", "Десятка", "10 проведенных уроков!", "🔟")
        elif lessons_count == 25:
            award_achievement(lesson.student_id, "lessons_25", "Четверть сотни", "25 проведенных уроков!", "🎖️")
        elif lessons_count == 50:
            award_achievement(lesson.student_id, "lessons_50", "Полтинник", "50 проведенных уроков!", "🥉")
        elif lessons_count == 100:
            award_achievement(lesson.student_id, "lessons_100", "Сотня", "100 проведенных уроков!", "🥈")
        
        await update.callback_query.answer("✅ Отмечено! +10 баллов ученику.")
    else:
        await update.callback_query.answer("Урок уже был отмечен.")
    
    await show_lesson_details(update, context, lesson_id)
    db.close()

async def tutor_set_lesson_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id_status: str):
    """Устанавливает статус посещаемости урока."""
    try:
        # Парсим lesson_id и status из строки вида "123_attended"
        parts = lesson_id_status.split('_')
        lesson_id = int(parts[0])
        status_str = '_'.join(parts[1:])  # На случай если в статусе есть подчеркивания
        
        db = SessionLocal()
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            await update.callback_query.answer("Урок не найден")
            db.close()
            return
        
        # Получаем новый статус
        status_mapping = {
            'attended': AttendanceStatus.ATTENDED,
            'excused_absence': AttendanceStatus.EXCUSED_ABSENCE,
            'unexcused_absence': AttendanceStatus.UNEXCUSED_ABSENCE,
            'rescheduled': AttendanceStatus.RESCHEDULED
        }
        
        new_status = status_mapping.get(status_str)
        if not new_status:
            await update.callback_query.answer("Неизвестный статус")
            db.close()
            return
        
        old_status = lesson.attendance_status
        lesson.attendance_status = new_status
        
        # Обновляем is_attended для совместимости
        lesson.is_attended = (new_status == AttendanceStatus.ATTENDED)
        
        # Логика начисления/снятия баллов и достижений
        if old_status != AttendanceStatus.ATTENDED and new_status == AttendanceStatus.ATTENDED:
            # Урок стал посещенным - добавляем баллы и проверяем достижения
            lesson.student.points += 10
            
            # Обновляем streak и проверяем достижения
            streak_achievements = update_study_streak(lesson.student_id)
            points_achievements = check_points_achievements(lesson.student_id)
            
            # Проверяем достижения по количеству уроков
            lessons_count = db.query(Lesson).filter(
                Lesson.student_id == lesson.student_id, 
                Lesson.attendance_status == AttendanceStatus.ATTENDED
            ).count()
            
            if lessons_count == 1:
                award_achievement(lesson.student_id, "first_lesson", "Первый шаг", "Поздравляем с первым уроком!", "🎯")
            elif lessons_count == 10:
                award_achievement(lesson.student_id, "lessons_10", "Десятка", "10 проведенных уроков!", "🔟")
            elif lessons_count == 25:
                award_achievement(lesson.student_id, "lessons_25", "Четверть сотни", "25 проведенных уроков!", "🎖️")
            elif lessons_count == 50:
                award_achievement(lesson.student_id, "lessons_50", "Полтинник", "50 проведенных уроков!", "🥉")
            elif lessons_count == 100:
                award_achievement(lesson.student_id, "lessons_100", "Сотня", "100 проведенных уроков!", "🥈")
        
        elif old_status == AttendanceStatus.ATTENDED and new_status != AttendanceStatus.ATTENDED:
            # Урок больше не посещенный - снимаем баллы (если они были начислены)
            if lesson.student.points >= 10:
                lesson.student.points -= 10
        
        db.commit()
        
        status_text = ATTENDANCE_STATUS_RU.get(new_status, str(new_status))
        await update.callback_query.answer(f"✅ Статус изменен: {status_text}")
        
        await show_lesson_details(update, context, lesson_id)
        db.close()
        
    except Exception as e:
        await update.callback_query.answer("Ошибка при изменении статуса")
        print(f"Ошибка в tutor_set_lesson_attendance: {e}")

async def tutor_reschedule_lesson_start(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int):
    """Начинает процесс переноса урока."""
    query = update.callback_query
    await query.answer()
    
    # Сохраняем ID урока в контексте
    context.user_data['reschedule_lesson_id'] = lesson_id
    
    await query.edit_message_text(
        "📅 Введите новую дату урока в формате ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Например: 15.08.2025 10:00\n\n"
        "Или отправьте /cancel для отмены"
    )
    return RESCHEDULE_LESSON_DATE

async def tutor_reschedule_lesson_get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает новую дату урока и переносит его."""
    try:
        lesson_id = context.user_data.get('reschedule_lesson_id')
        if not lesson_id:
            await update.message.reply_text("Ошибка: урок для переноса не найден")
            return ConversationHandler.END
        
        # Парсим дату
        date_text = update.message.text.strip()
        try:
            new_date = datetime.strptime(date_text, '%d.%m.%Y %H:%M')
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат даты. Используйте формат ДД.ММ.ГГГГ ЧЧ:ММ\n"
                "Например: 15.08.2025 10:00"
            )
            return RESCHEDULE_LESSON_DATE
        
        # Проверяем, что дата в будущем
        if new_date <= datetime.now():
            await update.message.reply_text("❌ Дата должна быть в будущем")
            return RESCHEDULE_LESSON_DATE
        
        # Обновляем урок в базе данных
        db = SessionLocal()
        try:
            lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
            if not lesson:
                await update.message.reply_text("❌ Урок не найден")
                return ConversationHandler.END
            
            # Сохраняем оригинальную дату, если это первый перенос
            if not lesson.is_rescheduled:
                lesson.original_date = lesson.date
                lesson.is_rescheduled = True
            
            # Устанавливаем новую дату и статус
            lesson.date = new_date
            lesson.attendance_status = AttendanceStatus.RESCHEDULED
            lesson.is_attended = False
            
            db.commit()
            
            date_str = new_date.strftime('%d.%m.%Y в %H:%M')
            await update.message.reply_text(
                f"✅ Урок перенесен на {date_str}\n"
                f"Тема: {lesson.topic}",
                reply_markup=tutor_main_keyboard()
            )
            
            # Показываем обновленную карточку урока
            await show_lesson_details(update, context, lesson_id)
            
        finally:
            db.close()
        
        # Очищаем контекст
        context.user_data.pop('reschedule_lesson_id', None)
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text("❌ Произошла ошибка при переносе урока")
        print(f"Ошибка в tutor_reschedule_lesson_get_date: {e}")
        return ConversationHandler.END

async def tutor_set_lesson_mastery(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int, mastery_value: str):
    db = SessionLocal()
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    new_mastery = TopicMastery(mastery_value)
    if new_mastery == TopicMastery.MASTERED and lesson.mastery_level != TopicMastery.MASTERED:
        lesson.student.points += 25
        lesson.mastery_level = new_mastery
        db.commit()
        # Проверяем достижения по баллам после добавления
        check_points_achievements(lesson.student_id)
        await update.callback_query.answer("✅ Статус обновлен! +25 баллов ученику.")
    else:
        lesson.mastery_level = new_mastery
        db.commit()
        await update.callback_query.answer("✅ Статус обновлен!")
    await show_lesson_details(update, context, lesson_id)
    db.close()

async def tutor_set_homework_status(update: Update, context: ContextTypes.DEFAULT_TYPE, hw_id: int, status_value: str):
    db = SessionLocal()
    hw = db.query(Homework).filter(Homework.id == hw_id).first()
    
    new_status = HomeworkStatus(status_value)
    if new_status == HomeworkStatus.CHECKED and hw.status != HomeworkStatus.CHECKED:
        hw.lesson.student.points += 15
        hw.checked_at = datetime.now()
        
        # Проверяем достижения по домашним заданиям
        completed_hw_count = db.query(Homework).filter(
            Homework.lesson.has(Lesson.student_id == hw.lesson.student_id),
            Homework.status == HomeworkStatus.CHECKED
        ).count() + 1  # +1 потому что текущее еще не commit-нуто
        
        if completed_hw_count == 1:
            award_achievement(hw.lesson.student_id, "first_homework", "Первое ДЗ", "Поздравляем с первым выполненным домашним заданием!", "📝")
        elif completed_hw_count == 5:
            award_achievement(hw.lesson.student_id, "homework_5", "Прилежный ученик", "5 выполненных домашних заданий!", "📚")
        elif completed_hw_count == 10:
            award_achievement(hw.lesson.student_id, "homework_10", "Знаток заданий", "10 выполненных домашних заданий!", "🎓")
        elif completed_hw_count == 25:
            award_achievement(hw.lesson.student_id, "homework_25", "Мастер домашек", "25 выполненных домашних заданий!", "🏅")
        elif completed_hw_count == 50:
            award_achievement(hw.lesson.student_id, "homework_50", "Гуру ДЗ", "50 выполненных домашних заданий!", "🥇")
        
        hw.status = new_status
        db.commit()
        # Проверяем достижения по баллам после добавления
        check_points_achievements(hw.lesson.student_id)
        await update.callback_query.answer("✅ ДЗ принято! +15 баллов ученику.")
    else:
        hw.status = new_status
        db.commit()
        await update.callback_query.answer("✅ Статус ДЗ обновлен!")
    await show_lesson_details(update, context, hw.lesson_id)
    db.close()

async def show_my_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем роль пользователя для text-сообщений (reply keyboard)
    if update.message and not check_user_role(update, UserRole.STUDENT):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
    
    query = update.callback_query
    user = get_user_by_telegram_id(update.effective_user.id)
    db = SessionLocal()
    student = db.query(User).filter(User.id == user.id).first()
    
    lessons_attended = db.query(Lesson).filter(Lesson.student_id == student.id, Lesson.is_attended == True).count()
    hw_checked = db.query(Homework).join(Lesson).filter(Lesson.student_id == student.id, Homework.status == HomeworkStatus.CHECKED).count()
    topics_mastered = db.query(Lesson).filter(Lesson.student_id == student.id, Lesson.mastery_level == TopicMastery.MASTERED).count()
    
    db.close()

    text = (
        f"📊 *Мой прогресс*\n\n"
        f"🏅 *Всего баллов:* {student.points}\n\n"
        f"--- *Достижения* ---\n"
        f"✅ Посещено уроков: *{lessons_attended}*\n"
        f"📝 Сдано ДЗ: *{hw_checked}*\n"
        f"🎓 Освоено тем: *{topics_mastered}*\n"
    )
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")]])
    
    if query:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем роль пользователя для text-сообщений (reply keyboard)
    if update.message and not check_user_role(update, UserRole.STUDENT):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
    
    query = update.callback_query
    calendar, step = create_calendar()
    
    if query:
        await query.edit_message_text("🗓️ *Календарь уроков*\n\nВыберите дату:", reply_markup=calendar, parse_mode='Markdown')
    else:
        await update.message.reply_text("🗓️ *Календарь уроков*\n\nВыберите дату:", reply_markup=calendar, parse_mode='Markdown')

async def handle_calendar_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    result, key, step = CustomCalendar().process_selection(update, context)

    if not result and key:
        await query.edit_message_text("Выберите дату:", reply_markup=key)
    elif result:
        user = get_user_by_telegram_id(query.from_user.id)
        db = SessionLocal()
        lessons = db.query(Lesson).filter(
            Lesson.student_id == user.id,
            func.date(Lesson.date) == result.date()
        ).all()
        db.close()

        if lessons:
            lessons_text = "\n".join([f"• *{l.date.strftime('%H:%M')}* - {l.topic}" for l in lessons])
            message = f"🗓️ *Уроки на {result.strftime('%d.%m.%Y')}*:\n{lessons_text}"
        else:
            message = f"На {result.strftime('%d.%m.%Y')} уроков не запланировано."
        
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🗓️ Открыть календарь", callback_data="schedule")]])
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def show_analytics_chart(update: Update, context: ContextTypes.DEFAULT_TYPE, student_id: int):
    query = update.callback_query
    await query.answer("Генерирую график, это может занять несколько секунд...")

    chart_path = generate_progress_chart(student_id)

    if chart_path and os.path.exists(chart_path):
        await context.bot.send_photo(
            chat_id=query.from_user.id,
            photo=open(chart_path, 'rb'),
            caption="График прогресса ученика."
        )
        os.remove(chart_path)
    else:
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="Недостаточно данных для построения графика."
        )
    
    await show_student_profile(update, context, student_id)

async def show_materials_library(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем роль пользователя для text-сообщений (reply keyboard)
    if update.message and not check_user_role(update, UserRole.STUDENT):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
    
    query = update.callback_query
    materials = get_all_materials()
    if not materials:
        message = "🗂️ В библиотеке пока пусто."
        if query:
            await query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return
    
    keyboard = student_materials_list_keyboard(materials)
    message = "🗂️ *Библиотека материалов*\n\nВыберите материал:"
    
    if query:
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def show_material_details(update: Update, context: ContextTypes.DEFAULT_TYPE, material_id: int):
    query = update.callback_query
    user = get_user_by_telegram_id(query.from_user.id)
    material = get_material_by_id(material_id)
    
    text = (f"*{material.title}*\n\n"
            f"{material.description or 'Описания нет.'}\n\n"
            f"🔗 *Ссылка:* {material.link}")

    # Determine the correct back button based on user role
    if user.role == UserRole.TUTOR:
        back_button = InlineKeyboardButton("⬅️ К списку материалов", callback_data="tutor_manage_library")
    else:
        back_button = InlineKeyboardButton("⬅️ К списку материалов", callback_data="materials_library")
        
    keyboard = InlineKeyboardMarkup([[back_button]])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown', disable_web_page_preview=True)

async def show_tutor_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_user_role(update, UserRole.TUTOR):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
        
    stats = get_dashboard_stats()
    month_name = datetime.now().strftime("%B")
    
    text = (
        f"📈 *Статистика за {month_name}*\n\n"
        f"🎓 *Всего учеников:* {stats['student_count']}\n"
        f"📚 *Проведено уроков:* {stats['lessons_this_month']}\n"
        f"✅ *Проверено ДЗ:* {stats['checked_hw_this_month']}\n"
        f"💰 *Оплачено уроков:* {stats['payments_sum_this_month']}"
    )
    
    await update.message.reply_text(text, parse_mode='Markdown')

# Alias for compatibility with bot.py
async def show_tutor_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_tutor_dashboard(update, context)

async def show_lesson_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the student's lesson history."""
    # Проверяем роль пользователя для text-сообщений (reply keyboard)
    if update.message and not check_user_role(update, UserRole.STUDENT):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
    
    query = update.callback_query
    user = get_user_by_telegram_id(update.effective_user.id)
    db = SessionLocal()
    lessons = db.query(Lesson).filter(Lesson.student_id == user.id).order_by(Lesson.date.desc()).all()
    db.close()

    if not lessons:
        message = "У вас еще не было уроков."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]])
        if query:
            await query.edit_message_text(message, reply_markup=keyboard)
        else:
            await update.message.reply_text(message, reply_markup=keyboard)
        return

    keyboard = student_lesson_list_keyboard(lessons)  # Используем специальную клавиатуру для студентов
    message = "📚 *История ваших уроков:*\n\n✅❌ - Посещение\n⚪🟡🟢 - Усвоение материала"
    
    if query:
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def student_view_lesson_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает детали урока для студента."""
    query = update.callback_query
    await query.answer()  # Обязательно отвечаем на callback_query
    
    lesson_id = int(query.data.split("_")[-1])
    
    db = SessionLocal()
    lesson = db.query(Lesson).options(joinedload(Lesson.homeworks)).filter(Lesson.id == lesson_id).first()
    db.close()
    
    if not lesson:
        await query.edit_message_text("❌ Урок не найден.")
        return
    
    # Формируем сообщение с деталями урока
    date_str = lesson.date.strftime('%d.%m.%Y')
    attended_str = "✅ Присутствовал" if lesson.is_attended else "❌ Отсутствовал"
    
    mastery_ru = {
        TopicMastery.NOT_LEARNED: "⚪ Не усвоено",
        TopicMastery.LEARNED: "🟡 Усвоено", 
        TopicMastery.MASTERED: "🟢 Закреплено"
    }.get(lesson.mastery_level, "❓ Неизвестно")
    
    message = f"📚 *Урок от {date_str}*\n\n"
    message += f"*Тема:* {lesson.topic}\n"
    message += f"*Посещение:* {attended_str}\n"
    message += f"*Усвоение:* {mastery_ru}\n"
    
    if lesson.skills_developed:
        message += f"*Изученные навыки:* {lesson.skills_developed}\n"
    
    if lesson.mastery_comment:
        message += f"*Комментарий:* {lesson.mastery_comment}\n"
    
    # Информация о ДЗ
    if lesson.homeworks:
        hw = lesson.homeworks[0]  # Берем первое ДЗ
        hw_status = {
            HomeworkStatus.PENDING: "⏳ К сдаче",
            HomeworkStatus.SUBMITTED: "📤 Сдано",
            HomeworkStatus.CHECKED: "✅ Проверено"
        }.get(hw.status, "❓")
        
        message += f"\n*Домашнее задание:* {hw_status}\n"
        message += f"*Описание:* {hw.description[:100]}{'...' if len(hw.description) > 100 else ''}\n"
        
        if hw.deadline:
            deadline_str = hw.deadline.strftime("%d.%m.%Y")
            message += f"*Дедлайн:* {deadline_str}\n"
    
    keyboard = student_lesson_details_keyboard(lesson)
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def show_student_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает достижения ученика."""
    # Проверяем роль пользователя для text-сообщений (reply keyboard)
    if update.message and not check_user_role(update, UserRole.STUDENT):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
    
    query = update.callback_query
    user = get_user_by_telegram_id(update.effective_user.id)
    
    achievements = get_student_achievements(user.id)
    
    if not achievements:
        text = (
            "🏆 *Ваши достижения*\n\n"
            "У вас пока нет достижений.\n"
            "Посещайте уроки, выполняйте домашние задания и зарабатывайте значки! 🎯"
        )
    else:
        text = f"🏆 *Ваши достижения* ({len(achievements)})\n\n"
        for achievement in achievements:
            earned_date = achievement.earned_at.strftime('%d.%m.%Y')
            text += f"{achievement.icon} *{achievement.title}*\n"
            if achievement.description:
                text += f"   _{achievement.description}_\n"
            text += f"   Получено: {earned_date}\n\n"
    
    # Добавляем информацию о текущем streak
    db = SessionLocal()
    student = db.query(User).filter(User.id == user.id).first()
    if student and student.streak_days > 0:
        text += f"🔥 *Текущая серия:* {student.streak_days} дней подряд\n"
    db.close()
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]])
    
    if query:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def show_payment_and_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает детальную информацию о балансе и посещаемости ученика."""
    # Проверяем роль пользователя для text-сообщений (reply keyboard)
    if update.message and not check_user_role(update, UserRole.STUDENT):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
    
    query = update.callback_query
    user = get_user_by_telegram_id(update.effective_user.id)
    
    balance = get_student_balance(user.id)
    
    db = SessionLocal()
    # Детальная статистика
    lessons_attended = db.query(Lesson).filter(Lesson.student_id == user.id, Lesson.is_attended == True).count()
    total_lessons = db.query(Lesson).filter(Lesson.student_id == user.id).count()
    missed_lessons = total_lessons - lessons_attended
    
    # Последние оплаты
    recent_payments = db.query(Payment).filter(Payment.student_id == user.id).order_by(Payment.payment_date.desc()).limit(5).all()
    total_paid = db.query(Payment).filter(Payment.student_id == user.id).all()
    total_paid_lessons = sum(p.lessons_paid for p in total_paid)
    
    # Streak информация
    student = db.query(User).filter(User.id == user.id).first()
    
    db.close()

    # Определяем статус баланса
    if balance > 5:
        balance_status = "🟢 Отличный баланс"
    elif balance > 2:
        balance_status = "🟡 Хороший баланс"
    elif balance > 0:
        balance_status = "🟠 Низкий баланс"
    else:
        balance_status = "🔴 Необходимо пополнение"
    
    # Посещаемость в процентах
    attendance_rate = (lessons_attended / total_lessons * 100) if total_lessons > 0 else 0
    
    text = (
        f"💰 *Баланс уроков*\n\n"
        f"💳 *Остаток занятий:* {balance}\n"
        f"📊 *Статус:* {balance_status}\n\n"
        f"📈 *Статистика посещаемости*\n"
        f"✅ *Посещено:* {lessons_attended} уроков\n"
        f"❌ *Пропущено:* {missed_lessons} уроков\n"
        f"📊 *Процент посещения:* {attendance_rate:.1f}%\n\n"
        f"💵 *Всего оплачено:* {total_paid_lessons} уроков"
    )
    
    if student and student.streak_days > 0:
        text += f"\n🔥 *Активная серия:* {student.streak_days} дней подряд"
    
    # Добавляем последние оплаты
    if recent_payments:
        text += "\n\n💸 *Последние оплаты:*\n"
        for payment in recent_payments[:3]:  # Показываем только 3 последние
            date_str = payment.payment_date.strftime('%d.%m.%Y')
            text += f"• {payment.lessons_paid} уроков - {date_str}\n"
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]])
    
    if query:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
