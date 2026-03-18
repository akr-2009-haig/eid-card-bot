import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pyrogram import Client
from config import BOT_TOKEN, API_ID, API_HASH
from database.db import init_db
from utils.helpers import logger

from handlers.start import register_start_handler
from handlers.forcesub import register_forcesub_handler
from handlers.user import register_user_handlers
from handlers.admin import register_admin_handler
from handlers.templates import register_template_handlers
from handlers.texts_buttons import register_texts_buttons_handlers
from handlers.forcesub_admin import register_forcesub_admin_handlers
from handlers.ads import register_ads_handlers
from handlers.admin_text_handler import register_admin_text_message_handler


def create_app() -> Client:
    if not API_ID or not API_HASH:
        app = Client(
            name="eid_card_bot",
            bot_token=BOT_TOKEN,
            in_memory=True
        )
    else:
        app = Client(
            name="eid_card_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            in_memory=True
        )
    return app


def main():
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized.")

    os.makedirs("data/templates", exist_ok=True)
    os.makedirs("data/fonts", exist_ok=True)
    os.makedirs("data/generated", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    app = create_app()

    register_admin_text_message_handler(app)
    register_forcesub_admin_handlers(app)
    register_texts_buttons_handlers(app)
    register_ads_handlers(app)
    register_template_handlers(app)
    register_admin_handler(app)
    register_forcesub_handler(app)
    register_user_handlers(app)
    register_start_handler(app)

    logger.info("Starting bot with long polling...")
    app.run()


if __name__ == "__main__":
    main()
