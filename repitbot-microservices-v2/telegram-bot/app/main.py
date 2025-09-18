import asyncio
import logging
import sys
from pathlib import Path

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

BASE_DIR = Path(__file__).resolve().parents[2]
shared_path = BASE_DIR.parent / "shared" / "python"
if str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))

from repitbot_shared.logging import configure_logging  # noqa: E402

from .core.config import get_settings  # noqa: E402
from .handlers.main_menu import start  # noqa: E402
from .handlers.lessons import show_lessons  # noqa: E402
from .services.api_client import api_client  # noqa: E402

settings = get_settings()
logger = configure_logging("telegram-bot")


async def run_bot() -> None:
    application = ApplicationBuilder().token(settings.bot_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("My lessons"), show_lessons))

    logger.info("Telegram bot starting")
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    await application.wait_closed()
    await application.stop()
    await application.shutdown()
    await api_client.close()


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
