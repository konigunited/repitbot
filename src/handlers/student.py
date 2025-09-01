# -*- coding: utf-8 -*-
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy.orm import joinedload

from ..database import (
    SessionLocal, User, UserRole, Lesson, Homework, Payment, Achievement,
    get_user_by_telegram_id, get_lesson_by_id, get_homework_by_id,
    get_student_balance, get_student_achievements, HomeworkStatus, TopicMastery, AttendanceStatus
)
from ..keyboards import (
    student_select_homework_keyboard, student_lesson_list_keyboard,
    student_lesson_details_keyboard, student_materials_list_keyboard
)
from ..chart_generator import generate_progress_chart
from .common import check_user_role

# --- Состояния для ConversationHandler ---
SUBMIT_HOMEWORK_FILE = range(1)

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

    message = f"📝 *Ваши домашние задания*\n\nВсего заданий: {len(all_hw)}"
    
    if query:
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        await query.answer()
    else:
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def student_submit_homework_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    hw_id = int(query.data.split("_")[-1])
    context.user_data['hw_id'] = hw_id
    
    hw = get_homework_by_id(hw_id)
    if not hw:
        await query.edit_message_text("Домашнее задание не найдено.")
        return ConversationHandler.END
    
    if hw.status != HomeworkStatus.PENDING:
        await query.edit_message_text("Это домашнее задание уже сдано.")
        return ConversationHandler.END
    
    message = (
        f"📝 *Сдача домашнего задания*\n\n"
        f"*Тема урока:* {hw.lesson.topic}\n"
        f"*Задание:* {hw.description}\n\n"
        "Пришлите ваш ответ (текст, фото или файл):"
    )
    
    await query.edit_message_text(message, parse_mode='Markdown')
    return SUBMIT_HOMEWORK_FILE

async def student_get_homework_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hw_id = context.user_data.get('hw_id')
    if not hw_id:
        await update.message.reply_text("Ошибка: ID домашнего задания не найден.")
        return ConversationHandler.END
    
    db = SessionLocal()
    hw = db.query(Homework).filter(Homework.id == hw_id).first()
    
    if not hw:
        await update.message.reply_text("Домашнее задание не найдено.")
        db.close()
        return ConversationHandler.END
    
    # Обрабатываем разные типы сообщений
    if update.message.text:
        hw.submission_text = update.message.text
    elif update.message.photo:
        # Берем фото с лучшим разрешением
        photo = update.message.photo[-1]
        photo_file_ids = json.loads(hw.submission_photo_file_ids) if hw.submission_photo_file_ids else []
        photo_file_ids.append(photo.file_id)
        hw.submission_photo_file_ids = json.dumps(photo_file_ids)
    elif update.message.document:
        # Сохраняем file_id документа в виде ссылки
        hw.file_link = update.message.document.file_id
    
    # Меняем статус на "сдано"
    hw.status = HomeworkStatus.SUBMITTED
    db.commit()
    db.close()
    
    await update.message.reply_text(
        "✅ Домашнее задание успешно сдано!\n"
        "Ожидайте проверки от репетитора."
    )
    
    # Возвращаемся в главное меню
    from .common import show_main_menu
    await show_main_menu(update, context)
    
    return ConversationHandler.END

async def student_view_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    hw_id = int(query.data.split("_")[-1])
    hw = get_homework_by_id(hw_id)
    
    if not hw:
        await query.edit_message_text("Домашнее задание не найдено.")
        return
    
    status_text = HOMEWORK_STATUS_RU.get(hw.status, "Неизвестно")
    deadline_text = hw.deadline.strftime('%d.%m.%Y в %H:%M') if hw.deadline else "Не указан"
    
    message = (
        f"📝 *Домашнее задание*\n\n"
        f"*Тема урока:* {hw.lesson.topic}\n"
        f"*Задание:* {hw.description}\n"
        f"*Дедлайн:* {deadline_text}\n"
        f"*Статус:* {status_text}\n"
    )
    
    # Добавляем информацию о сданной работе, если есть
    if hw.submission_text:
        message += f"\n*Ваш ответ:* {hw.submission_text}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ К домашним заданиям", callback_data="homework")]
    ])
    
    # Проверяем есть ли фото домашнего задания
    if hw.photo_file_ids:
        import json
        try:
            photo_ids = json.loads(hw.photo_file_ids)
            if photo_ids:
                # Отправляем фото с подписью
                await query.edit_message_text("📝 *Домашнее задание с фотографиями:*", parse_mode='Markdown')
                
                # Отправляем все фото
                for i, photo_id in enumerate(photo_ids):
                    caption = message if i == 0 else ""  # Подпись только к первому фото
                    reply_markup = keyboard if i == len(photo_ids) - 1 else None  # Кнопки только к последнему фото
                    
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=photo_id,
                        caption=caption,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
            else:
                # Если массив пустой, показываем только текст
                await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        except (json.JSONDecodeError, Exception) as e:
            # Если ошибка с JSON, показываем только текст
            print(f"Error parsing homework photo_file_ids: {e}")
            await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    else:
        # Если нет фото, показываем только текст
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    
    # Отправляем фото отдельными сообщениями, если есть
    if hw.submission_photo_file_ids:
        photo_ids = json.loads(hw.submission_photo_file_ids)
        for photo_id in photo_ids:
            try:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_id)
            except Exception:
                pass  # Игнорируем ошибки отправки фото

