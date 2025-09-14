# -*- coding: utf-8 -*-
import logging
import os
from dotenv import load_dotenv
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, 
                          CallbackQueryHandler, ConversationHandler, ContextTypes)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram_bot_calendar import DetailedTelegramCalendar
import asyncio

# Since bot.py is outside the src package, we need to adjust the path
# to ensure correct imports from our source files.
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.keyboards import TUTOR_BUTTONS, STUDENT_BUTTONS, PARENT_BUTTONS
# Импортируем из микросервисов
from src.handlers.common import start, handle_access_code, cancel_conversation
from src.handlers.shared import button_handler, handle_calendar_selection, chat_with_tutor_start, forward_message_to_tutor, handle_tutor_reply, CHAT_WITH_TUTOR

# Импортируем обработчики репетитора
from src.handlers.tutor import (
    tutor_add_student_start, tutor_get_student_name, tutor_get_parent_code,
    tutor_add_payment_start, tutor_get_payment_amount,
    tutor_add_lesson_start, tutor_get_lesson_topic, tutor_get_lesson_date, tutor_get_lesson_skills,
    tutor_edit_name_start, tutor_get_new_name, tutor_add_parent_start, tutor_get_parent_name,
    tutor_select_parent_type, tutor_select_existing_parent,
    tutor_add_second_parent_start, tutor_get_second_parent_name,
    tutor_select_second_parent_type, tutor_select_existing_second_parent,
    tutor_remove_second_parent, tutor_replace_second_parent,
    tutor_delete_student_start, tutor_delete_student_confirm,
    tutor_mark_lesson_attended, tutor_set_lesson_attendance, tutor_check_homework,
    tutor_set_homework_status, tutor_edit_lesson_start, tutor_edit_lesson_get_status, tutor_edit_lesson_get_comment,
    tutor_edit_attendance_status, tutor_edit_mastery_status, tutor_set_attendance_in_conversation,
    tutor_edit_lesson_conduct_status, tutor_set_lesson_conduct,
    tutor_add_hw_start, tutor_get_hw_description, tutor_get_hw_deadline, tutor_get_hw_link, tutor_get_hw_photos,
    show_student_list, show_tutor_stats, show_tutor_dashboard,
    report_start, report_select_student, report_select_month_and_generate, report_cancel,
    tutor_manage_library, tutor_add_material_start, tutor_add_material_with_grade, tutor_get_material_grade, tutor_get_material_title, 
    tutor_get_material_link, tutor_get_material_description,
    broadcast_start, broadcast_get_message, broadcast_cancel, broadcast_send,
    tutor_delete_lesson_start, tutor_confirm_delete_lesson,
    tutor_schedule_setup_start, tutor_schedule_toggle_day, tutor_schedule_back,
    tutor_message_student_start_wrapper, tutor_parent_contact_start, tutor_message_parent_start_wrapper,
    tutor_message_input, tutor_message_send_wrapper, tutor_message_cancel
)

# Импортируем обработчики ученика
from src.handlers.student import (
    student_submit_homework_start, student_get_homework_submission, SUBMIT_HOMEWORK_FILE,
    show_my_progress, show_schedule, show_materials_library, show_lesson_history,
    show_homework_menu, show_student_achievements, show_payment_and_attendance
)

# Импортируем обработчики родителя
from src.handlers.parent import show_parent_dashboard

# Состояния ConversationHandler (исключаем уже импортированные CHAT_WITH_TUTOR и SUBMIT_HOMEWORK_FILE)
(ADD_STUDENT_NAME, ADD_PARENT_CODE, ADD_PARENT_NAME, ADD_PAYMENT_AMOUNT, 
 ADD_LESSON_TOPIC, ADD_LESSON_DATE, ADD_LESSON_SKILLS, RESCHEDULE_LESSON_DATE,
 EDIT_STUDENT_NAME, EDIT_LESSON_STATUS, EDIT_LESSON_COMMENT,
 ADD_HW_DESC, ADD_HW_DEADLINE, ADD_HW_LINK, ADD_HW_PHOTOS,
 SELECT_STUDENT_FOR_REPORT, SELECT_MONTH_FOR_REPORT,
 ADD_MATERIAL_GRADE, ADD_MATERIAL_TITLE, ADD_MATERIAL_LINK, ADD_MATERIAL_DESC,
 BROADCAST_MESSAGE, BROADCAST_CONFIRM, SELECT_PARENT_TYPE, SELECT_EXISTING_PARENT,
 SELECT_SECOND_PARENT_TYPE, SELECT_EXISTING_SECOND_PARENT, ADD_SECOND_PARENT_NAME,
 MESSAGE_INPUT, MESSAGE_CONFIRM) = range(30)
