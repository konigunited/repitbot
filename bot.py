# -*- coding: utf-8 -*-
import logging
import os
from dotenv import load_dotenv
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, 
                          CallbackQueryHandler, ConversationHandler)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram_bot_calendar import DetailedTelegramCalendar

# Since bot.py is outside the src package, we need to adjust the path
# to ensure correct imports from our source files.
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.keyboards import TUTOR_BUTTONS
from src.handlers import (start, handle_access_code, button_handler,
                      tutor_add_student_start, tutor_get_student_name,
                      tutor_get_parent_code, cancel_conversation,
                      tutor_add_payment_start, tutor_get_payment_amount,
                      tutor_add_lesson_start, tutor_get_lesson_topic,
                      tutor_get_lesson_date, tutor_get_lesson_skills,
                      tutor_edit_name_start, tutor_get_new_name,
                      tutor_delete_student_start, tutor_delete_student_confirm,
                      tutor_mark_lesson_attended, tutor_check_homework,
                      tutor_set_homework_status, tutor_edit_lesson_start,
                      tutor_set_lesson_mastery, tutor_get_lesson_comment,
                      tutor_add_hw_start, tutor_get_hw_description,
                      tutor_get_hw_deadline, tutor_get_hw_link,
                      student_submit_homework_start, student_get_homework_submission,
                      show_my_progress, show_schedule,
                      show_materials_library, chat_with_tutor_start,
                      forward_to_tutor, handle_tutor_reply,
                      show_student_list, show_tutor_stats,
                      ADD_STUDENT_NAME, ADD_PARENT_CODE, ADD_PAYMENT_AMOUNT, 
                      ADD_LESSON_TOPIC, ADD_LESSON_DATE, ADD_LESSON_SKILLS,
                      EDIT_STUDENT_NAME, EDIT_LESSON_COMMENT,
                      ADD_HW_DESC, ADD_HW_DEADLINE, ADD_HW_LINK,
                      CHAT_WITH_TUTOR, SUBMIT_HOMEWORK_FILE,
                      report_start, report_select_student, report_select_month_and_generate,
                      report_cancel, SELECT_STUDENT_FOR_REPORT, SELECT_MONTH_FOR_REPORT,
                      tutor_manage_library, tutor_add_material_start, tutor_get_material_title,
                      tutor_get_material_link, tutor_get_material_description,
                      ADD_MATERIAL_TITLE, ADD_MATERIAL_LINK, ADD_MATERIAL_DESC,
                      show_tutor_dashboard, handle_calendar_selection,
                      broadcast_start, broadcast_get_message, broadcast_cancel,
                      BROADCAST_MESSAGE, BROADCAST_CONFIRM)
from src.database import engine, Base
from src.scheduler import send_reminders, send_payment_reminders
from src.admin_handlers import add_tutor, add_parent

# Загружаем переменные окружения из .env файла
load_dotenv()


# Включаем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота из .env файла
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("Необходимо создать .env файл и добавить в него TELEGRAM_TOKEN")


async def start_scheduler(application):
    """Инициализирует и запускает планировщик задач."""
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    
    # Напоминания о предстоящих уроках (каждый час)
    scheduler.add_job(send_reminders, 'interval', hours=1, args=[application], name="Lesson Reminders")
    
    # Напоминания о низком балансе (каждый день в 10:00)
    scheduler.add_job(send_payment_reminders, 'cron', hour=10, minute=0, args=[application], name="Payment Reminders")
    
    scheduler.start()
    logger.info("Планировщик запущен с двумя задачами: напоминания об уроках и о низком балансе.")

def main() -> None:
    """Запускает бота."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/checked.")

    application = Application.builder().token(TOKEN).post_init(start_scheduler).build()

    # --- Диалоги ---
    add_student_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{TUTOR_BUTTONS['add_student']}$"), tutor_add_student_start)],
        states={
            ADD_STUDENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_student_name)],
            ADD_PARENT_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_parent_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    add_payment_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tutor_add_payment_start, pattern="^tutor_add_payment_")],
        states={ADD_PAYMENT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_payment_amount)]},
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    add_lesson_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tutor_add_lesson_start, pattern="^tutor_add_lesson_")],
        states={
            ADD_LESSON_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_lesson_topic)],
            ADD_LESSON_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_lesson_date)],
            ADD_LESSON_SKILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_lesson_skills)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    edit_student_name_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tutor_edit_name_start, pattern="^tutor_edit_name_")],
        states={EDIT_STUDENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_new_name)]},
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    add_hw_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tutor_add_hw_start, pattern="^tutor_add_hw_")],
        states={
            ADD_HW_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_hw_description)],
            ADD_HW_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_hw_deadline)],
            ADD_HW_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_hw_link)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    chat_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(chat_with_tutor_start, pattern="^chat_with_tutor$")],
        states={CHAT_WITH_TUTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_tutor)]},
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
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
    )

    add_material_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tutor_add_material_start, pattern="^tutor_add_material$")],
        states={
            ADD_MATERIAL_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_material_title)],
            ADD_MATERIAL_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_material_link)],
            ADD_MATERIAL_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_get_material_description)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    
    submit_hw_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(student_submit_homework_start, pattern="^student_submit_hw_")],
        states={
            SUBMIT_HOMEWORK_FILE: [MessageHandler(filters.TEXT | filters.Document.ALL | filters.PHOTO, student_get_homework_submission)]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    broadcast_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(f"^{TUTOR_BUTTONS['broadcast']}$"), broadcast_start),
            CommandHandler("broadcast", broadcast_start)
        ],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO | filters.DOCUMENT, broadcast_get_message)],
            BROADCAST_CONFIRM: [
                CallbackQueryHandler(broadcast_send, pattern="^broadcast_send$"),
                CallbackQueryHandler(broadcast_cancel, pattern="^broadcast_cancel$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )


    # --- Регистрация обработчиков ---
    application.add_handler(add_student_conv)
    application.add_handler(add_payment_conv)
    application.add_handler(add_lesson_conv)
    application.add_handler(edit_student_name_conv)
    application.add_handler(add_hw_conv)
    application.add_handler(chat_conv)
    application.add_handler(report_conv)
    application.add_handler(add_material_conv)
    application.add_handler(submit_hw_conv)
    application.add_handler(broadcast_conv)
    
    # --- Admin Commands ---
    application.add_handler(CommandHandler("add_tutor", add_tutor))
    application.add_handler(CommandHandler("add_parent", add_parent))

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_calendar_selection, pattern="^calendar"))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.add_handler(MessageHandler(filters.Regex(f"^{TUTOR_BUTTONS['students']}$"), show_student_list))
    application.add_handler(MessageHandler(filters.Regex(f"^{TUTOR_BUTTONS['library']}$"), tutor_manage_library))
    application.add_handler(MessageHandler(filters.Regex(f"^{TUTOR_BUTTONS['stats']}$"), show_tutor_dashboard))
    
    application.add_handler(MessageHandler(filters.REPLY & filters.TEXT & ~filters.COMMAND, handle_tutor_reply))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_access_code))

    # --- Запуск бота ---
    logger.info("Запускаем бота...")
    application.run_polling()


if __name__ == "__main__":
    main()