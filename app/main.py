from fastapi import FastAPI
from app.routes.jobs import router as jobs_router

app = FastAPI(title="TaskScale AI")


@app.get("/")
def root():
    return {"message": "TaskScale AI is running"}


app.include_router(jobs_router)