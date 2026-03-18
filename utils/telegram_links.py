import re


def normalize_channel_input(raw_value: str) -> dict:
    value = (raw_value or "").strip()
    if not value:
        raise ValueError("empty")

    if value.startswith("@"):
        slug = value.lstrip("@")
        return {
            "lookup_value": f"@{slug}",
            "public_username": f"@{slug}",
            "channel_link": f"https://t.me/{slug}",
        }

    if value.startswith("https://t.me/") or value.startswith("http://t.me/"):
        normalized = value.replace("http://", "https://", 1)
        path = normalized.split("https://t.me/", 1)[-1].strip("/")
        if not path:
            raise ValueError("invalid_link")

        if path.startswith("+") or path.startswith("joinchat/"):
            return {
                "lookup_value": normalized,
                "public_username": "",
                "channel_link": normalized,
            }

        slug = path.split("/", 1)[0]
        return {
            "lookup_value": f"@{slug}",
            "public_username": f"@{slug}",
            "channel_link": f"https://t.me/{slug}",
        }

    if re.fullmatch(r"[A-Za-z0-9_]{4,}", value):
        return {
            "lookup_value": f"@{value}",
            "public_username": f"@{value}",
            "channel_link": f"https://t.me/{value}",
        }

    raise ValueError("invalid_link")


def resolve_channel_link(channel: dict) -> str:
    link = (channel.get("channel_link") or "").strip()
    if link:
        return link

    username = (channel.get("channel_username") or "").strip()
    if username.startswith("http://") or username.startswith("https://"):
        return username
    if username.startswith("@"):
        return f"https://t.me/{username.lstrip('@')}"
    return username


def resolve_channel_target(channel: dict):
    chat_id = channel.get("chat_id")
    if chat_id not in ("", None):
        return int(chat_id) if str(chat_id).lstrip("-").isdigit() else chat_id
    return channel.get("channel_username") or resolve_channel_link(channel)
