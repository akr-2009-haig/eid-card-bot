import os
import sys

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_templates, delete_template
from keyboards.admin_keyboard import (
    admin_templates_keyboard, template_delete_keyboard, admin_back_keyboard
)
from services.template_manager import save_template_file, register_template, remove_template
from utils.helpers import is_admin, logger

_waiting_template_upload: set = set()


def register_template_handlers(app: Client):

    @app.on_callback_query(filters.regex("^admin_add_template$"))
    async def admin_add_template(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        _waiting_template_upload.add(callback.from_user.id)
        await callback.message.edit_text("📤 أرسل الصورة التي تريد إضافتها كقالب")
        await callback.answer()

    @app.on_message(filters.private & filters.photo)
    async def receive_template_photo(client: Client, message: Message):
        user_id = message.from_user.id
        if not is_admin(user_id):
            return
        if user_id not in _waiting_template_upload:
            return

        _waiting_template_upload.discard(user_id)
        try:
            file_id = message.photo.file_id
            local_path = await client.download_media(
                message.photo,
                file_name=f"data/templates/template_dl_{message.id}.jpg"
            )
            dest_path = save_template_file(file_id, local_path)
            os.remove(local_path)
            tpl_id = register_template(file_id, dest_path)
            await message.reply(
                f"✅ تم إضافة القالب بنجاح\n📁 قالب #{tpl_id}",
                reply_markup=admin_templates_keyboard(),
                quote=True
            )
        except Exception as e:
            logger.error(f"Template upload error: {e}")
            await message.reply("❌ حدث خطأ أثناء حفظ القالب.", quote=True)

    @app.on_callback_query(filters.regex("^admin_view_templates$"))
    async def admin_view_templates(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        templates = get_templates()
        if not templates:
            await callback.message.edit_text(
                "📂 لا توجد قوالب مضافة بعد.",
                reply_markup=admin_templates_keyboard()
            )
            await callback.answer()
            return

        text = f"📂 القوالب المتاحة: {len(templates)} قالب\n\n"
        for t in templates:
            text += f"• قالب #{t['id']} - {t['added_at']}\n"

        await callback.message.edit_text(text, reply_markup=admin_templates_keyboard())
        await callback.answer()

    @app.on_callback_query(filters.regex("^admin_delete_template$"))
    async def admin_delete_template_menu(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        templates = get_templates()
        if not templates:
            await callback.message.edit_text(
                "⚠️ لا توجد قوالب لحذفها.",
                reply_markup=admin_templates_keyboard()
            )
            await callback.answer()
            return
        await callback.message.edit_text(
            "🗑 اختر القالب الذي تريد حذفه:",
            reply_markup=template_delete_keyboard(templates)
        )
        await callback.answer()

    @app.on_callback_query(filters.regex(r"^admin_del_tpl_(\d+)$"))
    async def admin_confirm_delete_template(client: Client, callback: CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ ممنوع", show_alert=True)
            return
        template_id = int(callback.data.split("_")[-1])
        remove_template(template_id)
        await callback.message.edit_text(
            f"✅ تم حذف القالب #{template_id} بنجاح",
            reply_markup=admin_templates_keyboard()
        )
        await callback.answer()
