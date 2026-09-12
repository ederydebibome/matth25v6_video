"""Point d'entrée. Lance en parallèle :
  - le bot utilisateur (polling Telegram, /start etc.)
  - le watcher qui surveille INCOMING_DIR et publie les lots complets
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
    logger.info("Watcher incoming lancé en tâche de fond.")


def main():
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN manquant dans .env")

    state_db.init_db()

    application = Application.builder().token(config.BOT_TOKEN).post_init(_post_init).build()
    bot.register_handlers(application)

    logger.info("Bot démarré.")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
