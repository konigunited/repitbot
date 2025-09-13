# -*- coding: utf-8 -*-
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import Forbidden

from ..database import (
    SessionLocal, User, UserRole, get_user_by_telegram_id, get_all_students
)
from ..calendar_util import create_calendar
from .common import show_main_menu

# --- Состояния для ConversationHandler ---
CHAT_WITH_TUTOR = range(1)

async def chat_with_tutor_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает диалог с репетитором"""
    query = update.callback_query
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if user.role == UserRole.STUDENT:
        message = (
            "💬 *Связь с репетитором*\n\n"
            "Напишите ваше сообщение, и я передам его репетитору.\n"
            "Можно отправлять текст, фото или файлы.\n\n"
            "Для отмены введите /cancel"
        )
    elif user.role == UserRole.PARENT:
        message = (
            "💬 *Связь с репетитором*\n\n"
            "Напишите ваше сообщение, и я передам его репетитору.\n"
            "Можно отправлять текст, фото или файлы.\n\n"
            "Для отмены введите /cancel"
        )
    else:
        if query:
            await query.answer()
            await query.edit_message_text("У вас нет доступа к этой функции.")
        else:
            await update.message.reply_text("У вас нет доступа к этой функции.")
        return ConversationHandler.END
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown')
        await query.answer()
    else:
        await update.message.reply_text(message, parse_mode='Markdown')
    
    return CHAT_WITH_TUTOR

async def forward_message_to_tutor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылает сообщение от ученика/родителя к репетитору или обрабатывает быстрый ответ репетитора"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == update.effective_user.id).first()

        # Если это репетитор с данными быстрого ответа, отправляем быстрый ответ
        if (user and user.role == UserRole.TUTOR and
            context.user_data.get('quick_reply_recipient')):
            return await send_tutor_quick_reply(update, context)

        # Находим репетитора (предполагаем, что он один)
        tutor = db.query(User).filter(User.role == UserRole.TUTOR).first()

        if not tutor or not tutor.telegram_id:
            await update.message.reply_text(
                "❌ Не удалось связаться с репетитором. Попробуйте позже."
            )
            return ConversationHandler.END

        if not user:
            await update.message.reply_text(
                "❌ Пользователь не найден. Используйте /start для регистрации."
            )
            return ConversationHandler.END

        # Сохраняем данные пользователя для использования после закрытия сессии
        user_data = {
            'full_name': user.full_name,
            'telegram_id': user.telegram_id,
            'role': user.role
        }
        tutor_telegram_id = tutor.telegram_id

    finally:
        db.close()

    # Формируем заголовок сообщения
    role_emoji = "👨‍🎓" if user_data['role'] == UserRole.STUDENT else "👨‍👩‍👧‍👦"
    role_text = "Ученик" if user_data['role'] == UserRole.STUDENT else "Родитель"
    header = f"{role_emoji} *{role_text}:* {user_data['full_name']}\nID для ответа: `{user_data['telegram_id']}`\n\n"
    
    try:
        # Отправляем разные типы сообщений
        if update.message.text:
            await context.bot.send_message(
                chat_id=tutor_telegram_id,
                text=header + update.message.text,
                parse_mode='Markdown',
                reply_to_message_id=update.message.message_id if update.message.reply_to_message else None
            )
        elif update.message.photo:
            photo = update.message.photo[-1]  # Берем фото лучшего качества
            caption = header + (update.message.caption or "")
            await context.bot.send_photo(
                chat_id=tutor_telegram_id,
                photo=photo.file_id,
                caption=caption,
                parse_mode='Markdown'
            )
        elif update.message.document:
            caption = header + (update.message.caption or "")
            await context.bot.send_document(
                chat_id=tutor_telegram_id,
                document=update.message.document.file_id,
                caption=caption,
                parse_mode='Markdown'
            )
        elif update.message.voice:
            caption = header + "🎤 Голосовое сообщение"
            await context.bot.send_voice(
                chat_id=tutor_telegram_id,
                voice=update.message.voice.file_id,
                caption=caption,
                parse_mode='Markdown'
            )

        # Добавляем кнопку для быстрого ответа репетитора
        reply_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("💬 Ответить", callback_data=f"tutor_reply_to_{user_data['telegram_id']}")
        ]])

        # Отправляем уведомление репетитору с кнопкой ответа
        try:
            await context.bot.send_message(
                chat_id=tutor_telegram_id,
                text="📬 *Новое сообщение получено!*\n\nДля ответа нажмите кнопку ниже или просто ответьте на сообщение выше.",
                parse_mode='Markdown',
                reply_markup=reply_keyboard
            )
        except:
            pass  # Если не удалось отправить уведомление, игнорируем
        
        await update.message.reply_text("✅ Сообщение отправлено репетитору!")
        
    except Forbidden:
        await update.message.reply_text(
            "❌ Репетитор заблокировал бота. Свяжитесь с ним напрямую."
        )
    except Exception as e:
        await update.message.reply_text(
            "❌ Не удалось отправить сообщение. Попробуйте позже."
        )
    
    # Возвращаемся в главное меню
    await show_main_menu(update, context)
    return ConversationHandler.END

async def tutor_quick_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Быстрый ответ репетитора на сообщение пользователя."""
    query = update.callback_query
    await query.answer()
    
    # Проверяем, что это действительно репетитор
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user or user.role != UserRole.TUTOR:
        await query.edit_message_text("У вас нет доступа к этой функции.")
        return
    
    # Находим получателя
    db = SessionLocal()
    recipient = db.query(User).filter(User.telegram_id == user_id).first()
    db.close()
    
    if not recipient:
        await query.edit_message_text("❌ Получатель не найден.")
        return
    
    # Сохраняем информацию о получателе в context
    context.user_data['quick_reply_recipient'] = {
        'user_id': user_id,
        'name': recipient.full_name,
        'role': recipient.role.value
    }
    
    role_emoji = "👨‍🎓" if recipient.role == UserRole.STUDENT else "👨‍👩‍👧‍👦"
    role_text = "ученику" if recipient.role == UserRole.STUDENT else "родителю"
    
    await query.edit_message_text(
        f"💬 *Быстрый ответ {role_text}*\n\n"
        f"{role_emoji} Получатель: {recipient.full_name}\n\n"
        f"Напишите ваше сообщение. Можно отправлять текст, фото или файлы.\n\n"
        f"Для отмены введите /cancel",
        parse_mode='Markdown'
    )
    return CHAT_WITH_TUTOR  # Возвращаем состояние для ожидания ввода сообщения

