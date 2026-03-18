import os

DEFAULT_ADMIN_IDS = [123456789]


def _get_int_env(name: str, default: int = 0) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_admin_ids(value: str) -> list[int]:
    ids = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            ids.append(int(item))
        except ValueError:
            continue
    return ids or DEFAULT_ADMIN_IDS.copy()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.getenv("STORAGE_DIR", BASE_DIR)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE").strip()
ADMIN_IDS = _parse_admin_ids(os.getenv("ADMIN_IDS", ",".join(str(admin_id) for admin_id in DEFAULT_ADMIN_IDS)))
API_ID = _get_int_env("API_ID", 0)
API_HASH = os.getenv("API_HASH", "").strip()

DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(STORAGE_DIR, "database", "bot.db"))

TEMPLATES_DIR = os.getenv("TEMPLATES_DIR", os.path.join(STORAGE_DIR, "data", "templates"))
# Font files live in the application directory by default; mutable runtime data uses STORAGE_DIR.
FONTS_DIR = os.getenv("FONTS_DIR", os.path.join(BASE_DIR, "data", "fonts"))
GENERATED_DIR = os.getenv("GENERATED_DIR", os.path.join(STORAGE_DIR, "data", "generated"))

LOG_FILE = os.getenv("LOG_FILE", os.path.join(STORAGE_DIR, "logs", "bot.log"))

FONT_PATH = os.getenv("FONT_PATH", os.path.join(FONTS_DIR, "arabic.ttf"))
FONT_SIZE_NAME = 60
FONT_SIZE_LABEL = 40

TEXT_COLOR = (255, 255, 255)
TEXT_SHADOW_COLOR = (0, 0, 0)

RATE_LIMIT_SECONDS = 10
