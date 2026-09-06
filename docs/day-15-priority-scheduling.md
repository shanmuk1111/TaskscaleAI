# Day 15 — Priority Scheduling

## Goal

Implement priority-based job scheduling so that higher-priority jobs are selected before lower-priority jobs.

## What Was Implemented

TaskScale AI now supports job priorities.

Priority values:

- High priority = 10
- Normal priority = 5
- Low priority = 1

Jobs are stored in a Redis Sorted Set:

taskscale:priority_queue

The priority is represented using a Redis score.

Because Redis returns lower scores first, the scheduler uses a negative priority score:

High priority:
10 → -10

Normal priority:
5 → -5

Low priority:
1 → -1

Therefore:

-10 is selected before -5
-5 is selected before -1

## Scheduler Flow

API
↓
PostgreSQL
↓
Priority Queue (Redis Sorted Set)
↓
Scheduler
↓
Redis Stream
↓
Workers
↓
PostgreSQL

## Testing

Three jobs were tested with different priorities:

| Job | Priority |
|-----|----------|
| 87 | 10 |
| 86 | 5 |
| 85 | 1 |

Scheduler output:

Scheduler selected job 87 with priority score -10.0
Scheduler selected job 86 with priority score -5.0
Scheduler selected job 85 with priority score -1.0

The worker processed the jobs successfully.

Final order:

87 → 86 → 85

## Database Verification

All three jobs reached COMPLETED status.

The database confirmed:

- Job 87 → COMPLETED → priority 10
- Job 86 → COMPLETED → priority 5
- Job 85 → COMPLETED → priority 1

## Redis Verification

After the scheduler processed the jobs:

ZRANGE taskscale:priority_queue 0 -1 WITHSCORES

returned an empty queue.

This is expected because the scheduler removed the selected jobs from the priority queue.

Redis Stream verification:

XPENDING taskscale:job_stream workers

returned:

(integer) 0

This confirms that all processed Stream messages were acknowledged.

## Result

Priority scheduling is working correctly.

Higher-priority jobs are selected before lower-priority jobs.

## Engineering Lesson

A Redis Sorted Set can be used as a priority queue by storing jobs with priority scores.

The scheduler selects the highest-priority waiting job and moves it into the Redis Stream for worker processing.