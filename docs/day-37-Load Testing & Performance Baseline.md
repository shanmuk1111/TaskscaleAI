# Day 37 — Load Testing & Performance Baseline

**Project:** TaskScale AI — Fault-Tolerant Distributed Workflow and AI Execution Platform
**Phase:** Phase 10 — Load Testing
**Status:** Completed

## 1. Objective

The objective of Day 37 was to verify TaskScale's behavior under HTTP load and confirm that jobs could successfully travel through the complete execution pipeline.

The project specification requires load testing with different worker counts and real measurements, without inventing benchmark numbers. 

---

## 2. Load Testing Tool

**Tool used:** Locust

Locust was configured to send requests to the TaskScale FastAPI backend.

The test was run against:

```text
http://localhost:8000
```

---

## 3. Baseline Configuration

The baseline test used:

```text
Users:       5
Spawn rate:  1 user/second
Workers:     3
```

The Kubernetes worker deployment was running three worker pods during the final verification.

---

## 4. Locust Results

Final measured results:

| Metric                |        Result |
| --------------------- | ------------: |
| Users                 |             5 |
| Requests              |       **998** |
| Failures              |         **0** |
| Failure rate          |        **0%** |
| Requests/sec          |       **2.9** |
| Median response time  |     **20 ms** |
| Average response time | **104.41 ms** |
| p95                   |    **200 ms** |
| p99                   |  **1,500 ms** |
| Maximum               |  **9,966 ms** |

These are the actual measurements from the Day 37 test.

The maximum response time of **9,966 ms** was an observed outlier. It was recorded rather than excluded from the results.

---

## 5. End-to-End Job Verification

After the Locust test, individual jobs were also submitted directly to the backend.

Job **1012** successfully followed the complete pipeline:

```text
FastAPI
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
   ↓
COMPLETED
```

Job 1012 was processed by:

```text
worker-0768e385
```

It was created at:

```text
13:10:12
```

and completed at:

```text
13:10:16
```

with no error.

Jobs **993–1012** were also verified as `COMPLETED`.

---

## 6. Worker Stability

The final Kubernetes verification showed:

```text
taskscale-worker-5d96cc456b-m5q5t   Running   0 restarts
taskscale-worker-5d96cc456b-n75b6   Running   0 restarts
taskscale-worker-5d96cc456b-sjd65   Running   0 restarts
```

Therefore, all three active workers remained healthy during the final verification.

---

## 7. Redis Verification

The Redis Stream was verified using the actual project configuration:

```text
Stream: taskscale:job_stream
Consumer group: workers
```

Final Redis state:

```text
Stream entries: 1016+
Consumers:      10
Pending:        0
Lag:            0
```

This confirmed that the consumer group had no unacknowledged pending messages and no remaining stream lag at the time of verification.

---

## 8. Scheduler Verification

The scheduler successfully moved jobs from the priority queue into the Redis Stream.

Example:

```text
Leader selected job 939
Job 939 added to Redis Stream
```

A later controlled test with job 1012 confirmed the scheduler continued to transfer newly submitted jobs into the stream.

The scheduler uses:

```text
taskscale:priority_queue
        ↓
taskscale:job_stream
```

This verified the scheduling portion of the pipeline.

---

## 9. Issue Discovered During Testing

During the load-testing process, some jobs temporarily remained in `QUEUED` state while TaskScale components had previously experienced Kubernetes restarts.

Investigation showed:

* Workers were healthy.
* Redis Stream had zero lag.
* Redis consumer group had zero pending messages.
* The priority queue was empty.
* The scheduler was running.
* The jobs were eventually processed successfully.

A controlled test with job 1012 confirmed that the current pipeline was functioning correctly.

This was an important debugging exercise because the project specification explicitly requires investigating real distributed-system failure scenarios rather than assuming the system always works. 

---

## 10. Metrics Verified

The following areas were checked during Day 37:

* HTTP request throughput
* HTTP failure rate
* Response latency
* Worker availability
* Worker restarts
* Redis Stream length
* Redis consumer-group pending messages
* Redis consumer-group lag
* Job completion
* Scheduler activity
* Queue state

The project specification identifies jobs/sec, latency, queue length, failure rate, retry count, recovery time, CPU, and memory as important observability/load-testing measurements. 

---

## 11. Final Architecture Tested

```text
                Locust
                  │
                  ▼
           FastAPI Backend
                  │
                  ▼
             PostgreSQL
                  │
                  ▼
       Redis Priority Queue
                  │
                  ▼
             Scheduler
                  │
                  ▼
         Redis Job Stream
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
     Worker 1  Worker 2  Worker 3
        │         │         │
        └─────────┼─────────┘
                  ▼
             PostgreSQL
                  │
                  ▼
          Completed Job
```

This follows the project's intended distributed architecture: API → scheduler → Redis queue → multiple workers → PostgreSQL. 

---

## 12. Day 37 Outcome

### Completed

* Locust installed and executed
* 5-user baseline performed
* 998 requests measured
* 0 request failures observed
* Real latency measurements recorded
* Worker stability verified
* Redis Stream verified
* Consumer group verified
* Scheduler verified
* End-to-end job processing verified
* Job 1012 successfully completed
* Workers remained at 0 restarts during final verification

### Day 37: **COMPLETE**

The next work should move to the next planned project task rather than repeating the same baseline test. The specification's broader Phase 10 goal is to test different worker counts and eventually larger workloads such as 1,000 and 10,000 jobs, using actual measured results. 

