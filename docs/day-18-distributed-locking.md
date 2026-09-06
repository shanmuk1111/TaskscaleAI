# Day 18 – Distributed Locking

## Objective

Implement distributed locking so that multiple scheduler instances cannot perform the protected scheduling operation at the same time.

Redis is used as the shared coordination mechanism.

---

## What Was Implemented

A new distributed lock module was created:


app/distributed_lock.py


The lock uses the Redis key:

taskscale:scheduler_lock

The lock has a timeout of:

10 seconds

## Lock Acquisition

The scheduler attempts to acquire the lock using Redis:

redis_client.set(
    LOCK_KEY,
    lock_token,
    nx=True,
    ex=LOCK_TIMEOUT
)

The NX option ensures that the lock is created only when it does not already exist.

Each lock owner receives a unique UUID token.

## Lock Releas

The lock is released only when the stored Redis token matches the token held by the scheduler.

This prevents one scheduler from accidentally releasing another scheduler's lock.

## Scheduler Integration

The scheduler now follows this flow:
        
        Scheduler
            ↓
        Acquire Distributed Lock
            ↓
        Read Priority Queue
            ↓
        Move Job to Redis Stream
            ↓
        Release Distributed Lock

If another scheduler already owns the lock:

Scheduler 1 → Lock acquired
Scheduler 2 → Lock unavailable

The second scheduler waits and tries again.

## Testing

### Test 1 – Lock Acquisition

The first lock acquisition returned a unique UUID.

The second acquisition while the lock was already held returned:

None

This confirmed that only one caller can acquire the lock.

### Test 2 – Lock Release

The lock owner successfully released its lock:

Release first: True

A new lock could then be acquired successfully.

### Test 3 – Two Scheduler Instances

Two scheduler instances were started.

The scheduler that did not own the lock repeatedly displayed:

Another scheduler holds the lock

This confirmed that the Redis lock prevented both scheduler instances from entering the protected scheduling operation at the same time.

### Test 4 – Redis Lock Verification

Redis was checked using:

GET taskscale:scheduler_lock

A UUID value was returned.

The TTL was checked using:

TTL taskscale:scheduler_lock

The value was approximately:

10 seconds

This confirmed that the lock has an automatic expiration.

### Test 5 – Job Processing

A test job with idempotency key:

day18-001

was submitted.

The job was successfully processed and reached:

COMPLETED

The priority queue was then checked:

ZCARD taskscale:priority_queue

## Result:

(integer) 0

The Redis Stream pending count was also:

XPENDING taskscale:job_stream workers
(integer) 0
Result

Distributed locking successfully coordinates multiple scheduler instances using Redis.

Only one scheduler can hold the lock at a time, while other schedulers wait until the lock becomes available.

Status

## Day 18 – COMPLETE ✅