from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.job import Job
from app.models.worker import Worker
from app.schemas.job import JobCreate
from app.queue.redis_client import redis_client
from app.rate_limiter import check_rate_limit
from app.backpressure import check_backpressure


router = APIRouter()


@router.post("/jobs")
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    
    check_backpressure()
    
    check_rate_limit("default-client")

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
        priority=job.priority,
        idempotency_key=job.idempotency_key,
        depends_on=job.depends_on,
        dependencies=job.dependencies
    )
    try:
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
    except Exception:
        db.rollback()
        raise
    
    
    # Add the job to the Redis Stream
    redis_client.zadd(
    "taskscale:priority_queue",
    {
        str(new_job.id): -job.priority
    }
)
    return new_job

@router.get("/jobs/stats")
def get_job_stats(db: Session = Depends(get_db)):

    total_jobs = db.query(Job).count()

    queued_jobs = (
        db.query(Job)
        .filter(Job.status == "QUEUED")
        .count()
    )

    running_jobs = (
        db.query(Job)
        .filter(Job.status == "RUNNING")
        .count()
    )

    completed_jobs = (
        db.query(Job)
        .filter(Job.status == "COMPLETED")
        .count()
    )

    failed_jobs = (
        db.query(Job)
        .filter(Job.status == "FAILED")
        .count()
    )

    return {
        "total_jobs": total_jobs,
        "queued_jobs": queued_jobs,
        "running_jobs": running_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs
    }
    
@router.get("/workers/stats")
def get_worker_stats(db: Session = Depends(get_db)):

    total_workers = db.query(Worker).count()

    alive_workers = (
        db.query(Worker)
        .filter(Worker.status == "ALIVE")
        .count()
    )

    dead_workers = (
        db.query(Worker)
        .filter(Worker.status == "DEAD")
        .count()
    )

    return {
        "total_workers": total_workers,
        "alive_workers": alive_workers,
        "dead_workers": dead_workers
    }


@router.get("/jobs/recent")
def get_recent_jobs(db: Session = Depends(get_db)):

    jobs = (
        db.query(Job)
        .order_by(Job.id.desc())
        .limit(10)
        .all()
    )

    return [
        {
            "id": job.id,
            "type": job.type,
            "status": job.status,
            "priority": job.priority,
            "retry_count": job.retry_count,
            "worker_id": job.worker_id,
            "created_at": job.created_at
        }
        for job in jobs
    ]