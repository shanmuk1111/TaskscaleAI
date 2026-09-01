import time

from app.database.database import SessionLocal
from app.models.job import Job


print("Worker started")


while True:
    db = SessionLocal()

    try:
        # Find the oldest queued job
        job = (
            db.query(Job)
            .filter(Job.status == "QUEUED")
            .order_by(Job.id)
            .first()
        )

        if job is None:
            print("Worker is waiting for a job...")
            time.sleep(3)
            continue

        print(f"Picked up job {job.id}")

        # Mark job as running
        job.status = "RUNNING"
        db.commit()

        print(f"Job {job.id} is RUNNING")

        # Simulate doing the actual work
        time.sleep(5)

        # Store a simple result
        job.result = {
            "message": "Job processed successfully",
            "job_id": job.id,
        }

        job.status = "COMPLETED"
        db.commit()

        print(f"Job {job.id} is COMPLETED")

    except Exception as e:
        db.rollback()

        if "job" in locals() and job is not None:
            job.status = "FAILED"
            job.error = str(e)
            db.commit()

        print(f"Job failed: {e}")

    finally:
        db.close()