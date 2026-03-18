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
from utils.telegram_links import normalize_channel_input, resolve_channel_link

_waiting_channel_input: set = set()


def register_forcesub_admin_handlers(app: Client):

    @app.on_callback_query(filters.regex("^admin_add_channel$"))
    async def admin_add_channel_cb(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        _waiting_channel_input.add(callback.from_user.id)
        await callback.message.edit_text(
            "📎 أرسل رابط القناة أو القروب\n\n"
            "يدعم البوت جميع الأنواع التالية:\n"
            "• @channelname\n"
            "• https://t.me/channelname\n"
            "• https://t.me/+AbCdEfGh\n"
            "• https://t.me/joinchat/AbCdEfGh\n\n"
            "ملاحظة: يجب أن يكون البوت أدمن أو عضوًا داخل القناة/القروب ليتمكن من التحقق من الاشتراك."
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
        text = "📢 القنوات والقروبات الحالية:\n\n"
        for index, ch in enumerate(channels, start=1):
            ch_type = ch.get("channel_type", "channel")
            label = "📢" if ch_type == "channel" else "👥"
            title = ch.get("channel_title") or ch.get("channel_username")
            text += f"{index}️⃣ {label} {title}\n{resolve_channel_link(ch)}\n\n"
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
            "✅ تم حذف القناة من الاشتراك الإجباري",
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

        raw_value = message.text.strip()

        try:
            parsed = normalize_channel_input(raw_value)
            chat = await client.get_chat(parsed["lookup_value"])
            chat_type = str(chat.type).lower()
            ch_type = "group" if "group" in chat_type or "supergroup" in chat_type else "channel"
            title = chat.title or parsed["public_username"] or raw_value
            # Prefer the real Telegram username when available, then the parsed public username, then the raw input.
            username = f"@{chat.username}" if getattr(chat, "username", None) else parsed["public_username"] or raw_value
            channel_link = parsed["channel_link"]
            if getattr(chat, "username", None):
                channel_link = f"https://t.me/{chat.username}"

            add_channel(username, title, ch_type, channel_link=channel_link, chat_id=str(chat.id))
            _waiting_channel_input.discard(user_id)
            type_label = "القروب" if ch_type == "group" else "القناة"
            await message.reply(
                f"✅ تم إضافة {type_label} للاشتراك الإجباري\n\n"
                f"📋 الاسم: {title}\n"
                f"🔗 الرابط: {channel_link}\n"
                f"🆔 المعرف: {chat.id}",
                reply_markup=admin_forcesub_keyboard(),
                quote=True
            )
        except Exception as e:
            logger.warning(f"Channel add error for {raw_value}: {e}")
            await message.reply(
                "❌ تعذر إضافة الرابط.\n\n"
                "تأكد من أن الرابط صحيح وأن البوت أدمن أو عضو داخل القناة/القروب، ثم أرسل الرابط مرة أخرى.",
                reply_markup=admin_back_keyboard(),
                quote=True
            )
