import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH

ALLOWED_SCHEMA_TABLES = {"channels", "templates"}
ALLOWED_SCHEMA_COLUMNS = {
    "channels": {"channel_link", "chat_id"},
    "templates": {
        "original_filename",
        "placeholder_x",
        "placeholder_y",
        "placeholder_w",
        "placeholder_h",
        "font_size",
        "placeholder_text",
    },
}
ALLOWED_UPDATE_TEMPLATE_FIELDS = ALLOWED_SCHEMA_COLUMNS["templates"]
SCHEMA_TABLE_NAMES = {
    "channels": "channels",
    "templates": "templates",
}
SCHEMA_COLUMN_DEFINITIONS = {
    "channels": {
        "channel_link": "TEXT DEFAULT ''",
        "chat_id": "TEXT DEFAULT ''",
    },
    "templates": {
        "original_filename": "TEXT DEFAULT ''",
        "placeholder_x": "INTEGER",
        "placeholder_y": "INTEGER",
        "placeholder_w": "INTEGER",
        "placeholder_h": "INTEGER",
        "font_size": "INTEGER",
        "placeholder_text": "TEXT DEFAULT ''",
    },
}


def get_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    if table_name not in ALLOWED_SCHEMA_TABLES or column_name not in ALLOWED_SCHEMA_COLUMNS.get(table_name, set()):
        raise ValueError("Unsupported schema lookup")
    safe_table_name = SCHEMA_TABLE_NAMES[table_name]
    # SQLite PRAGMA identifiers cannot be parameterized; this value is selected only from a fixed internal whitelist.
    cursor.execute(f"PRAGMA table_info({safe_table_name})")
    return any(row["name"] == column_name for row in cursor.fetchall())


