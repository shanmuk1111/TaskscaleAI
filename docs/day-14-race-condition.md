# Day 14 — Race-Condition Handling

## Objective

Understand and implement protection against race conditions when multiple workers try to process the same job at the same time.

The main goals were:

- Understand race conditions in a multi-worker system
- Prevent two workers from claiming the same job
- Use an atomic database update for job claiming
- Verify that only one worker can change `QUEUED` → `RUNNING`
- Test the behavior with two workers
- Verify Redis acknowledgements after the test

---

# 1. What is a Race Condition?

A race condition can happen when two workers try to modify or process the same job at nearly the same time.

Without protection:

    Job = QUEUED
         ↓
    ┌────┴────┐
    ↓         ↓
 Worker A  Worker B
    ↓         ↓
  RUNNING   RUNNING
    ↓         ↓
 Process the same job twice

This can cause duplicate execution and inconsistent job ownership.

---

# 2. Race-Condition Protection

TaskScale uses an atomic database claim.

The worker attempts to update the job only when its current status is `QUEUED`:

```python
claim_result = (
    db.query(Job)
    .filter(
        Job.id == job.id,
        Job.status == "QUEUED"
    )
    .update(
        {
            Job.worker_id: worker_id,
            Job.status: "RUNNING"
        },
        synchronize_session=False
    )
)

db.commit()
```

The important condition is:

```python
Job.status == "QUEUED"
```

The database performs the condition and update as one database operation.

---

# 3. Claim Result

The worker checks the number of rows updated:

```python
if claim_result == 0:
    print(
        f"Job {job.id} could not be claimed. "
        f"Another worker may already own it."
    )
```

If the result is `1`:

```text
Job was successfully claimed.
```

If the result is `0`:

```text
Job was not claimed because another worker
already changed its state.
```

This prevents the second worker from processing the same job.

---

# 4. Two Worker Test

Two workers were started at the same time.

Worker 1:

```text
worker-e2e3939c
```

Worker 2:

```text
worker-2abe440d
```

Both workers were registered and sending heartbeats.

---

# 5. Race-Condition Test

A new job was created for the test.

The job ID was:

```text
78
```

A duplicate Redis Stream message for Job 78 was also added intentionally so that two workers could attempt to process the same job.

The purpose was to create a controlled race:

    Job 78 = QUEUED
          ↓
   ┌──────┴──────┐
   ↓             ↓
Worker A      Worker B
   ↓             ↓
 Claim         Claim
   ↓             ↓
SUCCESS         0 rows
   ↓             ↓
RUNNING        Rejected
   ↓
COMPLETED

---

# 6. Successful Worker

Worker `worker-e2e3939c` successfully claimed Job 78.

The worker output showed:

```text
Worker worker-e2e3939c picked up job 78
Job 78 is RUNNING
Job 78 is COMPLETED
ACK sent for job 78
```

This confirmed that one worker successfully owned and processed the job.

---

# 7. Second Worker Attempt

Worker `worker-2abe440d` also received a message for Job 78.

Its output showed:

```text
Worker worker-2abe440d picked up job 78
Job 78 could not be claimed. Another worker may already own it.
```

The second worker was therefore prevented from changing the already-owned job from `QUEUED` to `RUNNING`.

This is the key evidence that the atomic database claim protected the job from concurrent execution.

---

# 8. PostgreSQL Result

The completed job was verified in PostgreSQL.

The job had:

```text
id       = 78
status   = COMPLETED
worker   = worker-e2e3939c
```

The job was processed by one worker and completed successfully.

The `worker_id` field showed the worker that successfully claimed the job.

---

# 9. Redis Pending Message

After the race test, one duplicate Stream message remained pending.

The pending message was inspected using:

```text
XPENDING taskscale:job_stream workers - + 10
```

The pending message belonged to:

```text
worker-2abe440d
```

The message was then inspected using:

```text
XRANGE taskscale:job_stream 1788687001350-0 1788687001350-0
```

The result confirmed:

```text
job_id = 78
```

This was the duplicate message associated with the rejected claim attempt.

---

# 10. Redis ACK Cleanup

The duplicate message was acknowledged using:

```text
XACK taskscale:job_stream workers 1788687001350-0
```

Redis returned:

```text
(integer) 1
```

This confirmed that the pending message was successfully acknowledged.

---

# 11. Final Redis Verification

The pending messages were checked again:

```text
XPENDING taskscale:job_stream workers
```

The final result was:

```text
(integer) 0
```

This confirmed that there were no remaining pending messages after the test.

---

# 12. What the Test Proved

The test demonstrated the following behavior:

    Worker A
       ↓
    Claims Job 78
       ↓
    RUNNING
       ↓
    COMPLETED

    Worker B
       ↓
    Attempts same job
       ↓
    Database condition:
    status = QUEUED
       ↓
    0 rows updated
       ↓
    Claim rejected

Therefore, two workers could not both successfully claim the same job.

---

# 13. Why the Database Check is Important

The Redis Stream can deliver messages to workers, but PostgreSQL is responsible for protecting the job state.

The important transition is:

```text
QUEUED → RUNNING
```

The worker is allowed to make this transition only when the job is still `QUEUED`.

Once another worker changes the job to `RUNNING`, the second worker cannot successfully claim it.

This provides database-level protection against concurrent job ownership.

---

# 14. Relationship With Previous Correctness Features

Day 14 builds on the correctness features implemented previously.

The overall protection is:

    Idempotency
         ↓
    Redis Stream
         ↓
    Consumer Group
         ↓
    Duplicate Execution Protection
         ↓
    Atomic Database Claim
         ↓
    Single Worker Ownership
         ↓
    Job Processing
         ↓
    COMPLETED
         ↓
    XACK

Each part handles a different correctness problem.

---

# 15. What I Learned

By the end of Day 14:

A race condition can occur when multiple workers try to process the same job.

Checking the job status before updating it is not enough if the check and update are separate operations.

The database can perform the conditional update atomically.

The `QUEUED` → `RUNNING` transition is protected by checking the current status inside the database update.

`claim_result == 1` means the worker successfully claimed the job.

`claim_result == 0` means the worker could not claim the job.

The `worker_id` field records which worker owns the running job.

Redis Stream messages still need to be acknowledged after they are safely handled.

---

# 16. Day 14 Testing

## Test 1 — Two Workers

Result:

```text
Worker 1 → ALIVE
Worker 2 → ALIVE
```

Status:

```text
PASS
```

## Test 2 — Same Job Race

Result:

```text
Worker A → Job 78 → RUNNING → COMPLETED
Worker B → Job 78 → claim rejected
```

Status:

```text
PASS
```

## Test 3 — Redis Pending Message

Result:

```text
Pending message found and identified as Job 78
```

Status:

```text
PASS
```

## Test 4 — Redis ACK

Result:

```text
XACK returned (integer) 1
```

Status:

```text
PASS
```

## Test 5 — Final Pending Check

Result:

```text
XPENDING taskscale:job_stream workers
(integer) 0
```

Status:

```text
PASS
```

---

# 17. Day 14 Status

Race-Condition Handling
        ↓
Understanding        ✅
Atomic Job Claim     ✅
Two Worker Test      ✅
Race Test            ✅
PostgreSQL Verify    ✅
Redis ACK Verify     ✅
Pending Check        ✅

**Day 14 — COMPLETED ✅**
