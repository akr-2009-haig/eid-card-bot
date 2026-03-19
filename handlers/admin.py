import os
import sys

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_users_count, get_templates_count, get_channels, get_text
from keyboards.admin_keyboard import (
    admin_main_keyboard, admin_templates_keyboard, admin_forcesub_keyboard,
    admin_texts_keyboard, admin_buttons_keyboard, admin_ads_keyboard,
    admin_back_keyboard
)
from handlers.texts_buttons import set_admin_text_state
from utils.helpers import is_admin


def register_admin_handler(app: Client):

    @app.on_message(filters.command("admin") & filters.private)
    async def admin_command(client: Client, message: Message):
        if not is_admin(message.from_user.id):
            await message.reply("⛔ هذا الأمر للأدمن فقط.", quote=True)
            return
        text = "👑 لوحة تحكم البوت\n\nاختر القسم الذي تريد التحكم به"
        await message.reply(text, reply_markup=admin_main_keyboard(), quote=True)

    @app.on_callback_query(filters.regex("^admin_back$"))
    async def admin_back(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        text = "👑 لوحة تحكم البوت\n\nاختر القسم الذي تريد التحكم به"
        await callback.message.edit_text(text, reply_markup=admin_main_keyboard())
        await callback.answer()

    @app.on_callback_query(filters.regex("^admin_stats$"))
    async def admin_stats(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        users = get_users_count()
        templates = get_templates_count()
        channels = get_channels()
        text = (
            "📊 إحصائيات البوت\n\n"
            f"👥 عدد المستخدمين: {users}\n"
            f"🎨 عدد القوالب: {templates}\n"
            f"📢 عدد قنوات الاشتراك: {len(channels)}"
        )
        await callback.message.edit_text(text, reply_markup=admin_back_keyboard())
        await callback.answer()

    @app.on_callback_query(filters.regex("^admin_templates$"))
    async def admin_templates_menu(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        await callback.message.edit_text(
            "🎨 إدارة قوالب بطاقات العيد\n"
            "يمكنك من هنا إدارة القوالب التي يستخدمها البوت لتصميم بطاقات التهنئة.",
            reply_markup=admin_templates_keyboard()
        )
        await callback.answer()

    @app.on_callback_query(filters.regex("^admin_forcesub$"))
    async def admin_forcesub_menu(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        await callback.message.edit_text(
            "🔒 إدارة الاشتراك الإجباري\n"
            "يمكنك إضافة أو حذف القنوات أو القروبات التي يجب على المستخدم الاشتراك فيها قبل استخدام البوت.",
            reply_markup=admin_forcesub_keyboard()
        )
        await callback.answer()

    @app.on_callback_query(filters.regex("^admin_texts$"))
    async def admin_texts_menu(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        await callback.message.edit_text(
            "📝 إدارة النصوص والأزرار\n"
            "يمكنك من هنا تعديل رسائل البوت والأزرار التي تظهر للمستخدمين.",
            reply_markup=admin_texts_keyboard()
        )
        await callback.answer()

    @app.on_callback_query(filters.regex("^admin_buttons$"))
    async def admin_buttons_menu(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        await callback.message.edit_text(
            "🔘 إدارة الأزرار التي تظهر أسفل البطاقة",
            reply_markup=admin_buttons_keyboard()
        )
        await callback.answer()

    @app.on_callback_query(filters.regex("^admin_ads$"))
    async def admin_ads_menu(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        await callback.message.edit_text(
            "📢 قسم الإعلانات",
            reply_markup=admin_ads_keyboard()
        )
        await callback.answer()

    @app.on_callback_query(filters.regex("^admin_settings$"))
    async def admin_settings_menu(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        await callback.message.edit_text(
            "⚙️ إعدادات البوت\n\nلا توجد إعدادات إضافية حالياً.",
            reply_markup=admin_back_keyboard()
        )
        await callback.answer()

    @app.on_callback_query(
        filters.regex("^admin_edit_(start|ask_name|designing|card_ready|forcesub_msg)$")
    )
    async def admin_edit_text_cb(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        key_map = {
            "admin_edit_start": "start_message",
            "admin_edit_ask_name": "ask_name_message",
            "admin_edit_designing": "designing_message",
            "admin_edit_card_ready": "card_ready_message",
            "admin_edit_forcesub_msg": "forcesub_message",
        }
        text_key = key_map.get(callback.data)
        if not text_key:
            await callback.answer("خطأ", show_alert=True)
            return

        set_admin_text_state(callback.from_user.id, text_key)

        current = get_text(text_key)
        prompt_map = {
            "start_message": "✏️ أرسل رسالة البداية الجديدة",
            "ask_name_message": "✏️ أرسل رسالة طلب الاسم الجديدة",
            "designing_message": "✏️ أرسل رسالة الانتظار أثناء تصميم البطاقة",
            "card_ready_message": "✏️ أرسل الرسالة التي ستظهر بعد إرسال البطاقة",
            "forcesub_message": "✏️ أرسل رسالة الاشتراك الجديدة",
        }
        await callback.message.edit_text(
            f"{prompt_map.get(text_key, '✏️ أرسل النص الجديد')}\n\n"
            f"النص الحالي:\n\n{current}"
        )
        await callback.answer()
