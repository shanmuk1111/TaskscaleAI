# Day 2 — TaskScale AI Architecture

## Objective

Understand the major components of TaskScale AI and how they
work together to process jobs.

## Main Components

### User

The user submits a task to TaskScale AI.

### FastAPI

FastAPI receives the user's request and creates a job.

### PostgreSQL

PostgreSQL provides persistent storage for job and system
information, including job status and results.

### Scheduler

The scheduler manages which jobs should be processed and
manages job assignment.

### Redis

Redis is used as the queue/messaging system where jobs can
wait to be processed.

### Worker

A worker is the program that actually executes the job.


### Flow 
         TASKSCALE

       User
        │
        ▼
       FastAPI
        │
        ├──────────────→ PostgreSQL
        │                   │
        │                   │ job information
        │                   │
        ▼                   │
       Scheduler            │
        │                   │
        ▼                   │
       Redis Queue          v
        │                   │
        ├──────┬──────┐     │
        ▼      ▼      ▼     │
       W1      W2     W3    │
        │      │      │     │
        └──────┴──────┴─────┘
                  │
                  ▼
              PostgreSQL
                  │
                  ▼
                Result
       
## Basic Job Flow

User
↓
FastAPI
↓
PostgreSQL
↓
Scheduler
↓
Redis
↓
Worker
↓
PostgreSQL
↓
Result

## Important Distinctions

Job = work that needs to be done.

Worker = program that executes the work.

PostgreSQL = persistent storage.

Redis = queue/messaging system.

Scheduler = manages which work should be processed.

## Example

For an image-resizing job:

User requests image resizing.
↓
FastAPI receives the request.
↓
A job is created.
↓
Job information is stored in PostgreSQL.
↓
The job enters the processing system.
↓
A worker receives the job.
↓
The worker resizes the image.
↓
The result and job status are stored.

## Why We Build Incrementally

The project starts with a simple system consisting of:

FastAPI
+
PostgreSQL
+
One Worker

After the basic system works, we will introduce Redis,
multiple workers, retries, recovery, and other distributed
system features.