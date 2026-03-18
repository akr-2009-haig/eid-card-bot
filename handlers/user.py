import os
import sys

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import (
    get_text, get_buttons, get_channels, get_templates,
    add_user, log_generated_card, update_template_path
)
from keyboards.user_keyboard import (
    main_menu_keyboard, forcesub_keyboard, back_home_keyboard, card_result_keyboard
)
from services.subscription_checker import check_subscription
from services.image_generator import generate_card, pick_random_template
from utils.helpers import logger
from utils.rate_limit import is_rate_limited, reset_rate_limit

_waiting_for_name: set = set()


def register_user_handlers(app: Client):

    @app.on_callback_query(filters.regex("^design_card$"))
    async def design_card_callback(client: Client, callback: CallbackQuery):
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
                await callback.answer()
                return

        templates = get_templates()
        if not templates:
            await callback.answer(
                "⚠️ لا توجد قوالب متاحة حالياً. يرجى التواصل مع الأدمن.",
                show_alert=True
            )
            return

        if is_rate_limited(user.id, seconds=10):
            await callback.answer(
                "⏳ يرجى الانتظار قليلاً قبل طلب بطاقة جديدة.",
                show_alert=True
            )
            return

        _waiting_for_name.add(user.id)
        text = get_text("ask_name_message")
        await callback.message.edit_text(
            text,
            reply_markup=back_home_keyboard()
        )
        await callback.answer()

    @app.on_message(filters.private & filters.text & ~filters.command(["start", "admin"]))
    async def handle_name_input(client: Client, message: Message):
        user = message.from_user
        if user.id not in _waiting_for_name:
            return

        name = message.text.strip()
        if not name or len(name) > 50:
            await message.reply("⚠️ اسم غير صالح. أرسل اسمك فقط (حتى 50 حرف).", quote=True)
            return

        _waiting_for_name.discard(user.id)

        designing_text = get_text("designing_message")
        wait_msg = await message.reply(designing_text, quote=True)

        try:
            templates = get_templates()
            if not templates:
                await wait_msg.edit_text("⚠️ لا توجد قوالب متاحة حالياً.")
                return

            template = pick_random_template(templates)
            template_path = template.get("file_path", "")

            if not template_path or not os.path.exists(template_path):
                downloaded = await client.download_media(
                    template.get("file_id"),
                    file_name=f"data/templates/template_{template['id']}_dl.jpg"
                )
                template_path = downloaded
                update_template_path(template["id"], template_path)
                template["file_path"] = template_path

            card_path = generate_card(template_path, name, template=template)
            log_generated_card(user.id, name, template["id"])

            card_ready_text = get_text("card_ready_message")
            extra_buttons = get_buttons()

            await wait_msg.delete()
            await client.send_photo(
                chat_id=user.id,
                photo=card_path,
                caption=card_ready_text,
                reply_markup=card_result_keyboard(extra_buttons)
            )

            try:
                os.remove(card_path)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Card generation error for user {user.id}: {e}")
            await wait_msg.edit_text(
                "❌ حدث خطأ أثناء التصميم. حاول مرة أخرى.",
                reply_markup=back_home_keyboard()
            )
