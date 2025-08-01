# -*- coding: utf-8 -*-
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import Forbidden
from .database import (SessionLocal, User, UserRole, Lesson, Homework, Payment, Material,
                      get_user_by_telegram_id, get_all_students, get_user_by_id,
                      get_lesson_by_id, get_homework_by_id,
                      get_lessons_for_student_by_month, get_payments_for_student_by_month,
                      get_all_materials, get_material_by_id, delete_material_by_id,
                      get_dashboard_stats, HomeworkStatus, TopicMastery, get_student_balance)
from .keyboards import (tutor_main_keyboard, student_main_keyboard, parent_main_keyboard,
                       tutor_student_list_keyboard, tutor_student_profile_keyboard,
                       tutor_lesson_list_keyboard, tutor_lesson_details_keyboard,
                       tutor_delete_confirm_keyboard, tutor_edit_lesson_status_keyboard,
                       tutor_check_homework_keyboard, tutor_select_student_for_report_keyboard,
                       tutor_select_month_for_report_keyboard, tutor_library_management_keyboard,
                       tutor_select_material_to_delete_keyboard, student_materials_list_keyboard,
                       parent_child_selection_keyboard, parent_child_menu_keyboard,
                       student_select_homework_keyboard, broadcast_confirm_keyboard)
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

# --- Состояния для ConversationHandler ---
ADD_STUDENT_NAME, ADD_PARENT_CODE = range(2)
ADD_PAYMENT_AMOUNT = range(1)
ADD_LESSON_TOPIC, ADD_LESSON_DATE, ADD_LESSON_SKILLS = range(3)
EDIT_STUDENT_NAME = range(1)
ADD_HW_DESC, ADD_HW_DEADLINE, ADD_HW_LINK = range(3)
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
    access_code = update.message.text.strip()
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
        reply_markup = tutor_main_keyboard()
        message = "Добро пожаловать, Репетитор!"
        # ReplyKeyboardMarkup cannot be edited, so we send a new message
        if query:
            await query.delete_message()
            await context.bot.send_message(chat_id=query.from_user.id, text=message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)
        return

    elif user.role == UserRole.STUDENT:
        reply_markup = student_main_keyboard()
        message = f"Добро пожаловать, {user.full_name}!"
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
    query = update.callback_query
    await query.answer()
    data = query.data

    # Карта для сопоставления префиксов callback_data с функциями и именами их ID-параметров.
    # Формат: { "префикс": (функция, "имя_параметра_id") }
    # Если ID не требуется, имя параметра - None.
    action_map = {
        "main_menu": (show_main_menu, None),
        "my_progress": (show_my_progress, None),
        "schedule": (show_schedule, None),
        "homework": (show_homework_menu, None),
        "tutor_student_list": (show_student_list, None),
        "tutor_view_student_": (show_student_profile, "student_id"),
        "tutor_analytics_": (show_analytics_chart, "student_id"),
        "tutor_delete_student_": (tutor_delete_student_start, "student_id"),
        "tutor_delete_confirm_": (tutor_delete_student_confirm, "student_id"),
        "tutor_lessons_list_": (show_tutor_lessons, "student_id"),
        "tutor_lesson_details_": (show_lesson_details, "lesson_id"),
        "tutor_mark_attended_": (tutor_mark_lesson_attended, "lesson_id"),
        "tutor_check_hw_": (tutor_check_homework, "lesson_id"),
        "tutor_manage_library": (tutor_manage_library, None),
        "tutor_delete_material_start": (tutor_delete_material_start, None),
        "tutor_delete_material_": (tutor_delete_material_confirm, "material_id"),
        "tutor_view_material_": (show_material_details, "material_id"),
        "materials_library": (show_materials_library, None),
        "student_view_material_": (show_material_details, "material_id"),
        "select_child": (parent_select_child, None),
        "view_child_": (parent_view_child_menu, "child_id"),
        "child_progress_": (parent_view_child_progress, "child_id"),
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
    if data.startswith("tutor_set_mastery_"):
        prefix = "tutor_set_mastery_"
        payload = data[len(prefix):]
        try:
            lesson_id_str, mastery_value = payload.split('_', 1)
            lesson_id = int(lesson_id_str)
            await tutor_set_lesson_mastery(update, context, lesson_id, mastery_value)
        except ValueError:
            # Можно добавить логирование для отладки
            await query.answer("Ошибка обработки данных.")
        return

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
    await update.message.reply_text("Введите ФИО нового ученика:")
    return ADD_STUDENT_NAME

async def tutor_get_student_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['student_name'] = update.message.text
    await update.message.reply_text("Введите код доступа родителя (или 'пропустить'):")
    return ADD_PARENT_CODE

async def tutor_get_parent_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parent_code = update.message.text.strip()
    student_name = context.user_data.get('student_name')
    db = SessionLocal()
    parent = None
    if parent_code.lower() != 'пропустить':
        parent = db.query(User).filter(User.access_code == parent_code, User.role == UserRole.PARENT).first()
    
    access_code = generate_access_code()
    new_student = User(full_name=student_name, role=UserRole.STUDENT, access_code=access_code, parent=parent)
    db.add(new_student)
    db.commit()
    
    message = f"✅ Ученик *{student_name}* добавлен. Код: `{access_code}`."
    if parent: message += f"\nПривязан к родителю: *{parent.full_name}*"
    
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

        text = (f"📚 *Тема:* {topic}\n"
                f"🗓️ *Дата:* {date_str}\n"
                f"👍 *Навыки:* {skills}\n"
                f"🎓 *Статус:* {mastery_level}\n")
        if comment:
            text += f"💬 *Комментарий:* {comment}\n"
        text += f"✅ *Посещение:* {'Да' if lesson.is_attended else 'Нет'}"

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

    # Сохраняем выбранный статус
    context.user_data['new_mastery_status'] = TopicMastery(mastery_value)
    
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
    
    lesson_id = context.user_data.get('hw_lesson_id')
    db = SessionLocal()
    new_hw = Homework(
        lesson_id=lesson_id,
        description=context.user_data.get('hw_description'),
        deadline=context.user_data.get('hw_deadline'),
        file_link=link
    )
    db.add(new_hw)
    db.commit()
    db.close()
    await update.message.reply_text("✅ ДЗ добавлено!")
    context.user_data.clear()
    await show_main_menu(update, context)
    return ConversationHandler.END

async def tutor_check_homework(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int):
    db = SessionLocal()
    hw = db.query(Homework).filter(Homework.lesson_id == lesson_id).first()
    db.close()
    if not hw:
        await update.callback_query.answer("Для этого урока нет ДЗ.")
        return
    
    status_ru = HOMEWORK_STATUS_RU.get(hw.status, "Неизвестно")
    description = escape_markdown(hw.description or "", version=2)
    status_md = escape_markdown(status_ru, version=2)

    text = f"ДЗ: {description}\nСтатус: {status_md}"
    keyboard = tutor_check_homework_keyboard(hw)
    await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='MarkdownV2')

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
    query = update.callback_query
    user = get_user_by_telegram_id(query.from_user.id)
    db = SessionLocal()
    
    # Загружаем все домашние задания для студента, у которых статус PENDING
    pending_hw = db.query(Homework).join(Lesson).filter(
        Lesson.student_id == user.id,
        Homework.status == HomeworkStatus.PENDING
    ).all()
    
    db.close()

    if not pending_hw:
        await query.edit_message_text(
            "У вас нет активных домашних заданий.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")]])
        )
        return

    keyboard = student_select_homework_keyboard(pending_hw)
    await query.edit_message_text("Выберите домашнее задание для сдачи:", reply_markup=keyboard)


