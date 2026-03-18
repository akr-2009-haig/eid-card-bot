import os
import sys

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_all_users, get_channels
from keyboards.admin_keyboard import admin_ads_keyboard, admin_back_keyboard
from services.broadcast import broadcast_to_users, broadcast_to_channels
from utils.helpers import is_admin, logger

_waiting_broadcast: dict = {}


def register_ads_handlers(app: Client):

    @app.on_callback_query(filters.regex("^admin_broadcast_users$"))
    async def admin_broadcast_users_cb(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        _waiting_broadcast[callback.from_user.id] = "users"
        await callback.message.edit_text(
            "✏️ أرسل الرسالة التي تريد إرسالها للمستخدمين\n\n"
            "(يمكن إرسال نص، صورة، فيديو، أو أي محتوى)"
        )
        await callback.answer()

    @app.on_callback_query(filters.regex("^admin_broadcast_channels$"))
    async def admin_broadcast_channels_cb(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        _waiting_broadcast[callback.from_user.id] = "channels"
        await callback.message.edit_text(
            "✏️ أرسل الرسالة التي تريد إرسالها للقنوات\n\n"
            "(يمكن إرسال نص، صورة، فيديو، أو أي محتوى)"
        )
        await callback.answer()

    @app.on_message(filters.private & ~filters.command(["start", "admin"]))
    async def handle_broadcast_message(client: Client, message: Message):
        user_id = message.from_user.id
        if not is_admin(user_id):
            return
        if user_id not in _waiting_broadcast:
            return

        target = _waiting_broadcast.pop(user_id)

        progress_msg = await message.reply("⏳ جاري إرسال الإعلان...", quote=True)

        try:
            if target == "users":
                user_ids = get_all_users()
                sent, failed = await broadcast_to_users(client, user_ids, message)
                await progress_msg.edit_text(
                    f"✅ تم إرسال الإعلان بنجاح\n\n"
                    f"✉️ تم الإرسال: {sent}\n"
                    f"❌ فشل: {failed}"
                )
            elif target == "channels":
                channels = get_channels()
                ch_usernames = [ch["channel_username"] for ch in channels]
                if not ch_usernames:
                    await progress_msg.edit_text("⚠️ لا توجد قنوات مضافة في قائمة الاشتراك الإجباري.")
                    return
                sent, failed = await broadcast_to_channels(client, ch_usernames, message)
                await progress_msg.edit_text(
                    f"✅ تم إرسال الإعلان بنجاح\n\n"
                    f"📢 تم الإرسال: {sent}\n"
                    f"❌ فشل: {failed}"
                )
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            await progress_msg.edit_text("❌ حدث خطأ أثناء الإرسال.")
