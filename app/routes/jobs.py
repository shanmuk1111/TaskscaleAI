from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.job import Job
from app.schemas.job import JobCreate

router = APIRouter()


@router.post("/jobs")
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    new_job = Job(
        type=job.type,
        status="QUEUED",
        input=job.input
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    return new_job