async def show_my_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем роль пользователя для text-сообщений (reply keyboard) 
    if update.message and not check_user_role(update, UserRole.STUDENT):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
    
    query = update.callback_query
    user = get_user_by_telegram_id(update.effective_user.id)
    
    # Отправляем сообщение о генерации графика
    if query:
        await query.edit_message_text("📊 Генерируем график прогресса...")
        await query.answer()
    else:
        progress_msg = await update.message.reply_text("📊 Генерируем график прогресса...")
    
    # Генерируем график
    chart_path = generate_progress_chart(user.id)
    
    if chart_path:
        try:
            with open(chart_path, 'rb') as chart_file:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")]
                ])
                
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=chart_file,
                    caption=f"📊 *Ваш прогресс*\n\nТекущие баллы: *{user.points}*",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                
                # Удаляем сообщение о генерации
                if query:
                    await query.message.delete()
                else:
                    await progress_msg.delete()
        except Exception as e:
            error_message = "❌ Не удалось сгенерировать график прогресса."
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")]
            ])
            
            if query:
                await query.edit_message_text(error_message, reply_markup=keyboard)
            else:
                await progress_msg.edit_text(error_message, reply_markup=keyboard)
    else:
        error_message = "❌ Недостаточно данных для построения графика."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")]
        ])
        
        if query:
            await query.edit_message_text(error_message, reply_markup=keyboard)
        else:
            await progress_msg.edit_text(error_message, reply_markup=keyboard)

