# Day 10 --- Idempotency and Duplicate Job Protection

## Goal

Day 10 introduces **idempotency** as the first correctness feature of
TaskScale AI.

The TaskScale AI specification identifies idempotency and duplicate
execution protection as part of **Phase 4 --- Correctness**. It also
describes duplicate execution as a failure scenario that must be handled
with appropriate idempotency and job-state mechanisms.

## 1. The Problem

In a distributed system, the same logical operation can sometimes be
submitted or executed more than once.

Example:

``` text
Client
  ↓
Submit Job A
  ↓
Worker processes Job A
  ↓
Network/worker failure
  ↓
Job may be submitted or processed again
```

Without protection, the system could create duplicate jobs.

TaskScale AI must prevent unwanted duplicate execution.

## 2. What Is an Idempotency Key?

An idempotency key is a unique value supplied by the client to identify
one logical operation.

Example:

``` text
test-key-001
```

If the client submits the same key again, TaskScale can recognize that
the logical operation already exists.

The flow is:

``` text
Request
   ↓
Idempotency Key
   ↓
Check PostgreSQL
   ↓
Already exists?
   ├── YES → Return existing job
   └── NO  → Create new job
```

## 3. Database Change

A new column was added to the `jobs` table:

``` sql
idempotency_key VARCHAR(255)
```

A partial unique index was created:

``` sql
CREATE UNIQUE INDEX jobs_idempotency_key_unique
ON jobs (idempotency_key)
WHERE idempotency_key IS NOT NULL;
```

This means:

``` text
NULL         → allowed
test-key-001 → allowed once
test-key-001 → duplicate
test-key-002 → allowed
```

The unique index provides database-level protection against duplicate
non-null keys.

## 4. SQLAlchemy Model

The `Job` model was updated with:

``` python
idempotency_key = Column(String(255), nullable=True)
```

The model test confirmed that SQLAlchemy recognizes the new field.

## 5. API Schema

The `JobCreate` schema was updated to accept an optional idempotency
key:

``` python
idempotency_key: Optional[str] = None
```

This keeps the key optional and maintains compatibility with requests
that do not provide one.

## 6. Job Creation

The API now stores the supplied idempotency key:

``` python
new_job = Job(
    type=job.type,
    status="QUEUED",
    input=job.input,
    retry_count=0,
    max_retries=3,
    idempotency_key=job.idempotency_key
)
```

## 7. Duplicate Request Handling

Before creating a new job, the API checks PostgreSQL:

``` python
if job.idempotency_key:
    existing_job = (
        db.query(Job)
        .filter(Job.idempotency_key == job.idempotency_key)
        .first()
    )

    if existing_job:
        return existing_job
```

Therefore:

``` text
First request
     ↓
test-key-001
     ↓
Create Job 49
```

A second request with the same key:

``` text
Second request
     ↓
test-key-001
     ↓
Find Job 49
     ↓
Return Job 49
```

No new job is created by the duplicate request.

## 8. Testing

A job was created using:

``` json
{
  "type": "idempotency_test",
  "input": {
    "message": "testing idempotency"
  },
  "idempotency_key": "test-key-001"
}
```

The original request created Job 49.

Submitting the same idempotency key again returned the previously stored
job instead of creating another job.

A separate key, `test-key-002`, correctly created a different job.

## 9. Result

``` text
                 Request
                    ↓
             idempotency_key
                    ↓
          ┌──────────────────┐
          │ Existing key?    │
          └────────┬─────────┘
              YES  │  NO
               ↓  │   ↓
      Existing Job │ Create Job
                   │
                   ↓
              Redis Queue
```

Day 10 successfully demonstrates basic idempotency at the API/database
level.

## 10. Important Limitation

This implementation should **not** be described as full exactly-once
execution.

The project specification explains that duplicate execution is more
complicated in distributed systems. The system still has further
correctness work to implement, including acknowledgements, stronger
duplicate-execution protection, database transactions, and
race-condition handling.

## 11. What Was Learned

Day 10 demonstrated:

-   Why duplicate operations are a problem.
-   What an idempotency key is.
-   How PostgreSQL unique indexes can enforce uniqueness.
-   How the API can return an existing job for a repeated key.
-   Why database-level constraints are important.
-   Why idempotency does not automatically mean exactly-once execution.

## Result

``` text
Day 10
  ↓
Idempotency Key
  ↓
PostgreSQL Unique Index
  ↓
Existing-Key Detection
  ↓
Existing Job Returned
  ↓
Unwanted Duplicate Job Prevented
```

**Day 10 completed: Basic idempotency and duplicate job protection.**
