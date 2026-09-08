from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.job import Job
from app.routes.jobs import router as jobs_router
from app.database.database import Base, engine
from app.models.worker import Worker

app = FastAPI(title="TaskScale AI")




Base.metadata.create_all(bind=engine)


app = FastAPI()

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


app.include_router(jobs_router)