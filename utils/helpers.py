import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LOG_FILE

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger("eid_bot")


def is_admin(user_id: int) -> bool:
    from config import ADMIN_IDS
    return user_id in ADMIN_IDS


def get_full_name(user) -> str:
    first_name = getattr(user, "first_name", "") or ""
    last_name = getattr(user, "last_name", "") or ""
    return f"{first_name} {last_name}".strip()


def format_channel_display(ch: dict) -> str:
    title = ch.get("channel_title") or ch.get("channel_username", "")
    username = ch.get("channel_username", "")
    ch_type = ch.get("channel_type", "channel")
    label = "📢 قناة" if ch_type == "channel" else "👥 قروب"
    return f"{label} | {title or username}"
