# -*- coding: utf-8 -*-
"""
Модуль обработчиков для функций репетитора.
Содержит все функции управления учениками, уроками, домашними заданиями, отчетами и библиотекой материалов.
"""

import os
import re
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import Forbidden
from telegram.helpers import escape_markdown
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from ..database import (
    SessionLocal, User, UserRole, Lesson, Homework, Payment, Material, Achievement,
    get_user_by_telegram_id, get_all_students, get_user_by_id,
    get_lesson_by_id, get_homework_by_id,
    get_lessons_for_student_by_month, get_payments_for_student_by_month,
    get_all_materials, get_material_by_id, delete_material_by_id,
    get_dashboard_stats, HomeworkStatus, TopicMastery, AttendanceStatus, get_student_balance,
    get_student_achievements, award_achievement, update_study_streak, check_points_achievements,
    shift_lessons_after_cancellation
)
from ..keyboards import (
    tutor_main_keyboard, tutor_student_list_keyboard, tutor_student_profile_keyboard,
    tutor_lesson_list_keyboard, tutor_lesson_details_keyboard, tutor_cancel_confirmation_keyboard,
    tutor_delete_confirm_keyboard, tutor_edit_lesson_status_keyboard,
    tutor_check_homework_keyboard, tutor_select_student_for_report_keyboard,
    tutor_select_month_for_report_keyboard, tutor_library_management_keyboard,
    tutor_select_material_to_delete_keyboard, broadcast_confirm_keyboard
)
from ..chart_generator import generate_progress_chart
from .common import show_main_menu

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
SELECT_STUDENT_FOR_REPORT, SELECT_MONTH_FOR_REPORT = range(2)
ADD_MATERIAL_TITLE, ADD_MATERIAL_LINK, ADD_MATERIAL_DESC = range(3)
BROADCAST_MESSAGE, BROADCAST_CONFIRM = range(2)
EDIT_LESSON_STATUS, EDIT_LESSON_COMMENT = range(2)

# --- Helper Functions ---
def generate_access_code(length=8):
    """Генерирует уникальный код доступа."""
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def check_user_role(update: Update, required_role: UserRole) -> bool:
    """Проверяет роль пользователя."""
    user = get_user_by_telegram_id(update.effective_user.id)
    return user and user.role == required_role

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет текущий диалог и возвращается к карточке урока если возможно."""
    lesson_id = context.user_data.get('lesson_id')
    context.user_data.clear()
    await update.message.reply_text("Действие отменено.")
    if lesson_id:
        # Возвращаемся к карточке урока после отмены
        await show_lesson_details(update, context, lesson_id)
    return ConversationHandler.END

async def show_material_details(update: Update, context: ContextTypes.DEFAULT_TYPE, material_id: int):
    """Показывает детали материала (доступно и репетитору, и ученику)."""
    query = update.callback_query
    user = get_user_by_telegram_id(query.from_user.id)
    material = get_material_by_id(material_id)
    
    text = (f"*{material.title}*\n\n"
            f"{material.description or 'Описания нет.'}\n\n"
            f"🔗 *Ссылка:* {material.link}")

    # Определяем правильную кнопку "Назад" в зависимости от роли пользователя
    if user.role == UserRole.TUTOR:
        back_button = InlineKeyboardButton("⬅️ К списку материалов", callback_data="tutor_manage_library")
    else:
        back_button = InlineKeyboardButton("⬅️ К списку материалов", callback_data="materials_library")
        
    keyboard = InlineKeyboardMarkup([[back_button]])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown', disable_web_page_preview=True)

# --- Student Management ---
async def show_student_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список всех учеников репетитора."""
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
    """Показывает профиль конкретного ученика."""
    db = SessionLocal()
    try:
        # Используем joinedload для "жадной" загрузки связанного родителя
        student = db.query(User).options(joinedload(User.parent)).filter(User.id == student_id).first()
        
        if not student:
            await update.callback_query.edit_message_text("Ученик не найден.")
            return
        
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
    """Начинает процесс добавления нового ученика."""
    if not check_user_role(update, UserRole.TUTOR):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return ConversationHandler.END
        
    await update.message.reply_text("Введите ФИО нового ученика:")
    return ADD_STUDENT_NAME