async def student_submit_homework_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    hw_id = int(query.data.split("_")[-1])
    context.user_data['hw_id_to_submit'] = hw_id
    
    hw = get_homework_by_id(hw_id)
    
    await query.edit_message_text(
        f"Вы выбрали:\n*Тема:* {hw.lesson.topic}\n*Задание:* {hw.description}\n\n"
        "Теперь отправьте файл с выполненным заданием или введите текст.",
        parse_mode='Markdown'
    )
    return SUBMIT_HOMEWORK_FILE

async def student_get_homework_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hw_id = context.user_data.get('hw_id_to_submit')
    submission_text = None
    file_id = None

    if update.message.text:
        submission_text = update.message.text
    elif update.message.document:
        file_id = update.message.document.file_id
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id # Берем самое большое разрешение

    if not submission_text and not file_id:
        await update.message.reply_text("Пожалуйста, отправьте текст или файл.")
        return SUBMIT_HOMEWORK_FILE

    db = SessionLocal()
    hw = db.query(Homework).filter(Homework.id == hw_id).first()
    if hw:
        hw.status = HomeworkStatus.SUBMITTED
        # Сохраняем и текст, и ID файла, если они есть
        hw.description += f"\n\n--- Ответ студента ---\n{submission_text or ''}"
        hw.file_link = file_id # Перезаписываем ссылку на файл ответом студента
        db.commit()
        
        # Уведомление репетитору (опционально)
        tutor_telegram_id = db.query(User).filter(User.role == UserRole.TUTOR).first().telegram_id
        if tutor_telegram_id:
            student_name = hw.lesson.student.full_name
            await context.bot.send_message(
                tutor_telegram_id,
                f"Студент {student_name} сдал домашнее задание по теме '{hw.lesson.topic}'.\n"
                "Вы можете проверить его в профиле ученика."
            )
        
        await update.message.reply_text("✅ Ваше домашнее задание отправлено на проверку!")
    else:
        await update.message.reply_text("❌ Произошла ошибка, ДЗ не найдено.")
        
    db.close()
    context.user_data.clear()
    await show_main_menu(update, context)
    return ConversationHandler.END


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
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Напишите ваше сообщение репетитору. Вы можете отправить текст, фото или документ.\n"
        "Для отмены введите /cancel."
    )
    return CHAT_WITH_TUTOR

