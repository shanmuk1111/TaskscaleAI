import uuid

from app.queue.redis_client import redis_client


LOCK_KEY = "taskscale:scheduler_lock"
LOCK_TIMEOUT = 10


def acquire_lock():
    lock_token = str(uuid.uuid4())

    acquired = redis_client.set(
        LOCK_KEY,
        lock_token,
        nx=True, ## important
        ex=LOCK_TIMEOUT
    )

    if acquired:
        return lock_token

    return None


def release_lock(lock_token):
    current_token = redis_client.get(LOCK_KEY)

    if current_token == lock_token:
        redis_client.delete(LOCK_KEY)
        return True

    return False