def _ensure_column(cursor, table_name: str, column_name: str):
    if table_name not in ALLOWED_SCHEMA_TABLES or column_name not in ALLOWED_SCHEMA_COLUMNS.get(table_name, set()):
        raise ValueError("Unsupported schema change")
    safe_table_name = SCHEMA_TABLE_NAMES[table_name]
    safe_definition = SCHEMA_COLUMN_DEFINITIONS[table_name][column_name]
    if not _column_exists(cursor, table_name, column_name):
        # ALTER TABLE identifiers and definitions are taken only from constant internal mappings above.
        cursor.execute(f"ALTER TABLE {safe_table_name} ADD COLUMN {column_name} {safe_definition}")


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_blocked INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_username TEXT NOT NULL,
            channel_title TEXT,
            channel_type TEXT DEFAULT 'channel',
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _ensure_column(cursor, "channels", "channel_link")
    _ensure_column(cursor, "channels", "chat_id")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT NOT NULL,
            file_path TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _ensure_column(cursor, "templates", "original_filename")
    _ensure_column(cursor, "templates", "placeholder_x")
    _ensure_column(cursor, "templates", "placeholder_y")
    _ensure_column(cursor, "templates", "placeholder_w")
    _ensure_column(cursor, "templates", "placeholder_h")
    _ensure_column(cursor, "templates", "font_size")
    _ensure_column(cursor, "templates", "placeholder_text")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_texts (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            url TEXT NOT NULL,
            position INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generated_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            template_id INTEGER,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    default_texts = {
        "start_message": "🌙 أهلاً بك في بوت تصميم بطاقات تهنئة عيد الفطر\n\nيمكنك إنشاء بطاقة تهنئة باسمك خلال ثواني 🎉\n\nاضغط على الزر بالأسفل ثم أرسل اسمك",
        "forcesub_message": "⚠️ لاستخدام البوت يجب الاشتراك في القنوات التالية\n\nبعد الاشتراك اضغط تحقق",
        "ask_name_message": "✏️ أرسل اسمك ليتم تصميم بطاقة التهنئة لك\n\nمثال:\nمحمد\nأحمد\nفاطمة",
        "designing_message": "⏳ جاري تصميم بطاقتك...",
        "card_ready_message": "🎉 مبروك بطاقتك جاهزة\n\n🌙 عيد فطر مبارك",
    }

    for key, value in default_texts.items():
        cursor.execute(
            "INSERT OR IGNORE INTO bot_texts (key, value) VALUES (?, ?)",
            (key, value)
        )

    conn.commit()
    conn.close()


def add_user(user_id: int, username: str, full_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = CASE
                WHEN excluded.username != '' THEN excluded.username
                ELSE users.username
            END,
            full_name = CASE
                WHEN excluded.full_name != '' THEN excluded.full_name
                ELSE users.full_name
            END
        """,
        (user_id, username, full_name)
    )
    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE is_blocked = 0")
    rows = cursor.fetchall()
    conn.close()
    return [r["user_id"] for r in rows]


def get_users_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    row = cursor.fetchone()
    conn.close()
    return row["cnt"] if row else 0


def mark_user_blocked(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def add_channel(
    username: str,
    title: str = "",
    ch_type: str = "channel",
    channel_link: str = "",
    chat_id: str = "",
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO channels (
            channel_username, channel_title, channel_type, channel_link, chat_id
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (username, title, ch_type, channel_link, str(chat_id or ""))
    )
    conn.commit()
    conn.close()


def get_channels():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM channels ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_channel(channel_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
    conn.commit()
    conn.close()


def add_template(
    file_id: str,
    file_path: str = "",
    original_filename: str = "",
    placeholder_x: int | None = None,
    placeholder_y: int | None = None,
    placeholder_w: int | None = None,
    placeholder_h: int | None = None,
    font_size: int | None = None,
    placeholder_text: str = "",
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO templates (
            file_id, file_path, original_filename, placeholder_x, placeholder_y,
            placeholder_w, placeholder_h, font_size, placeholder_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            file_id,
            file_path,
            original_filename,
            placeholder_x,
            placeholder_y,
            placeholder_w,
            placeholder_h,
            font_size,
            placeholder_text,
        )
    )
    last_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return last_id


def get_templates():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM templates ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_template(template_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_template_path(template_id: int, file_path: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE templates SET file_path = ? WHERE id = ?", (file_path, template_id))
    conn.commit()
    conn.close()


def update_template_metadata(template_id: int, metadata: dict):
    fields = {key: value for key, value in metadata.items() if key in ALLOWED_UPDATE_TEMPLATE_FIELDS}
    if not fields:
        return

    ordered_fields = [field for field in SCHEMA_COLUMN_DEFINITIONS["templates"].keys() if field in fields]
    # Column names come from a constant whitelist; only values remain parameterized user data.
    assignments = ", ".join(f"{field} = ?" for field in ordered_fields)
    params = [fields[field] for field in ordered_fields] + [template_id]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE templates SET {assignments} WHERE id = ?", params)
    conn.commit()
    conn.close()


def delete_template(template_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
    row = cursor.fetchone()
    cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()
    return dict(row) if row else None


def get_templates_count():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM templates")
    row = cursor.fetchone()
    conn.close()
    return row["cnt"] if row else 0


def get_text(key: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM bot_texts WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else ""


def set_text(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO bot_texts (key, value) VALUES (?, ?)",
        (key, value)
    )
    conn.commit()
    conn.close()


def add_button(label: str, url: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(MAX(position), -1) + 1 as next_pos FROM bot_buttons")
    row = cursor.fetchone()
    pos = row["next_pos"] if row else 0
    cursor.execute(
        "INSERT INTO bot_buttons (label, url, position) VALUES (?, ?, ?)",
        (label, url, pos)
    )
    conn.commit()
    conn.close()


def get_buttons():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bot_buttons ORDER BY position ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_button(button_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bot_buttons WHERE id = ?", (button_id,))
    conn.commit()
    conn.close()


def log_generated_card(user_id: int, name: str, template_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO generated_cards (user_id, name, template_id) VALUES (?, ?, ?)",
        (user_id, name, template_id)
    )
    conn.commit()
    conn.close()
