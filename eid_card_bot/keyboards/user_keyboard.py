from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


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
    for ch in channels:
        username = ch.get("channel_username", "")
        ch_type = ch.get("channel_type", "channel")
        label_prefix = "📢 قناة" if ch_type == "channel" else "👥 قروب"
        title = ch.get("channel_title") or username
        url = f"https://t.me/{username.lstrip('@')}"
        rows.append([InlineKeyboardButton(f"{label_prefix} | {title}", url=url)])
    rows.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")])
    return InlineKeyboardMarkup(rows)


def card_result_keyboard(extra_buttons: list = None) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🎨 تصميم بطاقة جديدة", callback_data="design_card")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")],
    ]
    if extra_buttons:
        for btn in extra_buttons:
            rows.append([InlineKeyboardButton(btn["label"], url=btn["url"])])
    return InlineKeyboardMarkup(rows)


def back_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")]
    ])
