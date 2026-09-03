from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.job import Job
from app.schemas.job import JobCreate
from app.queue.redis_client import redis_client

router = APIRouter()


@router.post("/jobs")
def create_job(job: JobCreate, db: Session = Depends(get_db)):

    # Check if this idempotency key was already used
    if job.idempotency_key:
        existing_job = (
            db.query(Job)
            .filter(Job.idempotency_key == job.idempotency_key)
            .first()
        )

        if existing_job:
            return existing_job

    new_job = Job(
        type=job.type,
        status="QUEUED",
        input=job.input,
        retry_count=0,
        max_retries=3,
        idempotency_key=job.idempotency_key
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Add the job ID to Redis
    redis_client.rpush(
        "taskscale:jobs",
        str(new_job.id)
    )

    return new_job