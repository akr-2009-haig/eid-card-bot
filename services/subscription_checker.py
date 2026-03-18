import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.telegram_links import resolve_channel_target


async def check_subscription(client, user_id: int, channels: list) -> tuple[bool, list]:
    not_subscribed = []
    for ch in channels:
        target = resolve_channel_target(ch)
        try:
            member = await client.get_chat_member(target, user_id)
            status = member.status.value if hasattr(member.status, "value") else str(member.status)
            if status in ("left", "banned", "kicked", "restricted"):
                not_subscribed.append(ch)
        except Exception:
            not_subscribed.append(ch)
    return len(not_subscribed) == 0, not_subscribed
