import os
import sys

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import add_user, get_text, get_buttons, get_channels
from keyboards.user_keyboard import main_menu_keyboard, forcesub_keyboard, back_home_keyboard
from services.subscription_checker import check_subscription
from utils.helpers import is_admin


def register_start_handler(app: Client):

    @app.on_message(filters.command("start") & filters.private)
    async def start_handler(client: Client, message: Message):
        user = message.from_user
        add_user(user.id, user.username or "", user.full_name or "")

        channels = get_channels()
        if channels:
            subscribed, missing = await check_subscription(client, user.id, channels)
            if not subscribed:
                text = get_text("forcesub_message")
                await message.reply(
                    text,
                    reply_markup=forcesub_keyboard(missing),
                    quote=True
                )
                return

        extra_buttons = get_buttons()
        text = get_text("start_message")
        await message.reply(
            text,
            reply_markup=main_menu_keyboard(extra_buttons),
            quote=True
        )

    @app.on_callback_query(filters.regex("^back_home$"))
    async def back_home_callback(client: Client, callback: CallbackQuery):
        user = callback.from_user
        add_user(user.id, user.username or "", user.full_name or "")

        channels = get_channels()
        if channels:
            subscribed, missing = await check_subscription(client, user.id, channels)
            if not subscribed:
                text = get_text("forcesub_message")
                await callback.message.edit_text(
                    text,
                    reply_markup=forcesub_keyboard(missing)
                )
                return

        extra_buttons = get_buttons()
        text = get_text("start_message")
        try:
            await callback.message.edit_text(
                text,
                reply_markup=main_menu_keyboard(extra_buttons)
            )
        except Exception:
            await callback.message.reply(
                text,
                reply_markup=main_menu_keyboard(extra_buttons)
            )
        await callback.answer()

    @app.on_callback_query(filters.regex("^how_to_use$"))
    async def how_to_use_callback(client: Client, callback: CallbackQuery):
        text = (
            "📖 طريقة الاستخدام:\n\n"
            "1️⃣ اضغط على زر 🎨 تصميم بطاقة\n"
            "2️⃣ أرسل اسمك\n"
            "3️⃣ سيقوم البوت بتصميم بطاقة التهنئة الخاصة بك\n"
            "4️⃣ احتفظ بالبطاقة وشاركها مع أحبائك 🎉"
        )
        await callback.message.edit_text(text, reply_markup=back_home_keyboard())
        await callback.answer()
