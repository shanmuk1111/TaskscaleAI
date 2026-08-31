from fastapi import APIRouter
from app.schemas.job import JobCreate

router = APIRouter()


@router.post("/jobs")
def create_job(job: JobCreate):
    return {
        "id": 1,
        "type": job.type,
        "status": "QUEUED",
        "input": job.input
    }