from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.job import Job
from app.models.worker import Worker
from app.schemas.job import JobCreate
from app.rate_limiter import check_rate_limit
from app.backpressure import check_backpressure
from app.queue.redis_client import redis_client
from sqlalchemy import func


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
    
        # Calculate worker utilization
    alive_workers = (
        db.query(Worker)
        .filter(Worker.status == "ALIVE")
        .count()
    )

    if alive_workers > 0:
        worker_utilization = (
            running_jobs / alive_workers
        ) * 100
    else:
        worker_utilization = 0
    
        # Calculate total retries
    total_retries = db.query(
        func.coalesce(func.sum(Job.retry_count), 0)
    ).scalar()

    # Calculate average job latency
    average_latency = db.query(
        func.avg(
            func.extract(
                "epoch",
                Job.completed_at - Job.created_at
            )
        )
    ).filter(
        Job.status == "COMPLETED",
        Job.completed_at.isnot(None)
    ).scalar()

    # Current jobs waiting in Redis priority queue
    queue_size = redis_client.zcard(
        "taskscale:priority_queue"
    )

    # Calculate success rate
    finished_jobs = completed_jobs + failed_jobs

    if finished_jobs > 0:
        success_rate = (
            completed_jobs / finished_jobs
        ) * 100
    else:
        success_rate = 0

    return {
        "total_jobs": total_jobs,
        "queued_jobs": queued_jobs,
        "running_jobs": running_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "queue_size": queue_size,
        "success_rate": round(success_rate, 2),
        "average_latency_seconds": (
            round(float(average_latency), 2)
            if average_latency
            else 0
        ),
        "total_retries": int(total_retries),
        "worker_utilization": round(worker_utilization, 2)
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


@router.get("/workers")
def get_workers(db: Session = Depends(get_db)):

    workers = (
        db.query(Worker)
        .order_by(Worker.worker_id)
        .all()
    )

    result = []

    for worker in workers:

        running_jobs = (
            db.query(Job)
            .filter(
                Job.worker_id == worker.worker_id,
                Job.status == "RUNNING"
            )
            .count()
        )

        completed_jobs = (
            db.query(Job)
            .filter(
                Job.worker_id == worker.worker_id,
                Job.status == "COMPLETED"
            )
            .count()
        )

        failed_jobs = (
            db.query(Job)
            .filter(
                Job.worker_id == worker.worker_id,
                Job.status == "FAILED"
            )
            .count()
        )

        result.append({
            "worker_id": worker.worker_id,
            "status": worker.status,
            "last_heartbeat": worker.last_heartbeat,
            "running_jobs": running_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs
        })

    return {
        "workers": result,
        "total": len(result)
    }

@router.get("/queue")
def get_queue(db: Session = Depends(get_db)):

    queued_jobs = (
        db.query(Job)
        .filter(Job.status == "QUEUED")
        .order_by(Job.priority.desc(), Job.id.asc())
        .all()
    )

    return {
        "queue_size": redis_client.zcard(
            "taskscale:priority_queue"
        ),
        "jobs": [
            {
                "id": job.id,
                "type": job.type,
                "status": job.status,
                "priority": job.priority,
                "retry_count": job.retry_count,
                "created_at": job.created_at
            }
            for job in queued_jobs
        ]
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

@router.get("/jobs")
def get_jobs(
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100)
):
    query = db.query(Job)

    # Filter by status
    if status:
        query = query.filter(Job.status == status.upper())

    # Search by job type
    if search:
        query = query.filter(
            Job.type.ilike(f"%{search}%")
        )

    # Total matching jobs
    total = query.count()

    # Pagination
    offset = (page - 1) * limit

    jobs = (
        query
        .order_by(Job.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "jobs": [
            {
                "id": job.id,
                "type": job.type,
                "status": job.status,
                "priority": job.priority,
                "retry_count": job.retry_count,
                "worker_id": job.worker_id,
                "created_at": job.created_at,
                "completed_at": job.completed_at,
                "error": job.error
            }
            for job in jobs
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (
            (total + limit - 1) // limit
            if total > 0
            else 0
        )
    }
    
@router.get("/workflows")
def get_workflows(db: Session = Depends(get_db)):

    jobs = (
        db.query(Job)
        .order_by(Job.id.asc())
        .all()
    )

    return [
        {
            "id": job.id,
            "type": job.type,
            "status": job.status,
            "priority": job.priority,
            "dependencies": job.dependencies,
            "depends_on": job.depends_on,
            "created_at": job.created_at
        }
        for job in jobs
    ]