from fastapi import HTTPException

from app.queue.redis_client import redis_client


PRIORITY_QUEUE = "taskscale:priority_queue"
MAX_QUEUED_JOBS = 10


def check_backpressure():

    queue_size = redis_client.zcard(PRIORITY_QUEUE)

    if queue_size >= MAX_QUEUED_JOBS:
        raise HTTPException(
            status_code=429,
            detail="System is busy. Too many jobs are waiting."
        )