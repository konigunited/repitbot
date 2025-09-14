# -*- coding: utf-8 -*-
"""
Модуль обработчиков для родителей - микросервис
Содержит все функции для работы родителей с системой
"""

import os
from datetime import datetime, timedelta
from ..timezone_utils import now as tz_now
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy.orm import joinedload

from ..database import (
    SessionLocal, User, UserRole, Lesson, Homework, Payment, Achievement,
    get_user_by_telegram_id, get_user_by_id, get_student_balance,
    HomeworkStatus, TopicMastery, AttendanceStatus
)
from ..keyboards import parent_main_keyboard, parent_child_menu_keyboard
from ..logger import setup_logging, log_user_action
from .common import show_main_menu

logger = setup_logging()

# Состояния диалогов
CHAT_WITH_TUTOR = 1

async def safe_edit_or_reply(update, text, reply_markup=None, parse_mode=None):
    """Безопасно редактирует сообщение или отправляет новое, если редактирование невозможно"""
    try:
        if update.callback_query.message.text:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            # Если сообщение содержит фото или другой контент, отправляем новое сообщение
            await update.callback_query.message.delete()
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        # Если не удается отредактировать, отправляем новое сообщение
        try:
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except:
            # Крайний случай - отправляем в чат
            await update.effective_chat.send_message(text, reply_markup=reply_markup, parse_mode=parse_mode)

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

def check_parent_access(update: Update) -> User:
    """Проверяет, что пользователь - родитель"""
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user or user.role != UserRole.PARENT:
        return None
    return user

