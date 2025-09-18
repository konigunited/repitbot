from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from ..services.lesson_service import get_upcoming_lessons


async def show_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    lessons = await get_upcoming_lessons(user.id)
    if not lessons:
        await update.message.reply_text("No scheduled lessons yet.")
        return

    lines = []
    for lesson in lessons[:5]:
        dt = lesson.get("scheduled_at")
        when = datetime.fromisoformat(dt).strftime("%d.%m %H:%M") if dt else "unspecified"
        lines.append(f"- {lesson.get('subject')} - {lesson.get('topic')} ({when})")
    await update.message.reply_text("Upcoming lessons:\n" + "\n".join(lines))
