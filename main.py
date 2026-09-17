"""Entry point. Runs in parallel:
  - the user-facing bot (Telegram polling, /start etc.)
  - the watcher that monitors INCOMING_DIR and publishes complete batches
"""
import asyncio
import logging

from telegram.ext import Application

import bot
import config
import incoming_watcher
import state_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _post_init(application: Application):
    application.create_task(incoming_watcher.run_forever(application.bot))
    logger.info("Incoming watcher started as a background task.")


def main():
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing from .env")

    state_db.init_db()

    application = Application.builder().token(config.BOT_TOKEN).post_init(_post_init).build()
    bot.register_handlers(application)

    logger.info("Bot started.")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
