# Day 12 – Worker Failure Detection and Job Recovery

## Goal

The goal of Day 12 was to make TaskScale AI more reliable when a worker crashes while processing a job.

The system should:

- Detect workers that stop sending heartbeats.
- Mark failed workers as `DEAD`.
- Find jobs that were running on the failed worker.
- Return those jobs to the queue.
- Allow another worker to process the recovered jobs.
- Prevent duplicate execution of already completed jobs.
- Properly acknowledge recovered and failed Redis Stream messages.

---

## 1. Worker Heartbeat

Each worker has a unique worker ID.

Example:

text
worker-8f528a76

When a worker starts, it registers itself in the PostgreSQL workers table.

The worker sends a heartbeat every 3 seconds.

Example worker output:

Heartbeat sent: worker-8f528a76

The heartbeat updates:

last_heartbeat
status = ALIVE

This allows the system to determine whether a worker is still active.

## 2. Worker Monitor

A separate process was implemented in:

app/worker_monitor.py

The monitor checks worker heartbeats every 5 seconds.

A worker is considered dead when its heartbeat has not been updated for 10 seconds.

The monitor changes:

ALIVE → DEAD

Example:

Worker worker-eb7f0875 marked as DEAD

## 3. Detecting Unfinished Jobs

When a worker is detected as dead, the monitor searches PostgreSQL for jobs that were:

status = RUNNING

and belonged to that worker.

These jobs are considered unfinished because the worker stopped before completing them.

## 4. Recovering Jobs

For every unfinished job, the monitor changes:

RUNNING → QUEUED

and removes the failed worker assignment:

worker_id = NULL

The job is then added back to the Redis Stream:

taskscale:job_stream

The implementation uses:

redis_client.xadd(
    "taskscale:job_stream",
    {
        "job_id": str(job_id)
    }
)

This is important because the workers consume jobs from the Redis Stream.

## 5. Multiple Workers

Multiple workers can consume jobs from the same Redis Stream.

Each worker has a unique ID.

For example:

worker-eb7f0875
worker-8f528a76
worker-974b7582

If one worker fails, another available worker can process the recovered job.

## 6. Atomic Job Claim

Workers use an atomic database update when claiming a job.

The worker only changes a job from:

QUEUED → RUNNING

if the job is still QUEUED.

This prevents two workers from claiming the same job at the same time.

Example logic:

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

If the update affects zero rows, another worker may have already claimed the job.

## 7. Duplicate Execution Protection

Before processing a job, the worker checks whether the job is already completed.

If:

status = COMPLETED

the worker skips processing and sends an ACK for the Redis Stream message.

Example:

Job 53 is already COMPLETED. Skipping duplicate execution.
ACK sent for duplicate job 53

This provides protection against unnecessary duplicate execution.

## 8. Redis Stream Acknowledgement

Workers use Redis Streams consumer groups.

The consumer group is:

workers

A job is acknowledged only after successful processing.

Example:

redis_client.xack(
    "taskscale:job_stream",
    "workers",
    message_id
)

For a successfully completed job:

Job 65 is COMPLETED
ACK sent for job 65

For duplicate jobs, the message is also acknowledged without executing the job again.

## 9. Failure Recovery Test

A real worker failure was simulated by stopping a worker while it had a running job.

The monitor detected the worker failure.

Example:

Worker worker-eb7f0875 marked as DEAD
Recovered job 72 from dead worker worker-eb7f0875

The recovered job was then processed by another worker.

PostgreSQL verification showed:

id | status    | worker_id
---+-----------+----------------
72 | COMPLETED | worker-8f528a76

The original worker was:

worker-eb7f0875

The new worker was:

worker-8f528a76

Therefore, the test confirmed that the job was successfully recovered and processed by a different worker.

## 10. Redis Pending Message Cleanup

When a worker crashes after receiving a Redis Stream message, the original message can remain in the Pending Entries List because the failed worker could not send an ACK.

The pending messages were inspected using:

XPENDING taskscale:job_stream workers

Three stale pending messages were identified.

They corresponded to:

Job 63
Job 66
Job 72

The messages were verified against the Redis Stream using XRANGE.

After confirming that the jobs had already been recovered and completed, the stale messages were acknowledged using XACK.

Finally:

XPENDING taskscale:job_stream workers

returned:

(integer) 0

This confirmed that there were no remaining unacknowledged messages in the consumer group's pending list.

## 11. Final Job Lifecycle

The failure recovery lifecycle is:

QUEUED
   ↓
Redis Stream
   ↓
Worker claims job
   ↓
RUNNING
   ↓
Worker crashes
   ↓
Heartbeat stops
   ↓
Monitor detects DEAD worker
   ↓
RUNNING job identified
   ↓
Job returned to QUEUED
   ↓
Redis Stream
   ↓
Another worker claims job
   ↓
RUNNING
   ↓
COMPLETED
   ↓
Redis ACK

## 12. Day 12 Result

Day 12 successfully implemented and tested worker failure detection and job recovery.

Completed features:

Worker registration
Worker heartbeat
Worker health monitoring
Dead worker detection
Running job recovery
Redis Stream re-queueing
Multiple-worker recovery
Atomic job claiming
Duplicate execution protection
Redis Stream acknowledgements
Pending message inspection
Pending message cleanup

The failure recovery test successfully demonstrated that a job running on a failed worker can be recovered and completed by another worker.