async def tutor_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str):
    """Обработчик кнопки быстрого ответа репетитора."""
    return await tutor_quick_reply_start(update, context, int(user_id))

async def send_tutor_quick_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет быстрый ответ репетитора пользователю."""
    recipient_info = context.user_data.get('quick_reply_recipient')

    if not recipient_info:
        await update.message.reply_text("❌ Информация о получателе потеряна. Попробуйте снова.")
        return ConversationHandler.END

    # Получаем текст/контент ответа
    if update.message.text:
        reply_text = update.message.text
        message_type = 'text'
    elif update.message.photo:
        reply_text = update.message.caption or ""
        message_type = 'photo'
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        reply_text = update.message.caption or ""
        message_type = 'document'
        file_id = update.message.document.file_id
    else:
        await update.message.reply_text("❌ Поддерживаются только текст, фото или документы.")
        return CHAT_WITH_TUTOR

    user_id = recipient_info['user_id']
    sender_name = get_user_by_telegram_id(update.effective_user.id)
    sender_name = sender_name.full_name if sender_name else "Репетитор"

    try:
        # Отправляем ответ пользователю
        header = f"📩 Ответ от репетитора {sender_name}:\n\n"

        if message_type == 'text':
            await context.bot.send_message(
                chat_id=user_id,
                text=header + reply_text
            )
        elif message_type == 'photo':
            await context.bot.send_photo(
                chat_id=user_id,
                photo=file_id,
                caption=header + reply_text
            )
        elif message_type == 'document':
            await context.bot.send_document(
                chat_id=user_id,
                document=file_id,
                caption=header + reply_text
            )

        role_text = "ученику" if recipient_info['role'] == 'student' else "родителю"
        await update.message.reply_text(f"✅ Ответ {role_text} {recipient_info['name']} отправлен!")

        # Очищаем данные
        context.user_data.pop('quick_reply_recipient', None)
        return ConversationHandler.END

    except Forbidden:
        await update.message.reply_text("❌ Пользователь заблокировал бота. Ответ не доставлен.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при отправке ответа: {e}")

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

    # Получаем текст ответа репетитора
    if update.message.text:
        tutor_reply_text = update.message.text
    elif update.message.caption:
        tutor_reply_text = update.message.caption
    else:
        await update.message.reply_text("❌ Поддерживаются только текстовые ответы или файлы с подписями.")
        return

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
    original_text = original_message.text or original_message.caption
    if original_text and "ID для ответа:" in original_text:
        import re
        try:
            # Ищем ID в тексте разными способами
            user_to_reply_id = None
            text = original_text
            
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

    # --- Вариант 3: Ответ на сообщение с заголовком (содержит имя пользователя) ---
    if not original_text:
        return
    
    # Ищем имя отправителя в заголовке
    lines = original_text.split('\n')
    if len(lines) < 1:
        print(f"DEBUG: No lines in original message")
        return
    
    header = lines[0]
    print(f"DEBUG: Processing tutor reply. Header: '{header}'")
    
    # Извлекаем имя из заголовка (формат: "👨‍🎓 *Ученик:* Имя Фамилия")
    try:
        if '*Ученик:*' in header:
            full_name = header.split('*Ученик:*')[1].strip()
            role_filter = UserRole.STUDENT
        elif '*Родитель:*' in header:
            full_name = header.split('*Родитель:*')[1].strip()
            role_filter = UserRole.PARENT
        else:
            return
    except:
        return
    
    # Находим пользователя
    db = SessionLocal()
    recipient = db.query(User).filter(
        User.full_name == full_name,
        User.role == role_filter,
        User.telegram_id.isnot(None)
    ).first()
    db.close()
    
    if not recipient:
        await update.message.reply_text(
            f"❌ Не удалось найти получателя с именем '{full_name}' и ролью {role_filter.value}. Возможно, он не активировал бота."
        )
        print(f"DEBUG: Could not find recipient: name='{full_name}', role={role_filter.value}")
        return
    
    # Отправляем ответ
    reply_header = f"💬 *Ответ от репетитора:*\n\n"
    
    try:
        if update.message.text:
            await context.bot.send_message(
                chat_id=recipient.telegram_id,
                text=reply_header + update.message.text,
                parse_mode='Markdown'
            )
        elif update.message.photo:
            photo = update.message.photo[-1]
            caption = reply_header + (update.message.caption or "")
            await context.bot.send_photo(
                chat_id=recipient.telegram_id,
                photo=photo.file_id,
                caption=caption,
                parse_mode='Markdown'
            )
        elif update.message.document:
            caption = reply_header + (update.message.caption or "")
            await context.bot.send_document(
                chat_id=recipient.telegram_id,
                document=update.message.document.file_id,
                caption=caption,
                parse_mode='Markdown'
            )
        elif update.message.voice:
            caption = reply_header + "🎤 Голосовое сообщение"
            await context.bot.send_voice(
                chat_id=recipient.telegram_id,
                voice=update.message.voice.file_id,
                caption=caption,
                parse_mode='Markdown'
            )
        
        await update.message.reply_text(f"✅ Ответ отправлен пользователю {recipient.full_name}")
        
    except Forbidden:
        await update.message.reply_text(
            f"❌ Пользователь {recipient.full_name} заблокировал бота."
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Не удалось отправить ответ пользователю {recipient.full_name}."
        )

async def handle_calendar_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор даты в календаре"""
    query = update.callback_query
    await query.answer()
    
    # Импортируем календарь
    from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
    
    result, key, step = DetailedTelegramCalendar().process(query.data)
    
    if not result and key:
        # Еще не выбрана окончательная дата, обновляем календарь
        await query.edit_message_text(
            f"Выберите {LSTEP[step]}",
            reply_markup=key
        )
    elif result:
        # Дата выбрана
        selected_date = result.strftime('%d.%m.%Y')
        
        # Сохраняем выбранную дату в context
        context.user_data['selected_date'] = result
        
        await query.edit_message_text(
            f"✅ Выбрана дата: {selected_date}\n\nТеперь введите время в формате ЧЧ:ММ (например: 15:30)"
        )

