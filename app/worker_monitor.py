import time

from sqlalchemy import text

from app.database.database import SessionLocal
from app.queue.redis_client import redis_client


HEARTBEAT_TIMEOUT = 10


print("Worker monitor started")


while True:
    db = SessionLocal()

    try:
        # Find workers whose heartbeat has expired
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
            print("All workers are healthy")

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
                f"Worker {dead_worker_id} marked as DEAD"
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

                # Put the recovered job back into Redis Stream
                redis_client.xadd(
                    "taskscale:job_stream",
                    {
                        "job_id": str(job_id)
                    }
                )

                print(
                    f"Recovered job {job_id} "
                    f"from dead worker {dead_worker_id}"
                )

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"Monitor error: {e}")

    finally:
        db.close()

    time.sleep(5)