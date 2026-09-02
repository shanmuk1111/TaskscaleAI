from app.database.database import SessionLocal
from app.models.job import Job
from app.queue.redis_client import redis_client


print("Worker started")


while True:
    job = None

    try:
        # Wait for a job ID from Redis
        result = redis_client.blpop("taskscale:jobs", timeout=5)

        if result is None:
            print("Worker is waiting for a job...")
            continue

        queue_name, job_id = result

        print(f"Picked up job {job_id} from Redis")

        db = SessionLocal()

        try:
            # Find the job in PostgreSQL
            job = db.query(Job).filter(Job.id == int(job_id)).first()

            if job is None:
                print(f"Job {job_id} was not found in PostgreSQL")
                continue

            # Mark job as running
            job.status = "RUNNING"
            db.commit()

            print(f"Job {job.id} is RUNNING")

            # Simulate doing the actual work
            import time
            time.sleep(5)

            # Store result
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
                job.status = "FAILED"
                job.error = str(e)
                db.commit()

            print(f"Job failed: {e}")

        finally:
            db.close()

    except Exception as e:
        print(f"Worker error: {e}")