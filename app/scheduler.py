import time

from app.queue.redis_client import redis_client
from app.distributed_lock import acquire_lock, release_lock
from app.leader_election import (
    become_leader,
    renew_leadership,
    release_leadership
)


PRIORITY_QUEUE = "taskscale:priority_queue"
JOB_STREAM = "taskscale:job_stream"

print("Scheduler started")

leader_id = None


while True:
    try:
        # Try to become leader if we are not currently leader
        if leader_id is None:
            leader_id = become_leader()

            if leader_id:
                print(f"This scheduler is now LEADER: {leader_id}")
            else:
                print("Another scheduler is currently LEADER")
                time.sleep(2)
                continue

        # Renew leadership
        if not renew_leadership(leader_id):
            print("Leadership lost")
            leader_id = None
            time.sleep(1)
            continue

        # Acquire distributed lock before scheduling
        lock_token = acquire_lock()

        if lock_token is None:
            print("Another scheduler holds the distributed lock")
            time.sleep(1)
            continue

        try:
            result = redis_client.zpopmin(
                PRIORITY_QUEUE,
                count=1
            )

            if not result:
                time.sleep(1)
                continue

            job_id, score = result[0]

            print(
                f"Leader selected job {job_id} "
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

        finally:
            release_lock(lock_token)

    except KeyboardInterrupt:
        print("Scheduler shutting down")

        if leader_id:
            release_leadership(leader_id)
            print("Leadership released")

        break

    except Exception as e:
        print(f"Scheduler error: {e}")
        time.sleep(1)