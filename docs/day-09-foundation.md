# Day 9 --- Worker Heartbeat, Failure Detection, and Job Recovery

## Goal

Day 9 adds worker reliability features to TaskScale AI.

The system can now:

-   Register workers in PostgreSQL.
-   Give each worker a unique ID.
-   Send periodic heartbeats.
-   Detect workers whose heartbeat has stopped.
-   Track which worker is processing a job.
-   Recover a running job when its worker dies.
-   Put the recovered job back into the Redis queue.
-   Allow another worker to process the recovered job.

## 1. Worker Registration

Each worker generates a unique ID when it starts.

Example:

``` text
worker-0791ecb2
worker-64cc0954
worker-b5f52efe
```

The worker registers itself in the PostgreSQL `workers` table.

The table contains:

-   `worker_id`
-   `last_heartbeat`
-   `status`

A newly registered worker starts with status:

``` text
ALIVE
```

## 2. Worker Heartbeat

Each worker runs a background heartbeat thread.

The heartbeat updates `last_heartbeat` every 3 seconds.

Example:

``` text
Heartbeat sent: worker-0791ecb2
Heartbeat sent: worker-0791ecb2
Heartbeat sent: worker-0791ecb2
```

This allows the system to know whether a worker is still active.

## 3. Worker Failure Detection

A separate worker monitor checks the heartbeat timestamps.

Current configuration:

``` text
Heartbeat interval: 3 seconds
Heartbeat timeout: 10 seconds
Monitor interval: 5 seconds
```

If a worker has not sent a heartbeat for more than the timeout period,
the monitor changes its status:

``` text
ALIVE → DEAD
```

Example:

``` text
Worker worker-bff68958 marked as DEAD
```

## 4. Job-to-Worker Tracking

A `worker_id` column was added to the `jobs` table.

When a worker starts processing a job, the worker records its ID:

``` text
Job 46
status    = RUNNING
worker_id = worker-bff68958
```

This creates a relationship between a running job and the worker
processing it.

## 5. Job Recovery

When the monitor detects a dead worker, it searches for jobs that:

``` text
status = RUNNING
worker_id = dead worker
```

Those unfinished jobs are recovered.

The monitor:

1.  Marks the worker as `DEAD`.
2.  Finds its running jobs.
3.  Changes each recovered job to `QUEUED`.
4.  Clears the job's `worker_id`.
5.  Adds the job ID back to the Redis queue.

Example:

``` text
Worker A crashes
        ↓
Heartbeat stops
        ↓
Monitor detects DEAD
        ↓
Find RUNNING job
        ↓
Job → QUEUED
        ↓
Job ID → Redis
        ↓
Worker B picks up job
        ↓
Job → COMPLETED
```

## 6. Recovery Test

A real recovery test was completed.

The monitor reported:

``` text
Worker worker-bff68958 marked as DEAD
Recovered job 46 from dead worker worker-bff68958
```

PostgreSQL later showed:

``` text
id | status    | worker_id      | retry_count
46 | COMPLETED | worker-65b2b88c | 0
```

This confirms that:

-   The original worker died.
-   The monitor detected the failure.
-   The running job was recovered.
-   The job was returned to Redis.
-   Another worker processed the job.
-   The recovered job completed successfully.

## 7. Current Architecture

``` text
                PostgreSQL
              ┌─────────────┐
              │    jobs     │
              │   workers   │
              └──────┬──────┘
                     │
                     │ heartbeat/status
                     │
              ┌──────▼──────┐
              │   Monitor   │
              └──────┬──────┘
                     │
             detects DEAD worker
                     │
                     ▼
              recover RUNNING job
                     │
                     ▼
                ┌─────────┐
                │  Redis  │
                │  Queue  │
                └────┬────┘
                     │
              ┌──────▼──────┐
              │   Worker    │
              └─────────────┘
```

## 8. Reliability Features Completed

Day 9 now includes:

-   Worker registration
-   Worker identity
-   Heartbeat mechanism
-   Dead-worker detection
-   Job ownership tracking
-   Running-job recovery
-   Redis re-queueing
-   Recovery by another worker

## 9. Limitations

This is the current basic recovery implementation.

More advanced reliability features are still future work, including
stronger acknowledgement semantics, duplicate-execution protection, more
advanced recovery handling, and other production-grade failure
scenarios.

## Result

Day 9 successfully demonstrates worker health monitoring and recovery:

``` text
Worker failure
      ↓
Failure detection
      ↓
Job recovery
      ↓
Redis re-queue
      ↓
Another worker
      ↓
Successful completion
```

TaskScale AI can now recover an unfinished job when its worker fails.
