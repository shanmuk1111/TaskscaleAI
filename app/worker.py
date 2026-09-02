import time

from app.database.database import SessionLocal
from app.models.job import Job
from app.queue.redis_client import redis_client

print("Worker started")

while True:
    job = None

    try:
        result = redis_client.blpop("taskscale:jobs", timeout=5)

        if result is None:
            print("Worker is waiting for a job...")
            continue

        queue_name, job_id = result
        print(f"Picked up job {job_id} from Redis")

        db = SessionLocal()

        try:
            job = db.query(Job).filter(Job.id == int(job_id)).first()

            if job is None:
                print(f"Job {job_id} was not found in PostgreSQL")
                continue

            job.status = "RUNNING"
            db.commit()

            print(
                f"Job {job.id} is RUNNING "
                f"(attempt {job.retry_count + 1}/{job.max_retries})"
            )

            # --------------------------------
            # Simulate job processing
            # --------------------------------

            # Fail once, then succeed on retry
            if job.input.get("fail_once") and job.retry_count == 0:
                raise Exception("Simulated temporary failure")

            # Always fail
            if job.input.get("force_fail"):
                raise Exception("Simulated permanent failure")

            # Simulate processing time
            time.sleep(5)

            # Job succeeded
            job.result = {
                "message": "Job processed successfully",
                "job_id": job.id,
            }

            job.status = "COMPLETED"
            db.commit()

            print(f"Job {job.id} is COMPLETED")

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
                        f"Retry {job.retry_count}/{job.max_retries}"
                    )

                    # Small delay before retry
                    time.sleep(2)

                    # Put the job back into Redis
                    redis_client.rpush(
                        "taskscale:jobs",
                        str(job.id)
                    )

                    print(f"Job {job.id} added back to Redis")
                else:
                    job.status = "FAILED"
                    job.error = str(e)

                    db.commit()

                    # Add permanently failed job to Dead Letter Queue
                    redis_client.rpush(
                        "taskscale:dead_letters",
                        str(job.id)
                    )

                    print(
                        f"Job {job.id} permanently FAILED "
                        f"after {job.retry_count} attempts"
                    )

                    print(
                        f"Job {job.id} added to Dead Letter Queue"
                    )


        finally:
            db.close()

    except Exception as e:
        print(f"Worker error: {e}")