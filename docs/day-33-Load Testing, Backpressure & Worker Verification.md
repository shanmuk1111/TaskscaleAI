# Day 33 — Load Testing, Backpressure & Worker Verification
## 1. Objective

The main objective of Day 33 was to start real load testing of TaskScale AI and verify that the distributed worker system continues to operate correctly when the workload increases.

The project specification requires real performance measurements and specifically says not to invent benchmark results. 

---

## 2. Locust Load Testing

Locust was installed and configured for testing the TaskScale API.

Load-test endpoint:

```text
POST /jobs
```

The test submits:

```json
{
  "type": "ai_summarization",
  "input": {
    "text": "TaskScale load testing job."
  }
}
```

The test was performed using **5 concurrent users**.

---

## 3. Initial Load-Test Problem

During the first load test, many requests received:

```text
429 Too Many Requests
```

The reason was the TaskScale rate limiter.

The original configuration allowed only a small number of requests per time window.

For load testing, the rate limit was increased to:

```text
RATE_LIMIT = 1000
```

This allowed us to continue testing the actual job-processing system.

---

## 4. Stable Load Test

After the rate-limit adjustment, a stable Locust test was performed.

### Result

| Metric                |       Result |
| --------------------- | -----------: |
| Users                 |            5 |
| Requests              |      **355** |
| Failures              |        **0** |
| Failure rate          |       **0%** |
| RPS                   |      **2.9** |
| Average response time | **55.59 ms** |
| Median                |    **33 ms** |
| 95th percentile       |   **110 ms** |
| 99th percentile       |   **770 ms** |
| Minimum               |    **14 ms** |
| Maximum               |  **1170 ms** |

This confirmed that under this particular test workload, the API accepted all 355 requests successfully.

---

## 5. Backpressure / Overload Test

A second test was allowed to continue generating requests.

The system eventually became overloaded.

Final observed Locust result:

| Metric                |         Result |
| --------------------- | -------------: |
| Users                 |              5 |
| Requests              |        **789** |
| Failures              |        **413** |
| Failure rate          |        **52%** |
| RPS                   |        **1.4** |
| Average response time | **1124.46 ms** |
| Median                |    **2000 ms** |
| 95th percentile       |    **2100 ms** |
| 99th percentile       |    **2100 ms** |
| Minimum               |      **13 ms** |
| Maximum               |    **5540 ms** |

The failures occurred after the system received more work than it could accept/process at that point.

The API returned the backpressure response:

```text
System is busy. Too many jobs are waiting.
```

This demonstrated the queue-overload protection mechanism.

The project specification explicitly requires backpressure so that excessive incoming jobs do not cause uncontrolled queue growth. 

---

## 6. Worker and Redis Problem Discovered

During the load test, we discovered an important distributed-system configuration problem.

The worker was previously connecting to:

```text
host.docker.internal
```

while the Kubernetes scheduler was using the Kubernetes Redis service.

This meant that the scheduler and worker could be communicating with different Redis instances.

### Problem

```text
Scheduler
    ↓
Redis A

Worker
    ↓
Redis B
```

### Solution

The Redis client was changed to use environment variables:

```python
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
```

The Kubernetes worker uses:

```text
REDIS_HOST=redis
REDIS_PORT=6379
```

The final worker verification showed:

```text
host: redis
port: 6379
```

---

## 7. Worker Image Update

A corrected worker image was created:

```text
taskscale-worker:redis-fix
```

The image was imported into the Docker Desktop Kubernetes containerd environment.

The worker deployment was updated to:

```text
Image: taskscale-worker:redis-fix
ImagePullPolicy: IfNotPresent
```

The deployment successfully rolled out.

Two worker pods were subsequently running:

```text
taskscale-worker-5b87c8ccc6-54tfs   1/1   Running
taskscale-worker-5b87c8ccc6-cqntb    1/1   Running
```

---

## 8. Redis Stream Verification

The worker was verified against the Kubernetes Redis service.

Redis stream:

```text
taskscale:job_stream
```

Consumer group:

```text
workers
```

Final verification:

```text
STREAM: 10
pending: 0
lag: 0
```

The important result was:

```text
pending: 0
lag: 0
```

This confirmed that there were no pending messages waiting for worker acknowledgement.

---

## 9. PostgreSQL Job Verification

The database was checked after the worker fix.

Jobs 1–10 were:

```text
1   COMPLETED
2   COMPLETED
3   COMPLETED
4   COMPLETED
5   COMPLETED
6   COMPLETED
7   COMPLETED
8   COMPLETED
9   COMPLETED
10  COMPLETED
```

Therefore:

```text
10 / 10 jobs completed successfully
```

---

## 10. Kubernetes Verification

The current Kubernetes context is:

```text
docker-desktop
```

TaskScale deployments were verified:

```text
taskscale-backend       1/1
taskscale-postgres      1/1
taskscale-redis         1/1
taskscale-scheduler     1/1
taskscale-worker        1/1
```

The worker deployment is therefore operational in the current Docker Desktop Kubernetes cluster.

---

## 11. Monitoring Status

The current Kubernetes cluster does **not** contain the `monitoring` namespace.

Verified namespaces:

```text
default
kube-node-lease
kube-public
kube-system
local-path-storage
taskscale
```

There are currently no Prometheus or Grafana deployments/services in this cluster.

Therefore this command:

```powershell
kubectl port-forward svc/taskscale-monitoring-grafana 3001:80 -n monitoring
```

returns:

```text
Error from server (NotFound): namespaces "monitoring" not found
```

This is because the current Kubernetes context is the local Docker Desktop cluster. Prometheus/Grafana had previously been configured in the EKS environment, but they are not installed in this current local cluster.

**Grafana monitoring is therefore not counted as completed for the current Docker Desktop environment.**

---

## 12. Important Engineering Finding

Day 33 exposed and fixed a real distributed-system problem.

### Before

```text
              ┌── Redis A
Scheduler ────┘

Worker ──────── Redis B
```

The scheduler and worker were not necessarily operating on the same Redis instance.

### After

```text
                 ┌── Scheduler
                 │
Kubernetes Redis ─┼── Worker 1
                 │
                 └── Worker 2
```

Both scheduler and workers now use:

```text
redis:6379
```

This allowed the Redis stream to be consumed correctly.

---

## 13. Day 33 Results

### Successful tests

* Locust installed and configured
* 5-user load test performed
* **355 requests with 0 failures**
* **0% failure rate under the stable test**
* Redis stream verified
* Worker Redis connection fixed
* Scheduler/worker Redis consistency fixed
* Worker image updated
* Kubernetes worker deployment successfully rolled out
* Two worker pods running
* 10/10 queued jobs completed
* Redis pending messages = 0
* Backpressure behavior successfully observed

### Overload test

The overload test produced:

```text
789 requests
413 failures
52% failure rate
```

This is recorded as an **overload/backpressure measurement**, not as a normal system failure rate.

### Monitoring

Prometheus/Grafana are **not currently installed in the active Docker Desktop cluster**.

---

# Day 33 Status

**DAY 33 — COMPLETED**

The project now has a real measured load-testing result, a demonstrated overload/backpressure scenario, and a fixed scheduler-worker Redis configuration.

The next load-testing phase can later expand to the project specification's larger targets such as **1,000 jobs, 10,000 jobs, and different worker counts**, but those results should only be documented after actually running those tests. 
