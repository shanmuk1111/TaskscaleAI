# Day 17 – Backpressure

## Objective

Implement backpressure so that TaskScale AI can prevent uncontrolled queue growth when too many jobs are waiting.

The system should reject new jobs when the priority queue reaches a configured maximum size.

---

## What Was Implemented

A new backpressure module was created:

app/backpressure.py

The module checks the number of jobs currently waiting in the Redis priority queue.

Configuration
PRIORITY_QUEUE = "taskscale:priority_queue"
MAX_QUEUED_JOBS = 10

The maximum number of queued jobs is currently set to:

10 jobs
Backpressure Logic

The function:

check_backpressure()

checks the Redis priority queue size using:

redis_client.zcard(PRIORITY_QUEUE)

If the queue reaches the configured limit, the API returns:

HTTP 429 Too Many Requests

with the message:

{
  "detail": "System is busy. Too many jobs are waiting."
}

API Integration

Backpressure checking was added to the job creation endpoint.

The request flow is now:

            Client
               ↓
            FastAPI
               ↓
            Backpressure Check
               ↓
            Rate Limit Check
               ↓
            PostgreSQL
               ↓
            Redis Priority Queue
               ↓
            Scheduler
               ↓
            Redis Stream
               ↓
            Worker

If the priority queue is full, the request is rejected before a new job is created.

## Testing

### Test 1 – Empty Queue

Redis was checked using:

ZCARD taskscale:priority_queue

The queue was initially empty or being drained by the scheduler.

### Test 2 – Queue Overload

The scheduler was stopped temporarily so that jobs could remain in the priority queue.

Multiple jobs were submitted quickly until the queue reached the configured limit.

The next job submission returned:

HTTP 429 Too Many Requests

Response:

        {
        "detail": "System is busy. Too many jobs are waiting."
        }

This confirms that backpressure is working.

## Result

Backpressure successfully prevents additional jobs from being accepted when the Redis priority queue reaches its configured capacity.

Status

Day 17 – COMPLETE ✅

Evidence

The Day 17 test produced:

429 Too Many Requests

with:

{
  "detail": "System is busy. Too many jobs are waiting."
}

This provides evidence that the queue overload protection is functioning correctly.

Important Note

The current implementation measures only the number of jobs waiting in the Redis priority queue.

It does not yet represent total system capacity including:

jobs already inside the Redis Stream
jobs currently running
worker capacity

More advanced capacity control can be added later if required.