from src.database import engine, Base
from src.scheduler import send_reminders, send_payment_reminders, send_homework_deadline_reminders
from src.admin_handlers import add_tutor, add_parent

# Загружаем переменные окружения из .env файла
load_dotenv()


# Профессиональное логирование
from src.logger import setup_logging, log_user_action, log_telegram_error, metrics
from src.health_monitor import health_monitor, setup_default_checks

logger = setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_dir=os.getenv("LOG_DIR", "logs")
)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Профессиональный обработчик ошибок с логированием и метриками."""
    
    # Логируем ошибку через профессиональную систему
    log_telegram_error(logger, update, context, "Global Error Handler")
    
    # Записываем метрики
    metrics.record_error()
    
    # Отправляем пользователю дружественное сообщение
    if update and hasattr(update, 'effective_user') and update.effective_user:
        try:
            user_id = update.effective_user.id
            log_user_action(user_id, "error_encountered", str(context.error)[:100])
            
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠️ Произошла техническая ошибка. Попробуйте позже или обратитесь к администратору.\n"
                     "Мы уже получили уведомление и работаем над исправлением."
            )
        except Exception as send_error:
            logger.error(f"Failed to send error message to user: {send_error}")
    
    # В критических случаях уведомляем администратора
    admin_id = os.getenv("ADMIN_USER_ID")
    if admin_id and context.error and "critical" in str(context.error).lower():
        try:
            await context.bot.send_message(
                chat_id=int(admin_id),
                text=f"🚨 CRITICAL ERROR:\n{context.error}"
            )
        except Exception:
            pass

# Токен бота из .env файла
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("Необходимо создать .env файл и добавить в него TELEGRAM_TOKEN")


async def start_scheduler(application):
    """Инициализирует и запускает планировщик задач."""
    scheduler = AsyncIOScheduler(timezone="Europe/Kaliningrad")
    
    # Напоминания о предстоящих уроках (каждый час)
    scheduler.add_job(send_reminders, 'interval', hours=1, args=[application], name="Lesson Reminders")
    
    # Напоминания о низком балансе (каждый день в 10:00)
    scheduler.add_job(send_payment_reminders, 'cron', hour=10, minute=0, args=[application], name="Payment Reminders")
    
    # Напоминания о дедлайнах ДЗ (каждый день в 12:00)
    scheduler.add_job(send_homework_deadline_reminders, 'cron', hour=12, minute=0, args=[application], name="Homework Deadline Reminders")
    
    scheduler.start()
    logger.info("Планировщик запущен с задачами: напоминания об уроках, балансе и дедлайнах ДЗ")

async def start_health_monitoring(application):
    """Инициализирует систему мониторинга здоровья с устойчивой проверкой подключения к Telegram API."""
    setup_default_checks()

    async def check_bot_connection():
        try:
            # Попытка получить информацию о боте с таймаутом
            await asyncio.wait_for(application.bot.get_me(), timeout=10)
            return True
        except Exception as e:
            logger.warning(f"Health check bot_connection failed: {e}")
            return False

    # Добавляем проверку с интервалом и обработкой ретраев
    health_monitor.add_check("bot_connection", check_bot_connection, interval=120, retries=2)
    health_monitor.bot_application = application

    # Запускаем мониторинг
    await health_monitor.start_monitoring()
    logger.info("Система мониторинга здоровья запущена")

async def initialize_systems(application):
    """Инициализирует все системы бота."""
    try:
        # Сначала инициализируем сам бот
        await application.bot.initialize()
        logger.info("Бот инициализирован")
        
        # Проверяем соединение
        me = await application.bot.get_me()
        logger.info(f"Подключение к Telegram API установлено. Бот: @{me.username}")
        
        # Запускаем системы
        await start_scheduler(application)
        await start_health_monitoring(application)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации систем: {e}")
        raise

def main() -> None:
    """Запускает бота."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/checked.")

    # Создаем приложение с улучшенными настройками таймаута и обработки ошибок
    application = (Application.builder()
                   .token(TOKEN)
                   .post_init(initialize_systems)
                   .connect_timeout(30)  # Таймаут подключения 30 сек
                   .read_timeout(30)     # Таймаут чтения 30 сек
                   .write_timeout(30)    # Таймаут записи 30 сек
                   .pool_timeout(10)     # Таймаут пула соединений 10 сек
                   .build())

    # --- Диалоги ---
    # Диалог добавления студента (репетитор)
    add_student_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tutor_add_student_start, pattern="^add_student$")],
        states={
            ADD_STUDENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_student_name)],
            ADD_PARENT_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_parent_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_user=True,
        per_chat=True,
        per_message=False
    )
    add_payment_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tutor_add_payment_start, pattern="^tutor_add_payment_")],
        states={ADD_PAYMENT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_payment_amount)]},
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_user=True,
        per_chat=True,
        per_message=False
    )
    add_lesson_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tutor_add_lesson_start, pattern="^tutor_add_lesson_")],
        states={
            ADD_LESSON_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_lesson_topic)],
            ADD_LESSON_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_lesson_date)],
            ADD_LESSON_SKILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_lesson_skills)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_user=True,
        per_chat=True,
        per_message=False
    )
    edit_student_name_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tutor_edit_name_start, pattern="^tutor_edit_name_")],
        states={EDIT_STUDENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_new_name)]},
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_user=True,
        per_chat=True,
        per_message=False
    )
    add_parent_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tutor_add_parent_start, pattern="^tutor_add_parent_")],
        states={
            SELECT_PARENT_TYPE: [CallbackQueryHandler(tutor_select_parent_type, pattern="^(parent_create_new|parent_select_existing|parent_back_to_choice|main_menu)$")],
            SELECT_EXISTING_PARENT: [CallbackQueryHandler(tutor_select_existing_parent, pattern="^(parent_select_|parent_back_to_choice).*")],
            ADD_PARENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_parent_name)]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_user=True,
        per_chat=True,
        per_message=False
    )
    add_second_parent_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(tutor_add_second_parent_start, pattern="^tutor_add_second_parent_"),
            CallbackQueryHandler(tutor_replace_second_parent, pattern="^tutor_replace_second_parent_")
        ],
        states={
            SELECT_SECOND_PARENT_TYPE: [CallbackQueryHandler(tutor_select_second_parent_type, pattern="^(second_parent_create_new|second_parent_select_existing|second_parent_back_to_choice|main_menu)$")],
            SELECT_EXISTING_SECOND_PARENT: [CallbackQueryHandler(tutor_select_existing_second_parent, pattern="^(second_parent_select_|second_parent_back_to_choice).*")],
            ADD_SECOND_PARENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_second_parent_name)]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_user=True,
        per_chat=True,
        per_message=False
    )
    add_hw_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tutor_add_hw_start, pattern="^tutor_add_hw_")],
        states={
            ADD_HW_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_hw_description)],
            ADD_HW_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_hw_deadline)],
            ADD_HW_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_hw_link)],
            ADD_HW_PHOTOS: [MessageHandler(filters.TEXT | filters.PHOTO, tutor_get_hw_photos)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_user=True,
        per_chat=True,
        per_message=False
    )
    chat_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(chat_with_tutor_start, pattern="^chat_with_tutor$"),
            CallbackQueryHandler(chat_with_tutor_start, pattern="^parent_chat_with_tutor$"),
            CallbackQueryHandler(button_handler, pattern="^tutor_reply_to_"),
            MessageHandler(filters.Regex(f"^{STUDENT_BUTTONS['chat']}$"), chat_with_tutor_start)
        ],
        states={
            CHAT_WITH_TUTOR: [MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, chat_with_tutor_start)]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_user=True,
        per_chat=True,
        per_message=False
    )

    report_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{TUTOR_BUTTONS['monthly_report']}$"), report_start)],
        states={
            SELECT_STUDENT_FOR_REPORT: [CallbackQueryHandler(report_select_student, pattern="^report_select_student_")],
            SELECT_MONTH_FOR_REPORT: [CallbackQueryHandler(report_select_month_and_generate, pattern="^report_select_month_")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            CallbackQueryHandler(report_cancel, pattern="^cancel_report$")
        ],
        per_user=True,
        per_chat=True,
        per_message=False
    )

    add_material_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(tutor_add_material_start, pattern="^tutor_add_material$"),
            CallbackQueryHandler(tutor_add_material_with_grade, pattern="^tutor_add_material_grade_")
        ],
        states={
            ADD_MATERIAL_GRADE: [CallbackQueryHandler(tutor_get_material_grade, pattern="^select_grade_")],
            ADD_MATERIAL_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_material_title)],
            ADD_MATERIAL_LINK: [
                MessageHandler(filters.TEXT, tutor_get_material_link),
                CommandHandler("skip", tutor_get_material_link)
            ],
            ADD_MATERIAL_DESC: [
                MessageHandler(filters.TEXT, tutor_get_material_description),
                CommandHandler("skip", tutor_get_material_description)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_user=True,
        per_chat=True,
        per_message=False
    )
    
    submit_hw_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(student_submit_homework_start, pattern="^student_submit_hw_")],
        states={
            SUBMIT_HOMEWORK_FILE: [MessageHandler(filters.TEXT | filters.Document.ALL | filters.PHOTO, student_get_homework_submission)]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_user=True,
        per_chat=True,
        per_message=False
    )

    broadcast_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(f"^{TUTOR_BUTTONS['broadcast']}$"), broadcast_start),
            CommandHandler("broadcast", broadcast_start)
        ],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL, broadcast_get_message)],
            BROADCAST_CONFIRM: [
                CallbackQueryHandler(broadcast_send, pattern="^broadcast_send$"),
                CallbackQueryHandler(broadcast_cancel, pattern="^broadcast_cancel$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_user=True,
        per_chat=True,
        per_message=False
    )


    edit_lesson_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tutor_edit_lesson_start, pattern="^tutor_edit_lesson_")],
        states={
            EDIT_LESSON_STATUS: [
                CallbackQueryHandler(tutor_edit_lesson_get_status, pattern="^tutor_set_mastery_"),
                CallbackQueryHandler(tutor_edit_attendance_status, pattern="^tutor_edit_attendance_"),
                CallbackQueryHandler(tutor_edit_mastery_status, pattern="^tutor_edit_mastery_"),
                CallbackQueryHandler(tutor_edit_lesson_conduct_status, pattern="^tutor_edit_lesson_conduct_"),
                CallbackQueryHandler(tutor_set_lesson_conduct, pattern="^tutor_set_lesson_conduct_"),
                CallbackQueryHandler(tutor_set_attendance_in_conversation, pattern="^tutor_set_attendance_")
            ],
            EDIT_LESSON_COMMENT: [
                MessageHandler(filters.TEXT, tutor_edit_lesson_get_comment),
                CommandHandler("skip", tutor_edit_lesson_get_comment)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_user=True,
        per_chat=True,
        per_message=True
    )

    message_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(tutor_message_student_start_wrapper, pattern="^tutor_message_student_"),
            CallbackQueryHandler(tutor_message_parent_start_wrapper, pattern="^tutor_message_parent_")
        ],
        states={
            MESSAGE_INPUT: [
                MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, tutor_message_input)
            ],
            MESSAGE_CONFIRM: [
                CallbackQueryHandler(tutor_message_send_wrapper, pattern="^send_message_"),
                CallbackQueryHandler(tutor_message_cancel, pattern="^message_cancel$")
            ],
        },
        fallbacks=[
            CallbackQueryHandler(tutor_message_cancel, pattern="^message_cancel$")
        ],
        per_user=True,
        per_chat=True,
        per_message=False
    )

    # --- Регистрация обработчиков ---
    # ВАЖНО: ConversationHandlers должны быть зарегистрированы ПЕРЕД общими CallbackQueryHandlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_calendar_selection, pattern="^calendar"))
    
    # --- Admin Commands ---
    application.add_handler(CommandHandler("add_tutor", add_tutor))
    application.add_handler(CommandHandler("add_parent", add_parent))
    
    # ConversationHandlers регистрируем ПЕРЕД button_handler, чтобы они перехватывали свои callback'ы первыми
    application.add_handler(add_student_conv)
    application.add_handler(add_payment_conv)
    application.add_handler(add_lesson_conv)
    application.add_handler(edit_student_name_conv)
    application.add_handler(add_parent_conv)
    application.add_handler(add_second_parent_conv)
    application.add_handler(edit_lesson_conv)
    application.add_handler(add_hw_conv)
    application.add_handler(chat_conv)
    application.add_handler(report_conv)
    application.add_handler(add_material_conv)
    application.add_handler(submit_hw_conv)
    application.add_handler(broadcast_conv)
    application.add_handler(message_conv)
    
    # button_handler обрабатывает все остальные callback'ы ПОСЛЕ ConversationHandlers
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(?!(tutor_add_payment_|tutor_add_lesson_|tutor_add_parent_|tutor_add_second_parent_|tutor_edit_name_|tutor_edit_lesson_|tutor_edit_attendance_|tutor_edit_mastery_|tutor_set_mastery_|tutor_add_hw_|student_submit_hw_|report_select_|broadcast_|add_student|tutor_add_material|select_grade_|second_parent_|tutor_message_student_|tutor_message_parent_|send_message_|message_cancel)).*"))

    # Импортируем микросервисы
    from src.handlers.tutor import show_tutor_dashboard, show_student_list
    from src.handlers.student import show_homework_menu, show_my_progress, show_schedule, show_materials_library, show_lesson_history, show_student_achievements, show_payment_and_attendance
    from src.handlers.parent import show_parent_dashboard
    
    # Обработчики кнопок репетитора
    application.add_handler(MessageHandler(filters.Regex(f"^{TUTOR_BUTTONS['students']}$"), show_student_list))
    application.add_handler(MessageHandler(filters.Regex(f"^{TUTOR_BUTTONS['add_student']}$"), show_student_list))
    application.add_handler(MessageHandler(filters.Regex(f"^{TUTOR_BUTTONS['monthly_report']}$"), report_start))
    application.add_handler(MessageHandler(filters.Regex(f"^{TUTOR_BUTTONS['library']}$"), tutor_manage_library))
    application.add_handler(MessageHandler(filters.Regex(f"^{TUTOR_BUTTONS['stats']}$"), show_tutor_stats))
    application.add_handler(MessageHandler(filters.Regex(f"^{TUTOR_BUTTONS['broadcast']}$"), broadcast_start))
    
    # Обработчики для кнопок ученика
    application.add_handler(MessageHandler(filters.Regex(f"^{STUDENT_BUTTONS['lessons_history']}$"), show_lesson_history))
    application.add_handler(MessageHandler(filters.Regex(f"^{STUDENT_BUTTONS['schedule']}$"), show_schedule))
    application.add_handler(MessageHandler(filters.Regex(f"^{STUDENT_BUTTONS['homework']}$"), show_homework_menu))
    application.add_handler(MessageHandler(filters.Regex(f"^{STUDENT_BUTTONS['progress']}$"), show_my_progress))
    application.add_handler(MessageHandler(filters.Regex(f"^{STUDENT_BUTTONS['payment']}$"), show_payment_and_attendance))
    application.add_handler(MessageHandler(filters.Regex(f"^{STUDENT_BUTTONS['achievements']}$"), show_student_achievements))
    application.add_handler(MessageHandler(filters.Regex(f"^{STUDENT_BUTTONS['library']}$"), show_materials_library))
    application.add_handler(MessageHandler(filters.Regex(f"^{STUDENT_BUTTONS['chat']}$"), chat_with_tutor_start))
    
    # Обработчики для кнопок родителя
    application.add_handler(MessageHandler(filters.Regex(f"^{PARENT_BUTTONS['dashboard']}$"), show_parent_dashboard))
    application.add_handler(MessageHandler(filters.Regex(f"^{PARENT_BUTTONS['chat']}$"), chat_with_tutor_start))
    
    # Этот обработчик должен быть ПЕРЕД обработчиком handle_access_code, 
    # чтобы правильно перехватывать ответы репетитора.
    application.add_handler(MessageHandler(filters.REPLY & filters.TEXT & ~filters.COMMAND, handle_tutor_reply))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_access_code))

    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)

    # --- Запуск бота ---
    logger.info("Запускаем бота...")
    
    try:
        # Запуск с настройками таймаута для polling
        application.run_polling(
            timeout=30,          # Таймаут для long polling
            bootstrap_retries=3, # Количество попыток переподключения
            close_loop=True,     # Закрыть event loop при завершении
            stop_signals=None    # Отключаем default stop signals для Windows
        )
    except KeyboardInterrupt:
        logger.info("Получен сигнал завершения работы")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        raise
    finally:
        logger.info("Завершение работы бота")


if __name__ == "__main__":
    main()