async def forward_message_to_tutor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пересылает сообщение от пользователя репетитору с подписью."""
    user = get_user_by_telegram_id(update.effective_user.id)
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

    tutor_reply_text = update.message.text
    original_message = update.message.reply_to_message

    # --- Вариант 1: Ответ на пересланное сообщение ---
    if original_message.forward_from:
        user_to_reply_id = original_message.forward_from.id
        try:
            await context.bot.send_message(
                chat_id=user_to_reply_id,
                text=f"Сообщение от репетитора:\n\n{tutor_reply_text}"
            )
            await update.message.reply_text("✅ Ответ успешно отправлен.")
        except Forbidden:
            await update.message.reply_text("Не удалось отправить ответ: пользователь заблокировал бота.")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при отправке ответа: {e}")
        return

    # --- Вариант 2: Ответ на сообщение с подписью (содержит ID) ---
    if original_message.text and "ID для ответа:" in original_message.text:
        try:
            # Извлекаем ID из текста подписи
            user_to_reply_id = int(original_message.text.split("`")[1])
            await context.bot.send_message(
                chat_id=user_to_reply_id,
                text=f"Сообщение от репетитора:\n\n{tutor_reply_text}"
            )
            await update.message.reply_text("✅ Ответ успешно отправлен.")
        except (ValueError, IndexError):
            await update.message.reply_text("Не удалось извлечь ID пользователя из сообщения. Ответ не отправлен.")
        except Forbidden:
            await update.message.reply_text("Не удалось отправить ответ: пользователь заблокировал бота.")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при отправке ответа: {e}")
        return

# --- Broadcast ---
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает диалог создания рассылки."""
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user or user.role != UserRole.TUTOR:
        await update.message.reply_text("Эта функция доступна только репетитору.")
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
        await update.callback_query.answer("✅ Отмечено! +10 баллов ученику.")
    else:
        await update.callback_query.answer("Урок уже был отмечен.")
    
    await show_lesson_details(update, context, lesson_id)
    db.close()

async def tutor_set_lesson_mastery(update: Update, context: ContextTypes.DEFAULT_TYPE, lesson_id: int, mastery_value: str):
    db = SessionLocal()
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    
    new_mastery = TopicMastery(mastery_value)
    if new_mastery == TopicMastery.MASTERED and lesson.mastery_level != TopicMastery.MASTERED:
        lesson.student.points += 25
        await update.callback_query.answer("✅ Статус обновлен! +25 баллов ученику.")
    else:
        await update.callback_query.answer("✅ Статус обновлен!")

    lesson.mastery_level = new_mastery
    db.commit()
    await show_lesson_details(update, context, lesson_id)
    db.close()

async def tutor_set_homework_status(update: Update, context: ContextTypes.DEFAULT_TYPE, hw_id: int, status_value: str):
    db = SessionLocal()
    hw = db.query(Homework).filter(Homework.id == hw_id).first()
    
    new_status = HomeworkStatus(status_value)
    if new_status == HomeworkStatus.CHECKED and hw.status != HomeworkStatus.CHECKED:
        hw.lesson.student.points += 15
        hw.checked_at = datetime.now()
        await update.callback_query.answer("✅ ДЗ принято! +15 баллов ученику.")
    else:
        await update.callback_query.answer("✅ Статус ДЗ обновлен!")

    hw.status = new_status
    db.commit()
    await show_lesson_details(update, context, hw.lesson_id)
    db.close()

async def show_my_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = get_user_by_telegram_id(query.from_user.id)
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
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    calendar, step = create_calendar()
    await query.edit_message_text("🗓️ *Календарь уроков*\n\nВыберите дату:", reply_markup=calendar, parse_mode='Markdown')

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
    query = update.callback_query
    materials = get_all_materials()
    if not materials:
        await query.edit_message_text("🗂️ В библиотеке пока пусто.")
        return
    keyboard = student_materials_list_keyboard(materials)
    await query.edit_message_text("🗂️ *Библиотека материалов*\n\nВыберите материал:", reply_markup=keyboard, parse_mode='Markdown')

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