from telegram import ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.config import get_settings
from ..services.user_service import ensure_user_exists

settings = get_settings()

ROLE_TO_MENU = {
    "tutor": settings.tutor_menu,
    "student": settings.student_menu,
    "parent": settings.parent_menu,
}


async def start(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    profile = await ensure_user_exists(user.id, user.full_name or user.username or "Guest")
    role = profile.get("role", "student")
    keyboard = ROLE_TO_MENU.get(role, settings.student_menu)
    reply_markup = ReplyKeyboardMarkup([keyboard], resize_keyboard=True)

    await update.message.reply_text(
        f"Welcome, {profile.get('full_name', 'friend')}!", reply_markup=reply_markup
    )
