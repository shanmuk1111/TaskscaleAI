import time

from app.queue.redis_client import redis_client


PRIORITY_QUEUE = "taskscale:priority_queue"
JOB_STREAM = "taskscale:job_stream"


print("Scheduler started")


while True:

    try:
        # Get the highest-priority job
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

        # Move selected job into the worker stream
        message_id = redis_client.xadd(
            JOB_STREAM,
            {
                "job_id": str(job_id)
            }
        )

        print(
            f"Job {job_id} added to Redis Stream "
            f"(message {message_id})"
        )

    except Exception as e:
        print(f"Scheduler error: {e}")
        time.sleep(1)