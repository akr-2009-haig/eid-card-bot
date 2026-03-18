import os
import sys

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
        for b in buttons:
            text += f"• {b['label']} ← {b['url']}\n"
        await callback.message.edit_text(text, reply_markup=admin_buttons_keyboard())
        await callback.answer()

    @app.on_callback_query(filters.regex("^admin_add_button$"))
    async def admin_add_button_cb(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        _waiting_button_input.add(callback.from_user.id)
        _button_input_data[callback.from_user.id] = {"step": "label"}
        await callback.message.edit_text(
            "✏️ أرسل اسم الزر\n\nمثال:\nقناة البوت 📢"
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

            if step == "label":
                _button_input_data[user_id]["label"] = message.text.strip()
                _button_input_data[user_id]["step"] = "url"
                await message.reply(
                    "🔗 الآن أرسل رابط الزر\n\nمثال:\nhttps://t.me/yourchannel",
                    quote=True
                )
            elif step == "url":
                label = _button_input_data[user_id].get("label", "")
                url = message.text.strip()
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