async def tutor_get_student_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает имя ученика и запрашивает информацию о родителе."""
    context.user_data['student_name'] = update.message.text
    await update.message.reply_text("Введите ФИО родителя (или 'пропустить' если родителя нет):")
    return ADD_PARENT_CODE

async def tutor_get_parent_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создает ученика и родителя (если указан)."""
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
    """Начинает процесс редактирования имени ученика."""
    query = update.callback_query
    student_id = int(query.data.split("_")[-1])
    context.user_data['student_id_to_edit'] = student_id
    student = get_user_by_id(student_id)
    await query.edit_message_text(f"Введите новое ФИО для ученика {student.full_name}:")
    return EDIT_STUDENT_NAME

async def tutor_get_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет новое имя ученика."""
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
    return ConversationHandler.END

async def tutor_add_parent_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс добавления родителя к существующему ученику."""
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
    """Создает родителя и привязывает к ученику."""
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
        # Используем joinedload для предзагрузки
        student = db.query(User).options(
            joinedload(User.student_lessons),
            joinedload(User.payments)
        ).filter(User.id == student_id).first()

        if student:
            name = student.full_name
            # SQLAlchemy благодаря cascade="all, delete-orphan" сам удалит связанные записи
            db.delete(student)
            db.commit()
            await query.edit_message_text(f"✅ Ученик *{name}* и все его данные были успешно удалены.", parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ Не удалось найти ученика для удаления.")
    except Exception as e:
        db.rollback()
        await query.edit_message_text("Произошла ошибка при удалении. Попробуйте позже.")
    finally:
        db.close()

    # Показываем обновленный список учеников
    await show_student_list(update, context)

# --- Lesson Management ---
async def show_tutor_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE, student_id: int):
    """Показывает список уроков конкретного ученика."""
    student = get_user_by_id(student_id)
    db = SessionLocal()
    lessons = db.query(Lesson).filter(Lesson.student_id == student_id).order_by(Lesson.date.desc()).all()
    db.close()
    keyboard = tutor_lesson_list_keyboard(lessons, student_id)
    await update.callback_query.edit_message_text(f"Уроки ученика {student.full_name}:", reply_markup=keyboard)

async def show_lesson_details(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int):
    """Показывает детали конкретного урока."""
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
    """Начинает процесс добавления нового урока."""
    query = update.callback_query
    student_id = int(query.data.split("_")[-1])
    context.user_data['lesson_student_id'] = student_id
    await query.edit_message_text("Введите тему нового урока:")
    return ADD_LESSON_TOPIC

async def tutor_get_lesson_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает тему урока и запрашивает дату."""
    context.user_data['lesson_topic'] = update.message.text
    await update.message.reply_text("Введите дату урока (ДД.ММ.ГГГГ):")
    return ADD_LESSON_DATE

async def tutor_get_lesson_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает дату урока и запрашивает навыки."""
    try:
        context.user_data['lesson_date'] = datetime.strptime(update.message.text, "%d.%m.%Y")
        await update.message.reply_text("Какие навыки развивал урок?")
        return ADD_LESSON_SKILLS
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите дату как ДД.ММ.ГГГГ:")
        return ADD_LESSON_DATE

async def tutor_get_lesson_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает навыки и создает урок."""
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

async def tutor_mark_lesson_attended(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int):
    """Отмечает урок как посещенный (legacy функция)."""
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
        
        # НОВАЯ ФИШКА: При ЛЮБОЙ отмене урока сдвигаем все будущие уроки
        cancellation_statuses = [AttendanceStatus.EXCUSED_ABSENCE, AttendanceStatus.UNEXCUSED_ABSENCE, AttendanceStatus.RESCHEDULED]
        if new_status in cancellation_statuses and old_status not in cancellation_statuses:
            shift_lessons_after_cancellation(lesson_id)
            print(f"DEBUG: Lesson {lesson_id} cancelled with status {new_status.value}, shifted all future lessons")
        
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
    """Устанавливает уровень усвоения материала урока."""
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

# --- Homework Management ---
async def tutor_add_hw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс добавления домашнего задания."""
    query = update.callback_query
    lesson_id = int(query.data.split("_")[-1])
    context.user_data['hw_lesson_id'] = lesson_id
    await query.edit_message_text("Введите описание домашнего задания:")
    return ADD_HW_DESC