async def student_settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик настроек ученика."""
    query = update.callback_query
    await query.edit_message_text(
        "⚙️ **Настройки ученика**\n\n"
        "🔧 Функция находится в разработке.\n"
        "Скоро здесь появятся настройки уведомлений, часового пояса и другие параметры.",
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основной обработчик всех кнопок - используем рабочий код из handlers.py"""
    from ..logger import log_user_action
    
    query = update.callback_query
    await query.answer()
    data = query.data
    
    print(f"BUTTON_HANDLER: Received callback '{data}' from user {update.effective_user.id}")
    
    # Дополнительная отладка для schedule кнопок
    if "schedule" in data:
        print(f"DEBUG: Schedule button detected: {data}")
    
    # Логируем все нажатия кнопок
    log_user_action(update.effective_user.id, f"BUTTON_CLICK: {data}")
    
    # Проверяем роль пользователя
    user = get_user_by_telegram_id(update.effective_user.id)
    
    # Импортируем функции из микросервисов напрямую
    from .common import show_main_menu
    from .student import (show_my_progress, show_schedule, show_homework_menu, show_lesson_history,
                         show_payment_and_attendance, show_materials_library, show_student_achievements,
                         student_view_homework, student_view_lesson_details, student_library_by_grade)
    from .tutor import (show_student_list, show_student_profile, show_analytics_chart,
                       tutor_delete_student_start, tutor_delete_student_confirm, tutor_add_parent_start,
                       show_tutor_lessons, show_lesson_details, tutor_mark_lesson_attended,
                       tutor_set_lesson_attendance, tutor_reschedule_lesson_start, tutor_check_homework,
                       tutor_manage_library, tutor_add_material_start, tutor_delete_material_start,
                       tutor_delete_material_confirm, show_material_details, show_tutor_dashboard,
                       show_tutor_stats, tutor_edit_name_start, tutor_set_homework_status, 
                       tutor_add_payment_start, tutor_add_lesson_start,
                       tutor_confirm_lesson_cancellation, tutor_library_by_grade,
                       tutor_remove_second_parent, tutor_replace_second_parent,
                       tutor_edit_lesson_start, tutor_edit_attendance_status, tutor_edit_mastery_status,
                       tutor_edit_lesson_conduct_status, tutor_set_lesson_conduct,
                       tutor_delete_lesson_start, tutor_confirm_delete_lesson,
                       tutor_schedule_setup_start, tutor_schedule_toggle_day, tutor_schedule_back, tutor_schedule_add_note,
                       tutor_parent_contact_start, tutor_message_student_start_wrapper, tutor_message_parent_start_wrapper,
                       tutor_message_input, tutor_message_send_wrapper, tutor_message_cancel)
    from .parent import (show_parent_dashboard, show_child_menu, show_child_progress,
                        show_child_schedule, show_child_payments, parent_generate_chart,
                        show_child_homework, show_child_lessons, show_child_achievements)
    
    # Карта для сопоставления префиксов callback_data с функциями
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
        # tutor_add_parent_, tutor_add_payment_, tutor_add_lesson_ обрабатываются ConversationHandlers
        "tutor_lessons_list_": (show_tutor_lessons, "student_id"),
        "tutor_lesson_details_": (show_lesson_details, "lesson_id"),
        "tutor_mark_attended_": (tutor_mark_lesson_attended, "lesson_id"),
        "tutor_set_attendance_": (tutor_set_lesson_attendance, "lesson_id_status"),
        "tutor_reschedule_lesson_": (tutor_reschedule_lesson_start, "lesson_id"),
        "tutor_edit_lesson_": (tutor_edit_lesson_start, "lesson_id"),
        "tutor_edit_attendance_": (tutor_edit_attendance_status, "lesson_id"),
        "tutor_edit_lesson_conduct_": (tutor_edit_lesson_conduct_status, "lesson_id"),
        "tutor_set_lesson_conduct_": (tutor_set_lesson_conduct, "lesson_id_status"),
        "tutor_edit_mastery_": (tutor_edit_mastery_status, "lesson_id"),
        "tutor_delete_lesson_": (tutor_delete_lesson_start, "lesson_id"),
        "tutor_confirm_delete_lesson_": (tutor_confirm_delete_lesson, "lesson_id"),
        "tutor_schedule_setup_": (tutor_schedule_setup_start, "student_id"),
        "schedule_toggle_": (tutor_schedule_toggle_day, "day"),
        "schedule_day_": (tutor_schedule_toggle_day, "day"),
        "schedule_note_": (tutor_schedule_add_note, "day"),
        "schedule_back": (tutor_schedule_back, None),
        "tutor_parent_contact_": (tutor_parent_contact_start, "student_id"),
        "tutor_reply_to_": (tutor_reply_handler, "user_id"),
        "tutor_check_hw_": (tutor_check_homework, "lesson_id"),
        "tutor_manage_library": (tutor_manage_library, None),
        "tutor_add_material": (tutor_add_material_start, None),
        "tutor_delete_material_start": (tutor_delete_material_start, None),
        "tutor_delete_material_": (tutor_delete_material_confirm, "material_id"),
        "view_material_": (show_material_details, "material_id"),
        "parent_dashboard": (show_parent_dashboard, None),
        "student_view_hw_": (student_view_homework, None),
        "student_view_lesson_": (student_view_lesson_details, None),
        "materials_library": (show_materials_library, None),
        "student_achievements": (show_student_achievements, None),
        "tutor_dashboard": (show_tutor_dashboard, None),
        "tutor_stats": (show_tutor_stats, None),
        # tutor_edit_name_ обрабатывается ConversationHandler
        "tutor_set_hw_status_": (tutor_set_homework_status, "hw_id_status"),
        "tutor_confirm_cancel_": (tutor_confirm_lesson_cancellation, "lesson_id_status"),
        "tutor_view_material_": (show_material_details, "material_id"),
        "student_view_material_": (show_material_details, "material_id"),
        "tutor_library_grade_": (tutor_library_by_grade, "grade"),
        "student_library_grade_": (student_library_by_grade, "grade"),
        "student_settings": (student_settings_handler, None),
        "select_child": (show_parent_dashboard, None),
        "parent_child_": (show_child_menu, "child_id"),
        "parent_progress_": (show_child_progress, "child_id"),
        "parent_schedule_": (show_child_schedule, "child_id"), 
        "parent_payments_": (show_child_payments, "child_id"),
        "parent_chat_with_tutor_": (chat_with_tutor_start, None),
        "parent_homework_": (show_child_homework, None),
        "parent_lessons_": (show_child_lessons, None),
        "parent_achievements_": (show_child_achievements, None),
        "parent_chart_": (parent_generate_chart, None),
        "tutor_remove_second_parent_": (tutor_remove_second_parent, "student_id"),
        "tutor_replace_second_parent_": (tutor_replace_second_parent, "student_id"),
        "noop": (lambda update, context: update.callback_query.answer(), None),
    }
    
    # Попробуем найти подходящий обработчик
    handler_found = False
    for prefix, (handler, param_name) in action_map.items():
        if data == prefix or data.startswith(prefix):
            handler_found = True
            print(f"DEBUG: Found handler for '{data}': {handler.__name__ if hasattr(handler, '__name__') else handler}")
            try:
                if param_name is None:
                    # Вызываем без параметров
                    await handler(update, context)
                elif param_name == "student_id":
                    student_id = int(data.split("_")[-1])
                    await handler(update, context, student_id)
                elif param_name == "child_id":
                    child_id = int(data.split("_")[-1])
                    await handler(update, context, child_id)
                elif param_name == "lesson_id":
                    lesson_id = int(data.split("_")[-1])
                    await handler(update, context, lesson_id)
                elif param_name == "material_id":
                    material_id = int(data.split("_")[-1])
                    await handler(update, context, material_id)
                elif param_name == "lesson_id_status":
                    # Для установки посещаемости урока или статуса проведения
                    if data.startswith("tutor_set_attendance_"):
                        lesson_id_status = "_".join(data.split("_")[3:])  # Убираем префикс "tutor_set_attendance_"
                    elif data.startswith("tutor_set_lesson_conduct_"):
                        lesson_id_status = "_".join(data.split("_")[4:])  # Убираем префикс "tutor_set_lesson_conduct_"
                    else:
                        lesson_id_status = "_".join(data.split("_")[3:])  # Дефолт для других случаев
                    await handler(update, context, lesson_id_status)
                elif param_name == "hw_id_status":
                    # Для установки статуса домашнего задания
                    hw_id_status = "_".join(data.split("_")[4:])  # Убираем префикс "tutor_set_hw_status_"
                    await handler(update, context, hw_id_status)
                elif param_name == "lesson_id_mastery":
                    # Для установки уровня усвоения урока
                    lesson_id_mastery = "_".join(data.split("_")[3:])  # Убираем префикс "tutor_set_mastery_"
                    await handler(update, context, lesson_id_mastery)
                elif param_name == "grade":
                    # Для выбора класса в библиотеке
                    grade = data.split("_")[-1]  # Последняя часть после последнего "_"
                    await handler(update, context, grade)
                elif param_name == "day":
                    # Для выбора дня в расписании
                    day = data.split("_")[-1]  # Последняя часть после последнего "_"
                    await handler(update, context, day)
                elif param_name == "time":
                    # Для выбора времени в расписании
                    time = data.split("_")[-1]  # Последняя часть после последнего "_"
                    await handler(update, context, time)
                elif param_name == "parent_id_student_id":
                    # Для сообщений родителю (формат: tutor_message_parent_<parent_id>_<student_id>)
                    parts = data.split("_")
                    if len(parts) >= 4:
                        parent_id_student_id = "_".join(parts[3:])  # parent_id_student_id
                        await handler(update, context, parent_id_student_id)
                    else:
                        await handler(update, context, data)
                elif param_name == "user_id":
                    # Для быстрого ответа пользователю
                    user_id = data.split("_")[-1]  # Последняя часть после последнего "_"
                    await handler(update, context, user_id)
                else:
                    await handler(update, context)
                    
            except Exception as e:
                print(f"ERROR: Handler {handler.__name__} failed for data '{data}': {e}")
                await query.edit_message_text(f"❌ Ошибка обработки команды")
            break
    
    if not handler_found:
        print(f"WARNING: No handler found for callback_data '{data}'")
        await query.edit_message_text("🔄 Функция в разработке")