# Day -05 PostgreSQL + Worker Processing

## 1. Installed PostgreSQL

We installed PostgreSQL and verified it:

psql (PostgreSQL) 18.6

Then we connected to PostgreSQL using:

psql -U postgres

## 2. Created the TaskScale database

We created:

CREATE DATABASE taskscale;

Then connected to it:

\c taskscale

## 3. Created the jobs table

The table stores the complete lifecycle of a job.

It contains:

id
type
status
input
result
error
created_at
updated_at

The important idea is:

The database remembers what happened to every job.

## 4. Connected Python to PostgreSQL

We created:

app/database/database.py

This uses SQLAlchemy to connect the FastAPI application to PostgreSQL.

The basic structure is:

FastAPI
   ↓
SQLAlchemy
   ↓
PostgreSQL

## 5. Created the Job model

We created:

app/models/job.py

The Job model represents the jobs table in Python.

It contains fields for:

Job ID
Job type
Job status
Input
Result
Error
Created time
Updated time

## 6. Created the Worker

We created:

app/worker.py

The worker continuously waits for jobs.

Initially it simply printed:

Worker started
Worker is waiting for a job...

Then we connected it to the database so it could actually find and process queued jobs.

## Day 5 Workflow

This is the most important part.

The TaskScale AI workflow is now:

        User/API
            ↓
        Create Job
            ↓
        PostgreSQL
            ↓
        Job stored as QUEUED
            ↓
        Worker checks database
            ↓
        Worker finds QUEUED job
            ↓
        Worker processes job
            ↓
        Worker updates job
            ↓
        PostgreSQL
            ↓
        Job becomes COMPLETED
            ↓
        Result is stored

            
Example from our test

We sent:

{
  "type": "image_resize",
  "input": {
    "width": 800,
    "height": 600,
    "filename": "dog.png"
  }
}

The job was initially:

QUEUED

The worker processed it.

Then PostgreSQL showed:

COMPLETED

And the result contained:

{
  "job_id": 4,
  "message": "Job processed successfully"
}

We also tested multiple jobs, and the database showed:

1 | image_resize | COMPLETED
2 | image_resize | COMPLETED
3 | image_resize | COMPLETED
4 | image_resize | COMPLETED

So Day 5 is successfully working end-to-end. ✅