async def tutor_get_hw_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает описание ДЗ и запрашивает дедлайн."""
    context.user_data['hw_description'] = update.message.text
    await update.message.reply_text("Введите дедлайн (ДД.ММ.ГГГГ):")
    return ADD_HW_DEADLINE

async def tutor_get_hw_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает дедлайн ДЗ и запрашивает ссылку."""
    try:
        context.user_data['hw_deadline'] = datetime.strptime(update.message.text, "%d.%m.%Y")
        await update.message.reply_text("Прикрепите ссылку (или /skip):")
        return ADD_HW_LINK
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите дату как ДД.ММ.ГГГГ:")
        return ADD_HW_DEADLINE

async def tutor_get_hw_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает ссылку ДЗ и запрашивает фото."""
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
    """Получает фотографии для ДЗ."""
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
    """Создает домашнее задание с собранными данными."""
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
    return ConversationHandler.END

async def tutor_check_homework(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int):
    """Показывает домашнее задание для проверки."""
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

async def tutor_set_homework_status(update: Update, context: ContextTypes.DEFAULT_TYPE, hw_id: int, status_value: str):
    """Устанавливает статус домашнего задания."""
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

# --- Payment Management ---
async def tutor_add_payment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс добавления оплаты."""
    query = update.callback_query
    student_id = int(query.data.split("_")[-1])
    context.user_data['payment_student_id'] = student_id
    await query.edit_message_text("Введите количество оплаченных уроков:")
    return ADD_PAYMENT_AMOUNT

async def tutor_get_payment_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает сумму оплаты и создает запись."""
    try:
        amount = int(update.message.text)
        student_id = context.user_data.get('payment_student_id')
        print(f"DEBUG: Adding payment - student_id: {student_id}, amount: {amount}")
        
        db = SessionLocal()
        new_payment = Payment(student_id=student_id, lessons_paid=amount)
        db.add(new_payment)
        db.commit()
        
        # Проверяем баланс после добавления
        from ..database import get_student_balance
        new_balance = get_student_balance(student_id)
        print(f"DEBUG: New balance for student {student_id}: {new_balance}")
        
        db.close()
        await update.message.reply_text(f"✅ Оплата на {amount} уроков добавлена.\n💰 Новый баланс: {new_balance} уроков")
        
        # Показываем обновленную карточку ученика
        context.user_data['temp_student_id'] = student_id
        await show_student_profile_after_update(update, context, student_id)
        
    except ValueError:
        await update.message.reply_text("Введите число.")
        return ADD_PAYMENT_AMOUNT
    except Exception as e:
        print(f"ERROR in tutor_get_payment_amount: {e}")
        await update.message.reply_text("❌ Ошибка при добавлении оплаты.")
    
    context.user_data.clear()
    return ConversationHandler.END

async def show_student_profile_after_update(update: Update, context: ContextTypes.DEFAULT_TYPE, student_id: int):
    """Показывает обновленную карточку ученика после изменений."""
    db = SessionLocal()
    try:
        student = db.query(User).options(joinedload(User.parent)).filter(User.id == student_id).first()
        if not student:
            return
        
        balance = get_student_balance(student_id)
        parent_info = student.parent.full_name if student.parent else "Не привязан"
        
        text = (f"*Профиль ученика: {student.full_name}*\n\n"
                f"🏅 *Баллы:* {student.points}\n"
                f"- Код доступа: `{student.access_code}`\n"
                f"- Остаток занятий: *{balance}*\n"
                f"- Родитель: *{parent_info}*\n\n"
                "Выберите действие:")
        keyboard = tutor_student_profile_keyboard(student_id)
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    finally:
        db.close()
    return ConversationHandler.END

# --- Analytics and Reports ---
async def show_analytics_chart(update: Update, context: ContextTypes.DEFAULT_TYPE, student_id: int):
    """Генерирует и отправляет график прогресса ученика."""
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

async def show_tutor_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает панель статистики для репетитора."""
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

