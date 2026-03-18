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
        await callback.message.edit_text(
            "📤 أرسل الصورة التي تريد إضافتها كقالب.\n"
            "يمكنك إرسال PNG أو JPG أو JPEG، وسيتم حفظها داخل مجلد القوالب واستخدامها تلقائيًا عند التصميم."
        )
        await callback.answer()

    @app.on_message(filters.private & (filters.photo | filters.document))
    async def receive_template_photo(client: Client, message: Message):
        user_id = message.from_user.id
        if not is_admin(user_id):
            return
        if user_id not in _waiting_template_upload:
            return

        media = message.photo or message.document
        if message.document and not (message.document.mime_type or "").startswith("image/"):
            await message.reply("⚠️ يرجى إرسال صورة فقط بصيغة PNG أو JPG أو JPEG.", quote=True)
            return

        _waiting_template_upload.discard(user_id)
        try:
            file_id = media.file_id
            local_path = await client.download_media(
                media,
                file_name=f"data/templates/template_dl_{message.id}"
            )
            original_filename = getattr(message.document, "file_name", "") if message.document else os.path.basename(local_path)
            dest_path = save_template_file(local_path, original_filename=original_filename)
            os.remove(local_path)
            tpl_id, metadata = register_template(file_id, dest_path, original_filename=original_filename)
            placeholder_note = (
                f"\n🔎 تم اكتشاف موضع الاسم تلقائيًا عند الإحداثيات: "
                f"X={metadata['placeholder_x']} Y={metadata['placeholder_y']}"
                if metadata
                else "\nℹ️ لم يتم اكتشاف كلمة الاسم تلقائيًا، وسيستخدم البوت الموضع الافتراضي الحالي."
            )
            await message.reply(
                "✅ تم إضافة القالب بنجاح\n"
                "🖼 أصبح القالب متاح الآن لاستخدامه في تصميم البطاقات."
                f"\n📁 رقم القالب: {tpl_id}"
                f"{placeholder_note}",
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

        await callback.message.edit_text(
            f"📂 القوالب الحالية في البوت\nعدد القوالب: {len(templates)}",
            reply_markup=admin_templates_keyboard()
        )
        for template in templates:
            caption = (
                f"🖼 قالب {template['id']}\n"
                f"📄 الملف: {template.get('original_filename') or os.path.basename(template.get('file_path') or '')}\n"
                f"🕒 أضيف في: {template['added_at']}"
            )
            file_path = template.get("file_path", "")
            if not file_path or not os.path.exists(file_path):
                continue
            if os.path.splitext(file_path)[1].lower() == ".png":
                await client.send_document(callback.message.chat.id, file_path, caption=caption)
            else:
                await client.send_photo(callback.message.chat.id, file_path, caption=caption)
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
            "✅ تم حذف القالب بنجاح",
            reply_markup=admin_templates_keyboard()
        )
        await callback.answer()
