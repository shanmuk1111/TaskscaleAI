# Day 40 Documentation — 5-Worker Load Test

## Objective

The objective of Day 40 was to run a **1,000-job load test with 5 workers** and compare the observed results with the previous 3-worker test.

This test is part of the project’s load-testing and scalability phase, where different worker counts are tested using real measurements.

---

## 1. Worker Scaling

The worker deployment was scaled to **5 replicas** for the benchmark.

The HPA was configured with:

* Minimum workers: 3
* Maximum workers: 5
* CPU target: 70%

During the test, the HPA showed **5 replicas**.

---

## 2. Load Test

The existing `load_test_1000.py` script was used to submit 1,000 jobs.

### Submission Result

```text
Accepted:       1000
429 retries:    111
Submission time: 116.77 sec
Submission rate: 8.56 jobs/sec
```

### Result

* **1,000 jobs accepted successfully**
* **111 rate-limit retries**
* No permanent submission failures
* All submitted jobs eventually completed

---

## 3. Job Completion Verification

After the submission test, the database was checked.

Initial state:

```text
COMPLETED | 1005
RUNNING   |    3
```

After waiting for processing to finish:

```text
COMPLETED | 1008
```

There were:

* **0 RUNNING jobs**
* **0 QUEUED jobs**

The additional completed jobs represent previously existing jobs in the database, so the aggregate `1008` should **not** be interpreted as exactly 1,008 jobs from this benchmark.

---

## 4. Redis Verification

Redis consumer-group pending messages were checked:

```text
XPENDING taskscale:job_stream workers

0
```

This confirmed that there were **no pending unacknowledged jobs** remaining in the Redis stream consumer group.

---

## 5. Worker Health

At the end of the test:

```text
taskscale-worker-5d96cc456b-m5q5t   1/1 Running   6 restarts
taskscale-worker-5d96cc456b-n75b6   1/1 Running   6 restarts
taskscale-worker-5d96cc456b-pgskv   1/1 Running   2 restarts
```

All currently running workers were healthy:

```text
READY = 1/1
STATUS = Running
```

The restart counts are historical and occurred during the worker lifecycle. They should be investigated separately as a reliability issue.

---

## 6. Comparison With Day 39

| Metric             | Day 39 — 3 Workers | Day 40 — 5 Workers |
| ------------------ | -----------------: | -----------------: |
| Jobs submitted     |              1,000 |              1,000 |
| 429 retries        |                145 |                111 |
| Submission time    |         102.64 sec |         116.77 sec |
| Submission rate    |      9.74 jobs/sec |      8.56 jobs/sec |
| Final running jobs |                  0 |                  0 |
| Redis pending      |                  0 |                  0 |
| Workers used       |                  3 |                  5 |

**Important:** The submission rate measures how quickly the test client successfully submitted jobs to the backend. It is **not the worker processing throughput**.

Because the benchmark did not capture benchmark-specific processing start/end timestamps, we should not claim a processing-throughput improvement or degradation from these numbers.

---

## 7. Verification Commands Used

### Check job status

```powershell
kubectl exec -n taskscale taskscale-postgres-76fc9879f7-g4l98 -- psql -U postgres -d taskscale -c "SELECT status, COUNT(*) FROM jobs GROUP BY status ORDER BY status;"
```

### Check Redis pending jobs

```powershell
kubectl exec -n taskscale taskscale-redis-9dcb86cdf-27w8w -- redis-cli XPENDING taskscale:job_stream workers
```

### Check worker health

```powershell
kubectl get pods -n taskscale -l app=taskscale-worker
```

---

# Day 40 Final Status

**Day 40 — Completed**

### What was achieved

* Scaled the worker deployment to **5 workers**
* Submitted **1,000 jobs**
* Handled **111 rate-limit retries**
* All 1,000 submitted jobs completed
* Redis pending count reached **0**
* No jobs remained queued or running
* Verified all active worker pods were healthy
* Recorded real benchmark measurements for comparison with the 3-worker test

### Key learning

Increasing the worker count does not automatically increase the observed submission rate. The backend rate limiter, queue backpressure, scheduler, job workload, and available CPU all affect the overall system behavior.

### Next

**Day 41 — continue the load-testing/scalability phase and work toward a more accurate processing-throughput measurement.**

