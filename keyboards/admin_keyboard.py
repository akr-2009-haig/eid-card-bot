from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 احصائيات البوت", callback_data="admin_stats")],
        [InlineKeyboardButton("🎨 إدارة القوالب", callback_data="admin_templates")],
        [InlineKeyboardButton("🔒 الاشتراك الإجباري", callback_data="admin_forcesub")],
        [InlineKeyboardButton("📝 النصوص والأزرار", callback_data="admin_texts")],
        [InlineKeyboardButton("📢 الإعلانات", callback_data="admin_ads")],
        [InlineKeyboardButton("⚙️ إعدادات البوت", callback_data="admin_settings")],
    ])


def admin_templates_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة قالب", callback_data="admin_add_template")],
        [InlineKeyboardButton("🗑 حذف قالب", callback_data="admin_delete_template")],
        [InlineKeyboardButton("📂 عرض القوالب", callback_data="admin_view_templates")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="admin_back")],
    ])


def admin_forcesub_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة قناة أو قروب", callback_data="admin_add_channel")],
        [InlineKeyboardButton("🗑 حذف قناة أو قروب", callback_data="admin_delete_channel")],
        [InlineKeyboardButton("📂 عرض القنوات والقروبات", callback_data="admin_view_channels")],
        [InlineKeyboardButton("✏️ تعديل رسالة الاشتراك", callback_data="admin_edit_forcesub_msg")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="admin_back")],
    ])


def admin_texts_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ تعديل رسالة البداية", callback_data="admin_edit_start")],
        [InlineKeyboardButton("✏️ تعديل رسالة طلب الاسم", callback_data="admin_edit_ask_name")],
        [InlineKeyboardButton("✏️ تعديل رسالة أثناء التصميم", callback_data="admin_edit_designing")],
        [InlineKeyboardButton("✏️ تعديل رسالة إرسال البطاقة", callback_data="admin_edit_card_ready")],
        [InlineKeyboardButton("🔘 إدارة الأزرار", callback_data="admin_buttons")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="admin_back")],
    ])


def admin_buttons_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة زر", callback_data="admin_add_button")],
        [InlineKeyboardButton("🗑 حذف زر", callback_data="admin_delete_button")],
        [InlineKeyboardButton("📂 عرض الأزرار", callback_data="admin_view_buttons")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="admin_texts")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_back")],
    ])


def admin_ads_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📨 إذاعة للمستخدمين", callback_data="admin_broadcast_users")],
        [InlineKeyboardButton("📢 إذاعة للقنوات", callback_data="admin_broadcast_channels")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="admin_back")],
    ])


def admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ رجوع", callback_data="admin_back")]
    ])


def template_delete_keyboard(templates: list) -> InlineKeyboardMarkup:
    rows = []
    for t in templates:
        rows.append([InlineKeyboardButton(
            f"🗑 قالب #{t['id']}",
            callback_data=f"admin_del_tpl_{t['id']}"
        )])
    rows.append([InlineKeyboardButton("⬅️ رجوع", callback_data="admin_templates")])
    return InlineKeyboardMarkup(rows)


def channel_delete_keyboard(channels: list) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        label = ch.get("channel_title") or ch.get("channel_username", "")
        rows.append([InlineKeyboardButton(
            f"🗑 {label}",
            callback_data=f"admin_del_ch_{ch['id']}"
        )])
    rows.append([InlineKeyboardButton("⬅️ رجوع", callback_data="admin_forcesub")])
    return InlineKeyboardMarkup(rows)


def button_delete_keyboard(buttons: list) -> InlineKeyboardMarkup:
    rows = []
    for b in buttons:
        rows.append([InlineKeyboardButton(
            f"🗑 {b['label']}",
            callback_data=f"admin_del_btn_{b['id']}"
        )])
    rows.append([InlineKeyboardButton("⬅️ رجوع", callback_data="admin_buttons")])
    return InlineKeyboardMarkup(rows)
