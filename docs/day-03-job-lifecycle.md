# Day 3 — Job Lifecycle

## Objective

Understand the lifecycle of a job from creation to completion
or failure.

## What is a Job?

A job represents a unit of work that TaskScale needs to execute.

Each job has a unique ID so that the system can identify and
track it independently.

## Job Information

A job can contain:

- id
- type
- status
- input
- created_at
- started_at
- completed_at

Result and error information will be considered as the system
develops further.

## Job Status

The status represents the current state of a job.

Initial lifecycle:

QUEUED
↓
RUNNING
↓
COMPLETED

If execution fails:

QUEUED
↓
RUNNING
↓
FAILED

## Status vs Result

Status tells us the current state of the job.

Result contains the output produced by the job.

Example:

Status = COMPLETED
Result = resized-image.jpg

## Timestamps

created_at records when the job was created.

started_at records when job processing started.

completed_at records when job processing finished.

These timestamps can be used to understand waiting time,
execution time, and total processing time.

## Worker Failure

If a worker crashes while processing a job, the job could
remain in RUNNING state.

TaskScale will eventually need failure detection and recovery
mechanisms to handle this situation.

## Example

User requests:

Resize image.jpg to 800x600

↓

Job is created

↓

Job becomes QUEUED

↓

Worker starts processing

↓

Job becomes RUNNING

↓

Worker resizes the image

↓

Job becomes COMPLETED

↓

Result is stored and can be returned to the user.

### Overall strucure
        User
        │
        │ Submit job
        ▼
        FastAPI
        │
        │ Create
        ▼
        PostgreSQL
        │
        │ Job = QUEUED
        ▼
        Worker
        │
        │ Start
        ▼
        Job = RUNNING
        │
        │ Execute
        ▼
        ┌───────────────┐
        │               │
        ▼               ▼
        SUCCESS         ERROR
        │               │
        ▼               ▼
        COMPLETED       FAILED