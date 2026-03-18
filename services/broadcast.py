import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.helpers import logger


async def broadcast_to_users(client, user_ids: list, message) -> tuple[int, int]:
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await message.copy(uid)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"Broadcast failed for {uid}: {e}")
            failed += 1
    return sent, failed


async def broadcast_to_channels(client, channel_usernames: list, message) -> tuple[int, int]:
    sent = 0
    failed = 0
    for ch in channel_usernames:
        try:
            await message.copy(ch)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"Broadcast to channel {ch} failed: {e}")
            failed += 1
    return sent, failed
