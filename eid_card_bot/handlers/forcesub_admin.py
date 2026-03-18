import os
import sys

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import add_channel, get_channels, delete_channel
from keyboards.admin_keyboard import (
    admin_forcesub_keyboard, channel_delete_keyboard, admin_back_keyboard
)
from utils.helpers import is_admin, logger

_waiting_channel_input: set = set()


def register_forcesub_admin_handlers(app: Client):

    @app.on_callback_query(filters.regex("^admin_add_channel$"))
    async def admin_add_channel_cb(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        _waiting_channel_input.add(callback.from_user.id)
        await callback.message.edit_text(
            "📎 أرسل يوزر القناة أو القروب\n\n"
            "مثال:\n@channelname\n\n"
            "ملاحظة: يجب أن يكون البوت أدمن في القناة/القروب"
        )
        await callback.answer()

    @app.on_callback_query(filters.regex("^admin_view_channels$"))
    async def admin_view_channels_cb(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        channels = get_channels()
        if not channels:
            await callback.message.edit_text(
                "📂 لا توجد قنوات مضافة بعد.",
                reply_markup=admin_forcesub_keyboard()
            )
            await callback.answer()
            return
        text = f"📂 القنوات المضافة: {len(channels)}\n\n"
        for ch in channels:
            ch_type = ch.get("channel_type", "channel")
            label = "📢" if ch_type == "channel" else "👥"
            text += f"{label} {ch.get('channel_title') or ch.get('channel_username')}\n"
        await callback.message.edit_text(text, reply_markup=admin_forcesub_keyboard())
        await callback.answer()

    @app.on_callback_query(filters.regex("^admin_delete_channel$"))
    async def admin_delete_channel_cb(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        channels = get_channels()
        if not channels:
            await callback.message.edit_text(
                "⚠️ لا توجد قنوات لحذفها.",
                reply_markup=admin_forcesub_keyboard()
            )
            await callback.answer()
            return
        await callback.message.edit_text(
            "🗑 اختر القناة أو القروب الذي تريد حذفه:",
            reply_markup=channel_delete_keyboard(channels)
        )
        await callback.answer()

    @app.on_callback_query(filters.regex(r"^admin_del_ch_(\d+)$"))
    async def admin_confirm_delete_channel(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        ch_id = int(callback.data.split("_")[-1])
        delete_channel(ch_id)
        await callback.message.edit_text(
            "✅ تم حذف القناة بنجاح",
            reply_markup=admin_forcesub_keyboard()
        )
        await callback.answer()

    @app.on_message(filters.private & filters.text & ~filters.command(["start", "admin"]))
    async def handle_channel_input(client: Client, message: Message):
        user_id = message.from_user.id
        if not is_admin(user_id):
            return
        if user_id not in _waiting_channel_input:
            return

        _waiting_channel_input.discard(user_id)
        username = message.text.strip()

        if not username.startswith("@"):
            username = "@" + username

        try:
            chat = await client.get_chat(username)
            chat_type = str(chat.type).lower()
            ch_type = "group" if "group" in chat_type or "supergroup" in chat_type else "channel"
            title = chat.title or username
            add_channel(username, title, ch_type)
            type_label = "القروب" if ch_type == "group" else "القناة"
            await message.reply(
                f"✅ تم إضافة {type_label} للاشتراك الإجباري\n\n"
                f"📋 الاسم: {title}\n👤 اليوزر: {username}",
                reply_markup=admin_forcesub_keyboard(),
                quote=True
            )
        except Exception as e:
            logger.warning(f"Channel add error for {username}: {e}")
            add_channel(username, "", "channel")
            await message.reply(
                f"✅ تم إضافة {username} للاشتراك الإجباري\n\n"
                f"⚠️ تعذّر جلب معلومات القناة. تأكد أن البوت أدمن فيها.",
                reply_markup=admin_forcesub_keyboard(),
                quote=True
            )