async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем роль пользователя для text-сообщений (reply keyboard)
    if update.message and not check_user_role(update, UserRole.STUDENT):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
    
    query = update.callback_query
    user = get_user_by_telegram_id(update.effective_user.id)
    
    db = SessionLocal()
    
    # Получаем будущие уроки
    now = datetime.now()
    future_lessons = db.query(Lesson).filter(
        Lesson.student_id == user.id,
        Lesson.date >= now
    ).order_by(Lesson.date).limit(10).all()
    
    db.close()
    
    if not future_lessons:
        message = "📅 У вас нет запланированных уроков."
    else:
        message = "📅 *Ваше расписание*\n\n"
        for i, lesson in enumerate(future_lessons, 1):
            date_str = lesson.date.strftime('%d.%m.%Y в %H:%M')
            message += f"{i}. *{date_str}*\n   {lesson.topic or 'Тема не указана'}\n\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")]
    ])
    
    if query:
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        await query.answer()
    else:
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def show_materials_library(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем роль пользователя для text-сообщений (reply keyboard)
    if update.message and not check_user_role(update, UserRole.STUDENT):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
        
    query = update.callback_query
    
    from ..keyboards import library_grade_selection_keyboard
    keyboard = library_grade_selection_keyboard(is_tutor=False)
    message = "🗂️ *Библиотека материалов*\n\nВыберите класс для просмотра материалов:"
    
    if query:
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        await query.answer()
    else:
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def student_library_by_grade(update: Update, context: ContextTypes.DEFAULT_TYPE, grade=None):
    """Показывает материалы для определённого класса или все материалы для студента."""
    if not check_user_role(update, UserRole.STUDENT):
        await update.callback_query.answer("У вас нет доступа к этой функции.")
        return
        
    if grade == "all":
        from ..database import get_all_materials
        materials = get_all_materials()
        message = "🗂️ *Библиотека материалов - Все классы*\n\nВсе материалы:"
    else:
        from ..database import get_materials_by_grade
        materials = get_materials_by_grade(int(grade))
        message = f"🗂️ *Библиотека материалов - {grade} класс*\n\nМатериалы для {grade} класса:"
    
    if not materials:
        if grade == "all":
            message = "🗂️ Библиотека материалов пуста."
        else:
            message = f"🗂️ *Библиотека материалов - {grade} класс*\n\nДля {grade} класса материалов пока нет."
    
    keyboard = student_materials_list_keyboard(materials, grade)
    await update.callback_query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def show_lesson_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем роль пользователя для text-сообщений (reply keyboard)
    if update.message and not check_user_role(update, UserRole.STUDENT):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
    
    query = update.callback_query
    user = get_user_by_telegram_id(update.effective_user.id)
    
    db = SessionLocal()
    lessons = db.query(Lesson).filter(
        Lesson.student_id == user.id
    ).order_by(Lesson.date.desc()).limit(20).all()
    db.close()
    
    if not lessons:
        message = "📚 У вас еще не было уроков."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")]
        ])
    else:
        message = "📚 *История ваших уроков*\n\nПоследние 20 уроков:"
        keyboard = student_lesson_list_keyboard(lessons)
    
    if query:
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        await query.answer()
    else:
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def student_view_lesson_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    lesson_id = int(query.data.split("_")[-1])
    lesson = get_lesson_by_id(lesson_id)
    
    if not lesson:
        await query.edit_message_text("Урок не найден.")
        return
    
    date_str = lesson.date.strftime('%d.%m.%Y в %H:%M')
    attendance_text = ATTENDANCE_STATUS_RU.get(lesson.attendance_status, "Неизвестно")
    mastery_text = TOPIC_MASTERY_RU.get(lesson.mastery_level, "Не указано")
    
    message = (
        f"📚 *Детали урока*\n\n"
        f"*Дата:* {date_str}\n"
        f"*Тема:* {lesson.topic}\n"
        f"*Статус посещения:* {attendance_text}\n"
        f"*Уровень усвоения:* {mastery_text}\n"
    )
    
    if lesson.skills_developed:
        message += f"*Развиваемые навыки:* {lesson.skills_developed}\n"
    
    if lesson.mastery_comment:
        message += f"*Комментарий:* {lesson.mastery_comment}\n"
    
    keyboard = student_lesson_details_keyboard(lesson)
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def show_student_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем роль пользователя для text-сообщений (reply keyboard)
    if update.message and not check_user_role(update, UserRole.STUDENT):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
    
    query = update.callback_query
    user = get_user_by_telegram_id(update.effective_user.id)
    
    achievements = get_student_achievements(user.id)
    
    if not achievements:
        message = "🏆 *Ваши достижения*\n\nУ вас пока нет достижений.\nПродолжайте учиться, и они обязательно появятся!"
    else:
        message = f"🏆 *Ваши достижения*\n\nВсего достижений: {len(achievements)}\n\n"
        for achievement in achievements:
            date_str = achievement.earned_at.strftime('%d.%m.%Y')
            message += f"{achievement.icon} *{achievement.title}*\n"
            if achievement.description:
                message += f"   {achievement.description}\n"
            message += f"   📅 Получено: {date_str}\n\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")]
    ])
    
    if query:
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        await query.answer()
    else:
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def show_payment_and_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем роль пользователя для text-сообщений (reply keyboard)
    if update.message and not check_user_role(update, UserRole.STUDENT):
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
    
    query = update.callback_query
    user = get_user_by_telegram_id(update.effective_user.id)
    
    balance = get_student_balance(user.id)
    
    db = SessionLocal()
    
    # Статистика посещаемости за последние 30 дней
    from datetime import timedelta
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    recent_lessons = db.query(Lesson).filter(
        Lesson.student_id == user.id,
        Lesson.date >= thirty_days_ago
    ).all()
    
    attended_count = len([l for l in recent_lessons if l.attendance_status == AttendanceStatus.ATTENDED])
    total_count = len(recent_lessons)
    
    # Последние 5 платежей
    recent_payments = db.query(Payment).filter(
        Payment.student_id == user.id
    ).order_by(Payment.payment_date.desc()).limit(5).all()
    
    db.close()
    
    message = f"💰 *Баланс и посещаемость*\n\n"
    message += f"💳 *Баланс уроков:* {balance}\n\n"
    
    if total_count > 0:
        attendance_percentage = round((attended_count / total_count) * 100)
        message += f"📊 *Посещаемость за 30 дней:*\n"
        message += f"   Проведено: {attended_count} из {total_count}\n"
        message += f"   Процент: {attendance_percentage}%\n\n"
    
    if recent_payments:
        message += "📋 *Последние оплаты:*\n"
        for payment in recent_payments:
            date_str = payment.payment_date.strftime('%d.%m.%Y')
            message += f"   • {date_str}: {payment.lessons_paid} уроков\n"
    else:
        message += "📋 История оплат пуста.\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")]
    ])
    
    if query:
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        await query.answer()
    else:
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')