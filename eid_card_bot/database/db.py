import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH


def get_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT NOT NULL,
            file_path TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

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
        "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
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


def add_channel(username: str, title: str = "", ch_type: str = "channel"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO channels (channel_username, channel_title, channel_type) VALUES (?, ?, ?)",
        (username, title, ch_type)
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


def add_template(file_id: str, file_path: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO templates (file_id, file_path) VALUES (?, ?)",
        (file_id, file_path)
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


def delete_template(template_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM templates WHERE id = ?", (template_id,))
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