async def show_parent_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает дашборд родителя с выбором ребенка"""
    parent = check_parent_access(update)
    if not parent:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    log_user_action(parent.telegram_id, "parent_dashboard", "Просмотр дашборда родителя")
    
    db = SessionLocal()
    try:
        # Получаем всех детей этого родителя (как основной, так и второй родитель)
        children = db.query(User).filter(
            (User.parent_id == parent.id) | (User.second_parent_id == parent.id),
            User.role == UserRole.STUDENT
        ).all()
        
        if not children:
            text = f"👨‍👩‍👧‍👦 **Родительская панель**\n\n"
            text += f"Добро пожаловать, {parent.full_name}!\n\n"
            text += f"У вас пока нет привязанных детей.\n"
            text += f"Обратитесь к репетитору для добавления ученика."
            
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="parent_dashboard")],
                [InlineKeyboardButton("💬 Написать репетитору", callback_data="parent_chat_with_tutor")]
            ]
        else:
            text = f"👨‍👩‍👧‍👦 **Родительская панель**\n\n"
            text += f"Добро пожаловать, {parent.full_name}!\n"
            text += f"Детей в системе: {len(children)}\n\n"
            text += f"Выберите ребенка:"
            
            keyboard = []
            for child in children:
                # Краткая статистика по ребенку
                balance = get_student_balance(child.id)
                text += f"\n👤 **{child.full_name}**\n"
                text += f"   Баллы: {child.points} | Баланс: {balance} уроков\n"
                
                keyboard.append([InlineKeyboardButton(
                    f"👤 {child.full_name}", 
                    callback_data=f"parent_child_{child.id}"
                )])
            
            keyboard.append([InlineKeyboardButton("💬 Написать репетитору", callback_data="parent_chat_with_tutor")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            await update.callback_query.answer()
    
    finally:
        db.close()

# Первая версия функции удалена - используем более полную версию ниже

# Первая версия show_child_progress удалена - используем более полную версию ниже в строке 413+

async def show_child_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE, child_id: int):
    """Показывает расписание ребенка родителю"""
    query = update.callback_query
    await query.answer()
    
    student_id = child_id
    student = get_user_by_id(student_id)
    
    if not student:
        await query.edit_message_text("Ученик не найден.")
        return
    
    # Проверяем права доступа
    parent = get_user_by_telegram_id(update.effective_user.id)
    if student.parent_id != parent.id and student.second_parent_id != parent.id:
        await query.edit_message_text("У вас нет доступа к этой информации.")
        return
    
    from ..database import Lesson
    from datetime import datetime
    
    db = SessionLocal()
    
    # Получаем будущие уроки
    now = tz_now().replace(tzinfo=None)
    future_lessons = db.query(Lesson).filter(
        Lesson.student_id == student_id,
        Lesson.date >= now
    ).order_by(Lesson.date).limit(10).all()
    
    db.close()
    
    if not future_lessons:
        message = f"📅 *Расписание {student.full_name}*\n\nБлижайших уроков нет."
    else:
        message = f"📅 *Расписание {student.full_name}*\n\n"
        for i, lesson in enumerate(future_lessons, 1):
            date_str = lesson.date.strftime('%d.%m.%Y в %H:%M')
            message += f"{i}. *{date_str}*\n   {lesson.topic or 'Тема не указана'}\n"
            # Показать заметку репетитора для этого дня, если есть
            try:
                from ..database import get_day_note
                tutor_id = lesson.tutor_id
                weekday = lesson.date.strftime('%A').lower()
                weekday_map = {
                    'monday': 'monday', 'tuesday': 'tuesday', 'wednesday': 'wednesday',
                    'thursday': 'thursday', 'friday': 'friday', 'saturday': 'saturday', 'sunday': 'sunday'
                }
                day_key = weekday_map.get(weekday, None)
                if day_key:
                    note = get_day_note(lesson.student_id, tutor_id, day_key)
                    if note:
                        message += f"   📝 Заметка репетитора: {note}\n\n"
                    else:
                        message += "\n"
                else:
                    message += "\n"
            except Exception:
                message += "\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад к ребенку", callback_data=f"parent_child_{student_id}")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="parent_dashboard")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def show_child_payments(update: Update, context: ContextTypes.DEFAULT_TYPE, child_id: int):
    """Показывает информацию об оплатах ребенка"""
    query = update.callback_query
    await query.answer()
    
    student_id = child_id
    student = get_user_by_id(student_id)
    
    if not student:
        await query.edit_message_text("Ученик не найден.")
        return
    
    # Проверяем права доступа
    parent = get_user_by_telegram_id(update.effective_user.id)
    if student.parent_id != parent.id and student.second_parent_id != parent.id:
        await query.edit_message_text("У вас нет доступа к этой информации.")
        return
    
    from ..database import get_student_balance, Payment
    
    balance = get_student_balance(student_id)
    
    db = SessionLocal()
    
    # Последние 10 платежей
    recent_payments = db.query(Payment).filter(
        Payment.student_id == student_id
    ).order_by(Payment.payment_date.desc()).limit(10).all()
    
    db.close()
    
    message = f"💰 *Оплаты {student.full_name}*\n\n"
    message += f"💳 *Текущий баланс:* {balance} уроков\n\n"
    
    if recent_payments:
        message += "📋 *История оплат:*\n"
        for payment in recent_payments:
            date_str = payment.payment_date.strftime('%d.%m.%Y')
            message += f"   • {date_str}: +{payment.lessons_paid} уроков\n"
    else:
        message += "📋 История оплат пуста.\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад к ребенку", callback_data=f"parent_child_{student_id}")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="parent_dashboard")]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def parent_generate_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерирует график прогресса ребенка для родителя"""
    query = update.callback_query
    await query.answer()
    
    student_id = int(query.data.split("_")[-1])
    student = get_user_by_id(student_id)
    
    if not student:
        await query.edit_message_text("Ученик не найден.")
        return
    
    # Проверяем права доступа
    parent = get_user_by_telegram_id(update.effective_user.id)
    if student.parent_id != parent.id and student.second_parent_id != parent.id:
        await query.edit_message_text("У вас нет доступа к этой информации.")
        return
    
    await query.edit_message_text("📊 Генерируем график прогресса...")
    
    from ..chart_generator import generate_progress_chart
    
    chart_path = generate_progress_chart(student_id)
    
    if chart_path:
        try:
            with open(chart_path, 'rb') as chart_file:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад к ребенку", callback_data=f"parent_child_{student_id}")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="parent_dashboard")]
                ])
                
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=chart_file,
                    caption=f"📊 *Прогресс {student.full_name}*\n\nТекущие баллы: *{student.points}*",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                
                # Удаляем сообщение о генерации
                await query.message.delete()
        except Exception as e:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад к ребенку", callback_data=f"parent_child_{student_id}")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="parent_dashboard")]
            ])
            await query.edit_message_text(
                "❌ Не удалось сгенерировать график прогресса.",
                reply_markup=keyboard
            )
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад к ребенку", callback_data=f"parent_child_{student_id}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="parent_dashboard")]
        ])
        await query.edit_message_text(
            "❌ Недостаточно данных для построения графика.",
            reply_markup=keyboard
        )


