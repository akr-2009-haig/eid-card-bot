import os
import sys

from pyrogram import Client, filters
from pyrogram.types import Message

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import set_text
from keyboards.admin_keyboard import admin_texts_keyboard
from utils.helpers import is_admin

_admin_text_edit_state: dict = {}


def set_state(user_id: int, text_key: str):
    _admin_text_edit_state[user_id] = text_key


def register_admin_text_message_handler(app: Client):

    @app.on_message(filters.private & filters.text & ~filters.command(["start", "admin"]))
    async def handle_admin_text_edit(client: Client, message: Message):
        user_id = message.from_user.id
        if not is_admin(user_id):
            return
        if user_id not in _admin_text_edit_state:
            return
        text_key = _admin_text_edit_state.pop(user_id)
        set_text(text_key, message.text.strip())
        await message.reply(
            "✅ تم تحديث النص بنجاح",
            reply_markup=admin_texts_keyboard(),
            quote=True
        )
