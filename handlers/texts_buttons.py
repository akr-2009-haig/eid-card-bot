import os
import sys
from urllib.parse import urlparse

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_buttons, delete_button, add_button, set_text, get_text
from keyboards.admin_keyboard import (
    admin_texts_keyboard, admin_buttons_keyboard,
    admin_back_keyboard, button_delete_keyboard
)
from utils.helpers import is_admin, logger

_admin_text_state: dict = {}
_waiting_button_input: set = set()
_button_input_data: dict = {}


def _is_valid_button_url(url: str) -> bool:
    if url.startswith("tg://"):
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)

    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def register_texts_buttons_handlers(app: Client):

    @app.on_callback_query(filters.regex("^admin_view_buttons$"))
    async def admin_view_buttons(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        buttons = get_buttons()
        if not buttons:
            await callback.message.edit_text(
                "📂 لا توجد أزرار مضافة بعد.",
                reply_markup=admin_buttons_keyboard()
            )
            await callback.answer()
            return
        text = "📂 الأزرار الحالية:\n\n"
        for index, b in enumerate(buttons, start=1):
            text += f"{index}️⃣ {b['label']}\n{b['url']}\n\n"
        await callback.message.edit_text(text, reply_markup=admin_buttons_keyboard())
        await callback.answer()

    @app.on_callback_query(filters.regex("^admin_add_button$"))
    async def admin_add_button_cb(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        _waiting_button_input.add(callback.from_user.id)
        _button_input_data[callback.from_user.id] = {"step": "combined"}
        await callback.message.edit_text(
            "✏️ أرسل اسم الزر والرابط بهذا الشكل:\n"
            "اسم الزر\n"
            "الرابط\n\n"
            "مثال:\n"
            "قناة البوت\n"
            "https://t.me/mychannel"
        )
        await callback.answer()

    @app.on_callback_query(filters.regex("^admin_delete_button$"))
    async def admin_delete_button_cb(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        buttons = get_buttons()
        if not buttons:
            await callback.message.edit_text(
                "⚠️ لا توجد أزرار لحذفها.",
                reply_markup=admin_buttons_keyboard()
            )
            await callback.answer()
            return
        await callback.message.edit_text(
            "🗑 اختر الزر الذي تريد حذفه:",
            reply_markup=button_delete_keyboard(buttons)
        )
        await callback.answer()

    @app.on_callback_query(filters.regex(r"^admin_del_btn_(\d+)$"))
    async def admin_confirm_delete_button(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        btn_id = int(callback.data.split("_")[-1])
        delete_button(btn_id)
        await callback.message.edit_text(
            "✅ تم حذف الزر بنجاح",
            reply_markup=admin_buttons_keyboard()
        )
        await callback.answer()

    @app.on_message(filters.private & filters.text & ~filters.command(["start", "admin"]))
    async def handle_admin_text_input(client: Client, message: Message):
        user_id = message.from_user.id
        if not is_admin(user_id):
            return

        if user_id in _waiting_button_input:
            data = _button_input_data.get(user_id, {})
            step = data.get("step")

            if step == "combined":
                parts = [part.strip() for part in message.text.splitlines() if part.strip()]
                if len(parts) != 2:
                    await message.reply(
                        "⚠️ الصيغة غير صحيحة.\n\n"
                        "أرسل سطرين فقط:\n"
                        "1) اسم الزر\n"
                        "2) الرابط",
                        quote=True
                    )
                    return

                label = parts[0]
                url = parts[1]
                if not _is_valid_button_url(url):
                    await message.reply(
                        "⚠️ الرابط غير صالح. أرسل رابطًا صحيحًا يبدأ بـ https:// أو http:// أو tg://",
                        quote=True
                    )
                    return

                _waiting_button_input.discard(user_id)
                _button_input_data.pop(user_id, None)
                add_button(label, url)
                await message.reply(
                    f"✅ تم إضافة الزر بنجاح\n\n🔘 {label}\n🔗 {url}",
                    reply_markup=admin_buttons_keyboard(),
                    quote=True
                )
            return

        if user_id in _admin_text_state:
            state = _admin_text_state.pop(user_id)
            text_key = state.get("text_key")
            if text_key:
                set_text(text_key, message.text.strip())
                await message.reply(
                    "✅ تم تحديث النص بنجاح",
                    reply_markup=admin_texts_keyboard(),
                    quote=True
                )
            return


def set_admin_text_state(user_id: int, text_key: str):
    _admin_text_state[user_id] = {"text_key": text_key}
