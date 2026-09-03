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
        result = redis_client.xreadgroup(
        groupname="workers",
        consumername=worker_id,
        streams={"taskscale:job_stream": ">"},
        count=1,
        block=5000
        )

        if not result:
            print("Worker is waiting for a job...")
            continue

        stream_name, messages = result[0]

        for message_id, message_data in messages:
            job_id = int(message_data["job_id"])

            print(
                f"Worker {worker_id} picked up job {job_id} "
                f"(message {message_id})"
            )

            db = SessionLocal()
            job = None

            try:
                job = db.query(Job).filter(Job.id == job_id).first()

                if job is None:
                    print(f"Job {job_id} was not found in PostgreSQL")

                    redis_client.xack(
                        "taskscale:job_stream",
                        "workers",
                        message_id
                    )

                    continue

                # Assign this job to the current worker
                job.worker_id = worker_id
                job.status = "RUNNING"
                db.commit()

                print(f"Job {job.id} is RUNNING")

                # --------------------------------
                # Simulate job processing
                # --------------------------------

                if job.input.get("fail_once") and job.retry_count == 0:
                    raise Exception("Simulated temporary failure")

                if job.input.get("force_fail"):
                    raise Exception("Simulated permanent failure")

                time.sleep(5)

                # --------------------------------
                # Job succeeded
                # --------------------------------

                job.result = {
                    "message": "Job processed successfully",
                    "job_id": job.id,
                    "worker_id": worker_id
                }

                job.status = "COMPLETED"
                db.commit()

                # ACK only after successful processing
                redis_client.xack(
                    "taskscale:job_stream",
                    "workers",
                    message_id
                )

                print(
                    f"Job {job.id} is COMPLETED"
                )

                print(
                    f"ACK sent for job {job.id}"
                )

            except Exception as e:

                db.rollback()

                if job is not None:

                    job.retry_count += 1
                    job.error = str(e)

                    if job.retry_count < job.max_retries:

                        job.status = "RETRYING"
                        db.commit()

                        print(
                            f"Job {job.id} failed. "
                            f"Retry {job.retry_count}/{job.max_retries}"
                        )

                        time.sleep(2)

                        # Put retry into the Stream
                        redis_client.xadd(
                            "taskscale:job_stream",
                            {
                                "job_id": str(job.id)
                            }
                        )

                        # ACK the failed attempt
                        redis_client.xack(
                            "taskscale:job_stream",
                            "workers",
                            message_id
                        )

                        print(
                            f"Job {job.id} added back to Redis Stream"
                        )

                    else:

                        job.status = "FAILED"
                        db.commit()

                        # Put permanently failed job into DLQ
                        redis_client.rpush(
                            "taskscale:dead_letters",
                            str(job.id)
                        )

                        # ACK the original Stream message
                        redis_client.xack(
                            "taskscale:job_stream",
                            "workers",
                            message_id
                        )

                        print(
                            f"Job {job.id} permanently FAILED"
                        )

                        print(
                            f"Job {job.id} added to Dead Letter Queue"
                        )

            finally:
                db.close()

    except Exception as e:
        print(f"Worker error: {e}")