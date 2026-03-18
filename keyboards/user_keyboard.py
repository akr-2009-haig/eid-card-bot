from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.telegram_links import resolve_channel_link


def main_menu_keyboard(extra_buttons: list = None) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🎨 تصميم بطاقة", callback_data="design_card")],
        [InlineKeyboardButton("ℹ️ طريقة الاستخدام", callback_data="how_to_use")],
    ]
    if extra_buttons:
        for btn in extra_buttons:
            rows.append([InlineKeyboardButton(btn["label"], url=btn["url"])])
    return InlineKeyboardMarkup(rows)


def forcesub_keyboard(channels: list) -> InlineKeyboardMarkup:
    rows = []
    for index, ch in enumerate(channels, start=1):
        ch_type = ch.get("channel_type", "channel")
        label_prefix = "📢 قناة" if ch_type == "channel" else "👥 قروب"
        title = ch.get("channel_title") or ch.get("channel_username", "")
        url = resolve_channel_link(ch)
        rows.append([InlineKeyboardButton(f"{label_prefix} {index}️⃣ | {title}", url=url)])
    rows.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")])
    return InlineKeyboardMarkup(rows)


def card_result_keyboard(extra_buttons: list = None) -> InlineKeyboardMarkup:
    rows = []
    if extra_buttons:
        for btn in extra_buttons:
            rows.append([InlineKeyboardButton(btn["label"], url=btn["url"])])
    rows.extend([
        [InlineKeyboardButton("🎨 تصميم بطاقة جديدة", callback_data="design_card")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")],
    ])
    return InlineKeyboardMarkup(rows)


def back_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")]
    ])
