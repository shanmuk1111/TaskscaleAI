import time

from app.queue.redis_client import redis_client
from app.distributed_lock import acquire_lock, release_lock


PRIORITY_QUEUE = "taskscale:priority_queue"
JOB_STREAM = "taskscale:job_stream"

print("Scheduler started")


while True:
    lock_token = None

    try:
        lock_token = acquire_lock()

        if lock_token is None:
            print("Another scheduler holds the lock")
            time.sleep(1)
            continue

        result = redis_client.zpopmin(
            PRIORITY_QUEUE,
            count=1
        )

        if not result:
            time.sleep(1)
            continue

        job_id, score = result[0]

        print(
            f"Scheduler selected job {job_id} "
            f"with priority score {score}"
        )

        message_id = redis_client.xadd(
            JOB_STREAM,
            {"job_id": str(job_id)}
        )

        print(
            f"Job {job_id} added to Redis Stream "
            f"(message {message_id})"
        )

    except Exception as e:
        print(f"Scheduler error: {e}")
        time.sleep(1)

    finally:
        if lock_token is not None:
            release_lock(lock_token)