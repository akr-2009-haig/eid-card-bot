import time
from collections import defaultdict

_last_request: dict = defaultdict(float)


def is_rate_limited(user_id: int, seconds: int = 10) -> bool:
    now = time.time()
    last = _last_request[user_id]
    if now - last < seconds:
        return True
    _last_request[user_id] = now
    return False


def reset_rate_limit(user_id: int):
    _last_request[user_id] = 0.0
