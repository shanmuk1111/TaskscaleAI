import time

from fastapi import HTTPException
from app.queue.redis_client import redis_client


RATE_LIMIT = 5
WINDOW_SECONDS = 60


def check_rate_limit(client_id: str):

    key = f"taskscale:rate_limit:{client_id}"

    current_count = redis_client.get(key)

    if current_count is None:
        redis_client.set(
            key,
            1,
            ex=WINDOW_SECONDS
        )
        return

    current_count = int(current_count)

    if current_count >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later."
        )

    redis_client.incr(key)