async def show_child_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, child_id: int):
    """Показывает меню для конкретного ребенка"""
    query = update.callback_query
    await query.answer()  # Сразу отвечаем на callback
    
    parent = check_parent_access(update)
    if not parent:
        await query.edit_message_text("❌ Доступ запрещен")
        return
    
    student_id = child_id
    
    log_user_action(parent.telegram_id, "child_menu_view", f"Просмотр меню ребенка ID:{student_id}")
    
    db = SessionLocal()
    try:
        student = db.query(User).filter(
            User.id == student_id,
            (User.parent_id == parent.id) | (User.second_parent_id == parent.id),
            User.role == UserRole.STUDENT
        ).first()
        
        if not student:
            await update.callback_query.answer("❌ Ребенок не найден")
            return
        
        # Получаем основную статистику
        balance = get_student_balance(student.id)
        
        # Последний урок
        last_lesson = db.query(Lesson).filter(
            Lesson.student_id == student.id
        ).order_by(Lesson.date.desc()).first()
        
        # Активные ДЗ
        active_hw = db.query(Homework).join(Lesson).filter(
            Lesson.student_id == student.id,
            Homework.status.in_([HomeworkStatus.PENDING, HomeworkStatus.SUBMITTED])
        ).count()
        
        text = f"**{student.full_name}**\n\n"
        text += f"**Баллы:** {student.points}\n"
        text += f"**Баланс уроков:** {balance}\n"
        text += f"**Серия дней:** {student.streak_days}\n\n"
        
        if last_lesson:
            last_date = last_lesson.date.strftime('%d.%m.%Y')
            text += f"**Последний урок:** {last_date}\n"
            text += f"   Тема: {last_lesson.topic}\n\n"
        
        if active_hw > 0:
            text += f"**Активных ДЗ:** {active_hw}\n\n"
        
        text += "Выберите действие:"
        
        keyboard = [
            [
                InlineKeyboardButton("Прогресс", callback_data=f"parent_progress_{student.id}"),
                InlineKeyboardButton("Расписание", callback_data=f"parent_schedule_{student.id}")
            ],
            [
                InlineKeyboardButton("Домашние задания", callback_data=f"parent_homework_{student.id}"),
                InlineKeyboardButton("Оплаты", callback_data=f"parent_payments_{student.id}")
            ],
            [
                InlineKeyboardButton("История уроков", callback_data=f"parent_lessons_{student.id}"),
                InlineKeyboardButton("Достижения", callback_data=f"parent_achievements_{student.id}")
            ],
            [InlineKeyboardButton("К списку детей", callback_data="parent_dashboard")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await safe_edit_or_reply(update, text, reply_markup, 'Markdown')
    
    finally:
        db.close()


async def show_child_progress(update: Update, context: ContextTypes.DEFAULT_TYPE, child_id: int):
    """Показывает подробный прогресс ребенка"""
    query = update.callback_query
    await query.answer()  # Сразу отвечаем на callback
    
    parent = check_parent_access(update)
    if not parent:
        await query.edit_message_text("❌ Доступ запрещен")
        return
    
    student_id = child_id
    
    log_user_action(parent.telegram_id, "child_progress_view", f"Просмотр прогресса ребенка ID:{student_id}")
    
    db = SessionLocal()
    try:
        student = db.query(User).filter(
            User.id == student_id,
            (User.parent_id == parent.id) | (User.second_parent_id == parent.id),
            User.role == UserRole.STUDENT
        ).first()
        
        if not student:
            await update.callback_query.answer("❌ Ребенок не найден")
            return
        
        # Статистика за месяц
        month_start = tz_now().replace(day=1, tzinfo=None)
        monthly_lessons = db.query(Lesson).filter(
            Lesson.student_id == student.id,
            Lesson.date >= month_start,
            Lesson.attendance_status == AttendanceStatus.ATTENDED
        ).count()
        
        total_monthly = db.query(Lesson).filter(
            Lesson.student_id == student.id,
            Lesson.date >= month_start
        ).count()
        
        # ДЗ за месяц
        monthly_hw = db.query(Homework).join(Lesson).filter(
            Lesson.student_id == student.id,
            Homework.created_at >= month_start
        ).count()
        
        completed_hw = db.query(Homework).join(Lesson).filter(
            Lesson.student_id == student.id,
            Homework.created_at >= month_start,
            Homework.status == HomeworkStatus.CHECKED
        ).count()
        
        # Общая статистика
        total_lessons = db.query(Lesson).filter(
            Lesson.student_id == student.id,
            Lesson.attendance_status == AttendanceStatus.ATTENDED
        ).count()
        
        balance = get_student_balance(student.id)
        
        text = f"**Прогресс {student.full_name}**\n\n"
        text += f"**Общие показатели:**\n"
        text += f"   Баллы: {student.points}\n"
        text += f"   Серия: {student.streak_days} дней\n"
        text += f"   Всего уроков: {total_lessons}\n"
        text += f"   Баланс: {balance} уроков\n\n"
        
        text += f"**За текущий месяц:**\n"
        text += f"   Посещено: {monthly_lessons} из {total_monthly}\n"
        
        if total_monthly > 0:
            attendance_rate = (monthly_lessons / total_monthly) * 100
            text += f"   Посещаемость: {attendance_rate:.1f}%\n"
        
        text += f"   ДЗ выполнено: {completed_hw} из {monthly_hw}\n"
        
        if monthly_hw > 0:
            hw_rate = (completed_hw / monthly_hw) * 100
            text += f"   Выполнение ДЗ: {hw_rate:.1f}%\n"
        
        keyboard = [
            [InlineKeyboardButton("График прогресса", callback_data=f"parent_chart_{student.id}")],
            [InlineKeyboardButton("К ребенку", callback_data=f"parent_child_{student.id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await safe_edit_or_reply(update, text, reply_markup, 'Markdown')
    
    finally:
        db.close()


async def show_child_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает домашние задания ребенка"""
    parent = check_parent_access(update)
    if not parent:
        await update.callback_query.answer("❌ Доступ запрещен")
        return
    
    student_id = int(update.callback_query.data.split("_")[-1])
    
    log_user_action(parent.telegram_id, "child_homework_view", f"Просмотр ДЗ ребенка ID:{student_id}")
    
    db = SessionLocal()
    try:
        student = db.query(User).filter(
            User.id == student_id,
            (User.parent_id == parent.id) | (User.second_parent_id == parent.id),
            User.role == UserRole.STUDENT
        ).first()
        
        if not student:
            await update.callback_query.answer("❌ Ребенок не найден")
            return
        
        # Получаем последние ДЗ
        homeworks = db.query(Homework).join(Lesson).filter(
            Lesson.student_id == student.id
        ).order_by(Homework.deadline.desc()).limit(10).all()
        
        if not homeworks:
            text = f"📝 **ДЗ {student.full_name}**\n\nДомашних заданий пока нет"
            keyboard = [[InlineKeyboardButton("🔙 К ребенку", callback_data=f"parent_child_{student.id}")]]
        else:
            text = f"📝 **ДЗ {student.full_name}** (последние 10)\n\n"
            keyboard = []
            
            for hw in homeworks:
                status_ru = HOMEWORK_STATUS_RU.get(hw.status, "Неизвестно")
                deadline_str = hw.deadline.strftime('%d.%m') if hw.deadline else "Без срока"
                
                # Проверяем просрочку
                is_overdue = (hw.deadline and hw.deadline < tz_now().replace(tzinfo=None) 
                             and hw.status == HomeworkStatus.PENDING)
                overdue_mark = "🔴 " if is_overdue else ""
                
                status_emoji = {
                    HomeworkStatus.PENDING: "⏳",
                    HomeworkStatus.SUBMITTED: "📤",
                    HomeworkStatus.CHECKED: "✅"
                }.get(hw.status, "❓")
                
                text += f"{overdue_mark}{status_emoji} **{hw.lesson.topic}**\n"
                text += f"   📅 {deadline_str} | {status_ru}\n"
                text += f"   📖 {hw.description[:50]}{'...' if len(hw.description) > 50 else ''}\n\n"
                
                keyboard.append([InlineKeyboardButton(
                    f"📝 {hw.lesson.topic[:25]}...",
                    callback_data=f"parent_hw_detail_{hw.id}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 К ребенку", callback_data=f"parent_child_{student.id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        await update.callback_query.answer()
    
    finally:
        db.close()


async def show_child_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает достижения ребенка"""
    parent = check_parent_access(update)
    if not parent:
        await update.callback_query.answer("❌ Доступ запрещен")
        return
    
    student_id = int(update.callback_query.data.split("_")[-1])
    
    db = SessionLocal()
    try:
        student = db.query(User).filter(
            User.id == student_id,
            (User.parent_id == parent.id) | (User.second_parent_id == parent.id),
            User.role == UserRole.STUDENT
        ).first()
        
        if not student:
            await update.callback_query.answer("❌ Ребенок не найден")
            return
        
        achievements = db.query(Achievement).filter(
            Achievement.student_id == student.id
        ).order_by(Achievement.earned_at.desc()).all()
        
        if not achievements:
            text = f"🏆 **Достижения {student.full_name}**\n\n"
            text += f"Достижений пока нет.\n"
            text += f"Продолжайте учиться!"
        else:
            text = f"🏆 **Достижения {student.full_name}**\n\n"
            text += f"Всего наград: {len(achievements)}\n\n"
            
            for achievement in achievements:
                earned_date = achievement.earned_at.strftime('%d.%m.%Y')
                text += f"{achievement.icon} **{achievement.title}**\n"
                text += f"   {achievement.description}\n"
                text += f"   📅 {earned_date}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🔙 К ребенку", callback_data=f"parent_child_{student.id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        await update.callback_query.answer()
    
    finally:
        db.close()


# --- Коммуникация с репетитором ---
async def parent_chat_with_tutor_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает чат родителя с репетитором"""
    parent = check_parent_access(update)
    if not parent:
        if update.message:
            await update.message.reply_text("❌ Доступ запрещен")
        else:
            await update.callback_query.answer("❌ Доступ запрещен")
        return ConversationHandler.END
    
    text = (
        f"💬 **Чат с репетитором**\n\n"
        f"Напишите ваше сообщение, и оно будет отправлено репетитору.\n"
        f"Вы можете отправить:\n"
        f"• Текстовое сообщение\n"
        f"• Фотографию\n"
        f"• Документ\n\n"
        f"Для выхода из чата отправьте /cancel"
    )
    
    if update.message:
        await update.message.reply_text(text, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown')
        await update.callback_query.answer()
    
    return CHAT_WITH_TUTOR


async def parent_forward_message_to_tutor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылает сообщение родителя репетитору"""
    parent = check_parent_access(update)
    if not parent:
        await update.message.reply_text("❌ Доступ запрещен")
        return ConversationHandler.END
    
    db = SessionLocal()
    try:
        # Находим репетитора
        tutor = db.query(User).filter(User.role == UserRole.TUTOR).first()
        if not tutor or not tutor.telegram_id:
            await update.message.reply_text(
                "❌ Репетитор недоступен для чата. "
                "Обратитесь к администратору."
            )
            return ConversationHandler.END
        
        # Формируем сообщение для репетитора
        header = f"💬 Сообщение от родителя {parent.full_name}\n"
        header += f"ID для ответа: `{parent.telegram_id}`\n"
        header += "—" * 30 + "\n"
        
        try:
            # Отправляем заголовок
            await context.bot.send_message(
                chat_id=tutor.telegram_id,
                text=header,
                parse_mode='Markdown'
            )
            
            # Пересылаем само сообщение
            await context.bot.forward_message(
                chat_id=tutor.telegram_id,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
            
            await update.message.reply_text(
                "✅ Сообщение отправлено репетитору!\n"
                "Ответ придет в этом же чате."
            )
            
        except Exception as e:
            await update.message.reply_text(
                "❌ Не удалось отправить сообщение репетитору. "
                "Попробуйте позже."
            )
        
        return CHAT_WITH_TUTOR
    
    finally:
        db.close()


# --- Основной обработчик кнопок родителя ---
async def handle_parent_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основной обработчик кнопок родителя"""
    if not update.callback_query:
        return
    
    callback_data = update.callback_query.data
    parent = check_parent_access(update)
    
    if not parent:
        await update.callback_query.answer("❌ Доступ запрещен")
        return
    
    # Основные действия
    actions = {
        "parent_dashboard": show_parent_dashboard,
        "main_menu": show_main_menu
    }
    
    # Меню конкретного ребенка
    if callback_data.startswith("parent_child_"):
        await show_child_menu(update, context)
        return
    
    # Прогресс ребенка
    if callback_data.startswith("parent_progress_"):
        await show_child_progress(update, context)
        return
    
    # Расписание ребенка
    if callback_data.startswith("parent_schedule_"):
        await show_child_schedule(update, context)
        return
    
    # ДЗ ребенка
    if callback_data.startswith("parent_homework_"):
        await show_child_homework(update, context)
        return
    
    # Оплаты ребенка
    if callback_data.startswith("parent_payments_"):
        await show_child_payments(update, context)
        return
    
    # История уроков
    if callback_data.startswith("parent_lessons_"):
        await show_child_lessons(update, context)
        return
    
    # Достижения ребенка
    if callback_data.startswith("parent_achievements_"):
        await show_child_achievements(update, context)
        return
    
    # График прогресса
    if callback_data.startswith("parent_chart_"):
        await parent_generate_chart(update, context)
        return
    
    # Выполняем основные действия
    if callback_data in actions:
        await actions[callback_data](update, context)
    else:
        await update.callback_query.answer("🔄 Функция в разработке")


# --- Дополнительные функции ---
async def show_child_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает историю уроков ребенка"""
    parent = check_parent_access(update)
    if not parent:
        await update.callback_query.answer("❌ Доступ запрещен")
        return
    
    student_id = int(update.callback_query.data.split("_")[-1])
    
    db = SessionLocal()
    try:
        student = db.query(User).filter(
            User.id == student_id,
            (User.parent_id == parent.id) | (User.second_parent_id == parent.id),
            User.role == UserRole.STUDENT
        ).first()
        
        if not student:
            await update.callback_query.answer("❌ Ребенок не найден")
            return
        
        # Получаем последние 15 уроков
        lessons = db.query(Lesson).filter(
            Lesson.student_id == student.id
        ).order_by(Lesson.date.desc()).limit(15).all()
        
        if not lessons:
            text = f"📚 **История уроков {student.full_name}**\n\nУроков пока нет"
            keyboard = [[InlineKeyboardButton("🔙 К ребенку", callback_data=f"parent_child_{student.id}")]]
        else:
            text = f"📚 **История уроков {student.full_name}**\n\n"
            
            for lesson in lessons:
                date_str = lesson.date.strftime('%d.%m.%Y')
                
                # Эмодзи для статуса
                status_emoji = {
                    AttendanceStatus.ATTENDED: "✅",
                    AttendanceStatus.EXCUSED_ABSENCE: "😷", 
                    AttendanceStatus.UNEXCUSED_ABSENCE: "❌",
                    AttendanceStatus.RESCHEDULED: "📅"
                }.get(lesson.attendance_status, "❓")
                
                # Эмодзи для уровня усвоения
                mastery_emoji = {
                    TopicMastery.NOT_LEARNED: "⚪",
                    TopicMastery.LEARNED: "🟡",
                    TopicMastery.MASTERED: "🟢"
                }.get(lesson.mastery_level, "⚪")
                
                text += f"{date_str} {status_emoji}{mastery_emoji} **{lesson.topic}**\n"
                if lesson.skills_developed:
                    text += f"   💪 {lesson.skills_developed}\n"
                text += "\n"
            
            keyboard = [[InlineKeyboardButton("🔙 К ребенку", callback_data=f"parent_child_{student.id}")]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        await update.callback_query.answer()
    
    finally:
        db.close()


async def parent_generate_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерирует график прогресса для родителя"""
    parent = check_parent_access(update)
    if not parent:
        await update.callback_query.answer("❌ Доступ запрещен")
        return
    
    student_id = int(update.callback_query.data.split("_")[-1])
    
    db = SessionLocal()
    try:
        student = db.query(User).filter(
            User.id == student_id,
            (User.parent_id == parent.id) | (User.second_parent_id == parent.id),
            User.role == UserRole.STUDENT
        ).first()
        
        if not student:
            await update.callback_query.answer("❌ Ребенок не найден")
            return
        
        await safe_edit_or_reply(update, "Генерируем график прогресса...")
        
        from ..chart_generator import generate_progress_chart
        chart_path = generate_progress_chart(student_id)
        
        if chart_path and os.path.exists(chart_path):
            try:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Назад к ребенку", callback_data=f"parent_child_{student_id}")]
                ])
                
                with open(chart_path, 'rb') as chart_file:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=chart_file,
                        caption=f"График прогресса {student.full_name}\n\nТекущие баллы: {student.points}",
                        reply_markup=keyboard
                    )
                
                await update.callback_query.message.delete()
                os.remove(chart_path)
            except Exception as e:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Назад к ребенку", callback_data=f"parent_child_{student_id}")]
                ])
                await safe_edit_or_reply(update, "Ошибка при отправке графика.", keyboard)
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад к ребенку", callback_data=f"parent_child_{student_id}")]
            ])
            await safe_edit_or_reply(update, "Недостаточно данных для построения графика.", keyboard)
    
    finally:
        db.close()