import time
import uuid
import threading

from app.database.database import SessionLocal
from app.models.job import Job
from app.models.worker import Worker
from app.queue.redis_client import redis_client


# --------------------------------
# Worker identity
# --------------------------------

worker_id = f"worker-{uuid.uuid4().hex[:8]}"

print(f"Worker started: {worker_id}")


# --------------------------------
# Register worker
# --------------------------------

db = SessionLocal()

try:
    worker = Worker(
        worker_id=worker_id,
        status="ALIVE"
    )

    db.add(worker)
    db.commit()

    print(f"Worker {worker_id} registered")

finally:
    db.close()


# --------------------------------
# Heartbeat function
# --------------------------------

def send_heartbeat():
    while True:
        db = SessionLocal()

        try:
            worker = (
                db.query(Worker)
                .filter(Worker.worker_id == worker_id)
                .first()
            )

            if worker:
                worker.last_heartbeat = func.now()
                worker.status = "ALIVE"

                db.commit()

                print(f"Heartbeat sent: {worker_id}")

        except Exception as e:
            db.rollback()
            print(f"Heartbeat error: {e}")

        finally:
            db.close()

        time.sleep(3)


# --------------------------------
# Start heartbeat thread
# --------------------------------

from sqlalchemy.sql import func

heartbeat_thread = threading.Thread(
    target=send_heartbeat,
    daemon=True
)

heartbeat_thread.start()


# --------------------------------
# Job processing
# --------------------------------

while True:
    job = None

    try:
        result = redis_client.blpop(
            "taskscale:jobs",
            timeout=5
        )

        if result is None:
            print("Worker is waiting for a job...")
            continue

        queue_name, job_id = result

        print(
            f"Worker {worker_id} picked up "
            f"job {job_id} from Redis"
        )

        db = SessionLocal()

        try:
            job = (
                db.query(Job)
                .filter(Job.id == int(job_id))
                .first()
            )

            if job is None:
                print(
                    f"Job {job_id} was not found "
                    f"in PostgreSQL"
                )
                continue

            job.status = "RUNNING"
            job.worker_id = worker_id
            db.commit()

            print(
                f"Job {job.id} is RUNNING "
                f"(attempt {job.retry_count + 1}/"
                f"{job.max_retries})"
            )

            # --------------------------------
            # Simulate job processing
            # --------------------------------

            # Fail once, then succeed on retry
            if (
                job.input.get("fail_once")
                and job.retry_count == 0
            ):
                raise Exception(
                    "Simulated temporary failure"
                )

            # Always fail
            if job.input.get("force_fail"):
                raise Exception(
                    "Simulated permanent failure"
                )

            # Simulate processing time
            time.sleep(5)

            # --------------------------------
            # Job succeeded
            # --------------------------------

            job.result = {
                "message": "Job processed successfully",
                "job_id": job.id,
            }

            job.status = "COMPLETED"

            db.commit()

            print(
                f"Job {job.id} is COMPLETED"
            )

        except Exception as e:
            db.rollback()

            if job is not None:
                job.retry_count += 1

                if job.retry_count < job.max_retries:

                    job.status = "RETRYING"
                    job.error = str(e)

                    db.commit()

                    print(
                        f"Job {job.id} failed. "
                        f"Retry "
                        f"{job.retry_count}/"
                        f"{job.max_retries}"
                    )

                    # Small delay before retry
                    time.sleep(2)

                    # Put job back into Redis
                    redis_client.rpush(
                        "taskscale:jobs",
                        str(job.id)
                    )

                    print(
                        f"Job {job.id} added "
                        f"back to Redis"
                    )

                else:

                    job.status = "FAILED"
                    job.error = str(e)

                    db.commit()

                    # Add permanently failed job
                    # to Dead Letter Queue
                    redis_client.rpush(
                        "taskscale:dead_letters",
                        str(job.id)
                    )

                    print(
                        f"Job {job.id} permanently "
                        f"FAILED after "
                        f"{job.retry_count} attempts"
                    )

                    print(
                        f"Job {job.id} added "
                        f"to Dead Letter Queue"
                    )

        finally:
            db.close()

    except Exception as e:
        print(f"Worker error: {e}")