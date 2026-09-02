# Day 6 — Redis Job Queue

## Goal

Introduce Redis as the job queue between the FastAPI API and the worker.

The project specification defines Redis as the initial queue/messaging technology and describes the Phase 4 flow as:

API → PostgreSQL → Redis Queue → Worker

The purpose of this step is to stop the worker from repeatedly polling PostgreSQL for queued jobs and instead let the worker wait for jobs from Redis.

What We Built

## 1. Installed Redis on Windows

Because the project is being developed on Windows, Memurai was installed as the Redis-compatible server.

Redis was verified with:

memurai-cli ping

Expected result:

PONG

Result: Passed

## 2. Connected Python to Redis

The Python Redis client was installed in the project's virtual environment.

Python-to-Redis connectivity was tested with:

python -c "import redis; r=redis.Redis(host='localhost', port=6379); print(r.ping())"

Expected result:

True

Result: Passed

## 3. Added Redis Client

Created:

app/queue/redis_client.py

The application connects to Redis on:

localhost:6379

A Redis queue named:

taskscale:jobs

is used.

## 4. Updated Job Creation

The POST /jobs endpoint now:

Creates the job in PostgreSQL.

Commits the job.

Gets the generated job ID.

Pushes the job ID into the Redis queue.

Only the job ID is placed in Redis. PostgreSQL continues to store the complete job information.

### Flow:

        POST /jobs
            ↓
        FastAPI
            ↓
        PostgreSQL
            ↓
        Job created
            ↓
        Redis queue
            ↓
        Job ID

## 5. Updated the Worker

The worker now waits for a job from Redis using a blocking list operation.

Instead of repeatedly asking PostgreSQL:

Do you have a queued job?
    ↓
wait
    ↓
Do you have a queued job?
    ↓
wait

the worker waits for Redis to provide a job ID:

        Worker
           ↓
        Wait for Redis
           ↓
        Redis provides job ID
           ↓
        Worker reads job from PostgreSQL
           ↓
        RUNNING
           ↓
        Process
           ↓
        COMPLETED

## 6. Job Processing

The worker changes the job state:

            QUEUED
              ↓
            RUNNING
              ↓
            COMPLETED

If an exception occurs during processing, the current implementation marks the job as:

FAILED

## Architecture After Day 6

                Client
                  │
                  ▼
              FastAPI API
                  │
                  ├──────────────► PostgreSQL
                  │                 │
                  │                 │ Job details
                  ▼                 │
             Redis Queue             │
           taskscale:jobs            │
                  │                  │
                  ▼                  │
                Worker ◄─────────────┘
                  │
                  ▼
             Process Job
                  │
                  ▼
              PostgreSQL
        RUNNING / COMPLETED / FAILED

Verification

Redis server

memurai-cli ping
→ PONG

Passed

Python Redis connection

redis.ping()
→ True

Passed

End-to-end job test

Created Job 5 with:

{
  "type": "image_resize",
  "input": {
    "width": 800,
    "height": 600,
    "filename": "dog.png"
  }
}

Worker output:

Worker started
Picked up job 5 from Redis
Job 5 is RUNNING
Job 5 is COMPLETED

PostgreSQL verification showed Job 5 as:

COMPLETED

The result was stored successfully:

{
  "job_id": 5,
  "message": "Job processed successfully"
}

Jobs 1–5 were also verified as COMPLETED.

Why Redis Is Used

PostgreSQL is the persistent source of truth for job information.

Redis is used as the fast queue between the API and workers.

This separates two responsibilities:

PostgreSQL
→ Store job data and results

Redis
→ Hold jobs waiting for workers

This matches the project architecture, where Redis is the initial queue/messaging technology and multiple workers can later consume from the same queue.

Important Design Decision

Only the job_id is stored in Redis.

Example:

Redis:
5

The full job remains in PostgreSQL.

This avoids making Redis the source of truth for job data.

Current Limitations

Day 6 is intentionally a basic Redis queue implementation.

The following features are not implemented yet:

Multiple workers

Retry mechanism

Worker heartbeat

Failure detection and recovery

Dead-letter queue

Idempotency

Duplicate execution protection

Backpressure

Priority scheduling

Distributed locking

Advanced acknowledgements

These are later parts of the project roadmap. The project specification explicitly calls for reliability and correctness features after the basic queue is working.

Current Reliability Note

The worker currently uses a Redis blocking list operation. The job is removed from the Redis list when the worker receives it.

Therefore, if the worker crashes after receiving a job but before completing it, this basic implementation does not yet provide automatic job recovery.

This is a known limitation and will be addressed in the later reliability phase.

Day 6 Result

Day 6 successfully introduced Redis into TaskScale AI.

## The working flow is now:

        Create Job
            ↓
        PostgreSQL
            ↓
        Redis Queue
            ↓
        Worker
            ↓
        PostgreSQL
            ↓
        COMPLETED

The end-to-end Redis queue flow has been tested successfully.

Next Step

The next major step is to make the system distributed by running multiple workers against the same Redis queue and testing concurrent job processing.

After that, the project roadmap moves into reliability features such as retries, worker heartbeats, failure detection, recovery, and dead-letter handling.