# Alias for compatibility
async def show_tutor_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Алиас для show_tutor_dashboard."""
    await show_tutor_dashboard(update, context)

async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс создания отчета."""
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
    """Получает выбор ученика для отчета."""
    query = update.callback_query
    student_id = int(query.data.split("_")[-1])
    context.user_data['report_student_id'] = student_id
    keyboard = tutor_select_month_for_report_keyboard(student_id)
    await query.edit_message_text("Выберите месяц:", reply_markup=keyboard)
    return SELECT_MONTH_FOR_REPORT

async def report_select_month_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерирует отчет для выбранного ученика и месяца."""
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
    """Отменяет создание отчета."""
    await update.callback_query.edit_message_text("Создание отчета отменено.")
    context.user_data.clear()
    return ConversationHandler.END

# --- Material Library Management ---
async def tutor_manage_library(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает интерфейс управления библиотекой материалов."""
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
    """Начинает процесс добавления материала."""
    await update.callback_query.edit_message_text("Введите название материала:")
    return ADD_MATERIAL_TITLE

async def tutor_get_material_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает название материала и запрашивает ссылку."""
    context.user_data['material_title'] = update.message.text
    await update.message.reply_text("Отправьте ссылку:")
    return ADD_MATERIAL_LINK

async def tutor_get_material_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает ссылку на материал и запрашивает описание."""
    context.user_data['material_link'] = update.message.text
    await update.message.reply_text("Введите описание (или /skip):")
    return ADD_MATERIAL_DESC

async def tutor_get_material_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает описание и создает материал."""
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
    return ConversationHandler.END

async def tutor_delete_material_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список материалов для удаления."""
    materials = get_all_materials()
    if not materials:
        await update.callback_query.edit_message_text("Библиотека пуста.")
        return
    keyboard = tutor_select_material_to_delete_keyboard(materials)
    await update.callback_query.edit_message_text("Выберите материал для удаления:", reply_markup=keyboard)

async def tutor_delete_material_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, material_id: int):
    """Удаляет выбранный материал."""
    delete_material_by_id(material_id)
    await update.callback_query.answer("Материал удален.")
    await tutor_manage_library(update, context)

# --- Broadcast System ---
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

# --- Communication ---
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
async def tutor_confirm_lesson_cancellation(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id_status: str):
    """Показывает подтверждение перед отменой урока с предупреждением о сдвиге тем."""
    try:
        # Парсим lesson_id и status из строки вида "123_excused_absence"
        parts = lesson_id_status.split('_')
        lesson_id = int(parts[0])
        status_str = '_'.join(parts[1:])
        
        db = SessionLocal()
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            await update.callback_query.answer("Урок не найден")
            db.close()
            return
        
        # Проверяем, есть ли будущие уроки для сдвига
        future_lessons_count = db.query(Lesson).filter(
            Lesson.student_id == lesson.student_id,
            Lesson.date > lesson.date
        ).count()
        
        status_names = {
            'excused_absence': 'уважительной причине',
            'unexcused_absence': 'неуважительной причине', 
            'rescheduled': 'переносе'
        }
        
        warning_text = ""
        if future_lessons_count > 0:
            warning_text = f"\n\n⚠️ **ВНИМАНИЕ**: После отмены произойдет автоматический сдвиг тем для {future_lessons_count} будущих уроков!\n\nТема отмененного урока \"**{lesson.topic}**\" будет перенесена на следующий урок."
        
        confirmation_text = (
            f"🔄 **Подтверждение отмены урока**\n\n"
            f"📅 Дата: {lesson.date.strftime('%d.%m.%Y')}\n"
            f"📚 Тема: **{lesson.topic}**\n"
            f"👤 Ученик: **{lesson.student.full_name}**\n\n"
            f"Вы уверены, что хотите отменить урок по **{status_names.get(status_str, status_str)}**?"
            f"{warning_text}"
        )
        
        keyboard = tutor_cancel_confirmation_keyboard(lesson_id, status_str)
        await update.callback_query.edit_message_text(
            confirmation_text, 
            reply_markup=keyboard, 
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"ERROR in tutor_confirm_lesson_cancellation: {e}")
        await update.callback_query.answer("Ошибка при обработке запроса")
    finally:
        db.close()