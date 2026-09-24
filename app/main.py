from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

import app.metrics

from app.models.job import Job
from app.models.worker import Worker
from app.routes.jobs import router as jobs_router
from app.database.database import Base, engine


app = FastAPI(title="TaskScale AI")

Base.metadata.create_all(bind=engine)

app.include_router(jobs_router)


# Allow React frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "TaskScale AI is running"}


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )