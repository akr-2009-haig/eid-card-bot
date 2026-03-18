import os
import sys

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_text, get_buttons, get_channels
from keyboards.user_keyboard import main_menu_keyboard, forcesub_keyboard
from services.subscription_checker import check_subscription


def register_forcesub_handler(app: Client):

    @app.on_callback_query(filters.regex("^check_sub$"))
    async def check_sub_callback(client: Client, callback: CallbackQuery):
        user = callback.from_user
        channels = get_channels()

        if not channels:
            extra_buttons = get_buttons()
            text = get_text("start_message")
            await callback.message.edit_text(
                text,
                reply_markup=main_menu_keyboard(extra_buttons)
            )
            await callback.answer("✅ تم التحقق بنجاح!", show_alert=False)
            return

        subscribed, missing = await check_subscription(client, user.id, channels)
        if subscribed:
            extra_buttons = get_buttons()
            text = get_text("start_message")
            await callback.message.edit_text(
                text,
                reply_markup=main_menu_keyboard(extra_buttons)
            )
            await callback.answer("✅ تم التحقق بنجاح!", show_alert=False)
        else:
            await callback.answer(
                "⚠️ لم تشترك في جميع القنوات بعد!",
                show_alert=True
            )
            text = get_text("forcesub_message")
            await callback.message.edit_reply_markup(
                reply_markup=forcesub_keyboard(missing)
            )
