import time

from sqlalchemy import text

from app.database.database import SessionLocal
from app.queue.redis_client import redis_client


HEARTBEAT_TIMEOUT = 10

STREAM_NAME = "taskscale:job_stream"
GROUP_NAME = "workers"

# Redis considers a message stale after this amount of time.
# 30 seconds gives enough time for normal job processing.
REDIS_PENDING_TIMEOUT_MS = 30_000


print("Worker monitor started", flush=True)


def recover_dead_workers(db):
    """
    Detect workers that stopped sending heartbeats
    and recover their unfinished RUNNING jobs.
    """

    dead_workers = db.execute(
        text("""
            SELECT worker_id
            FROM workers
            WHERE last_heartbeat < CURRENT_TIMESTAMP
                - (:timeout * INTERVAL '1 second')
                AND status = 'ALIVE'
        """),
        {
            "timeout": HEARTBEAT_TIMEOUT
        }
    ).fetchall()

    if not dead_workers:
        print("All workers are healthy", flush=True)

    for worker_row in dead_workers:

        dead_worker_id = worker_row.worker_id

        # Mark worker as DEAD
        db.execute(
            text("""
                UPDATE workers
                SET status = 'DEAD'
                WHERE worker_id = :worker_id
            """),
            {
                "worker_id": dead_worker_id
            }
        )

        print(
            f"Worker {dead_worker_id} marked as DEAD",
            flush=True
        )

        # Find jobs that were running on this worker
        jobs = db.execute(
            text("""
                SELECT id
                FROM jobs
                WHERE worker_id = :worker_id
                AND status = 'RUNNING'
            """),
            {
                "worker_id": dead_worker_id
            }
        ).fetchall()

        # Recover each unfinished job
        for job_row in jobs:

            job_id = job_row.id

            db.execute(
                text("""
                    UPDATE jobs
                    SET status = 'QUEUED',
                        worker_id = NULL
                    WHERE id = :job_id
                """),
                {
                    "job_id": job_id
                }
            )

            # Put recovered job back into Redis Stream
            redis_client.xadd(
                STREAM_NAME,
                {
                    "job_id": str(job_id)
                }
            )

            print(
                f"Recovered job {job_id} "
                f"from dead worker {dead_worker_id}",
                flush=True
            )


def cleanup_stale_redis_messages(db):
    """
    Clean up Redis messages that are still pending
    because an old worker disappeared.

    QUEUED    -> ACK old message + create fresh message
    COMPLETED -> ACK old message
    FAILED    -> ACK old message
    RUNNING   -> leave it alone
    """

    try:
        pending = redis_client.xpending_range(
            STREAM_NAME,
            GROUP_NAME,
            min="-",
            max="+",
            count=100
        )

        if not pending:
            return

        for message in pending:

            message_id = message["message_id"]
            consumer_name = message["consumer"]
            idle_time = message["time_since_delivered"]

            # Ignore messages that are not old enough.
            if idle_time < REDIS_PENDING_TIMEOUT_MS:
                continue

            # Get the job_id from the Redis message.
            stream_messages = redis_client.xrange(
                STREAM_NAME,
                min=message_id,
                max=message_id,
                count=1
            )

            if not stream_messages:
                # Message disappeared from the stream.
                redis_client.xack(
                    STREAM_NAME,
                    GROUP_NAME,
                    message_id
                )

                print(
                    f"ACKed missing Redis message {message_id}",
                    flush=True
                )

                continue

            _, message_data = stream_messages[0]

            job_id = int(message_data["job_id"])

            job = db.execute(
                text("""
                    SELECT id, status
                    FROM jobs
                    WHERE id = :job_id
                """),
                {
                    "job_id": job_id
                }
            ).fetchone()

            if job is None:

                redis_client.xack(
                    STREAM_NAME,
                    GROUP_NAME,
                    message_id
                )

                print(
                    f"ACKed Redis message {message_id} "
                    f"because job {job_id} does not exist",
                    flush=True
                )

                continue

            job_status = job.status

            # -------------------------------------------------
            # COMPLETED / FAILED
            # -------------------------------------------------

            if job_status in ("COMPLETED", "FAILED"):

                redis_client.xack(
                    STREAM_NAME,
                    GROUP_NAME,
                    message_id
                )

                print(
                    f"ACKed stale Redis message {message_id} "
                    f"for job {job_id} ({job_status}) "
                    f"from {consumer_name}",
                    flush=True
                )

            # -------------------------------------------------
            # QUEUED
            # -------------------------------------------------

            elif job_status == "QUEUED":

                # Remove the stale pending message.
                redis_client.xack(
                    STREAM_NAME,
                    GROUP_NAME,
                    message_id
                )

                # Create a fresh message so a normal worker
                # using XREADGROUP(">") can receive it.
                redis_client.xadd(
                    STREAM_NAME,
                    {
                        "job_id": str(job_id)
                    }
                )

                print(
                    f"Requeued stale job {job_id}: "
                    f"old message {message_id} "
                    f"from {consumer_name}",
                    flush=True
                )

            # -------------------------------------------------
            # RUNNING
            # -------------------------------------------------

            elif job_status == "RUNNING":

                # Do not interfere with currently running jobs.
                print(
                    f"Job {job_id} is still RUNNING; "
                    f"leaving Redis message {message_id} untouched",
                    flush=True
                )

    except Exception as e:

        print(
            f"Redis cleanup error: {e}",
            flush=True
        )


while True:

    db = SessionLocal()

    try:

        # ---------------------------------------------
        # 1. Detect dead workers and recover jobs
        # ---------------------------------------------

        recover_dead_workers(db)

        db.commit()

        # ---------------------------------------------
        # 2. Clean stale Redis consumer messages
        # ---------------------------------------------

        cleanup_stale_redis_messages(db)

        db.commit()

    except Exception as e:

        db.rollback()

        print(
            f"Monitor error: {e}",
            flush=True
        )

    finally:

        db.close()

    time.sleep(5)