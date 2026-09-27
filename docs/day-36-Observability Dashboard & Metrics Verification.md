# Day 36 — Observability Dashboard & Metrics Verification

## Objective

The goal of Day 36 was to connect the TaskScale AI application metrics to Prometheus and visualize the system performance and health using Grafana.

This continues the observability requirements in the project specification, including jobs/sec, latency, queue length, failures, CPU, memory, and other worker/system metrics. 

---

## Work Completed

### 1. Prometheus Verification

Verified that Prometheus is running correctly inside Kubernetes.

Prometheus successfully discovered the TaskScale worker targets.

The query:

```promql
up{namespace="taskscale"}
```

returned active TaskScale worker targets with value:

```text
1
```

This confirmed that Prometheus can scrape the TaskScale worker metrics endpoints.

---

### 2. TaskScale Metrics Verification

Verified the actual metrics exposed by the TaskScale application.

The application exposes metrics with the `taskscale_` prefix:

```text
taskscale_jobs_total
taskscale_jobs_completed_total
taskscale_jobs_failed_total
taskscale_job_duration_seconds
taskscale_queue_size
```

The metrics were verified directly from both the worker and backend `/metrics` endpoints.

---

### 3. Grafana Dashboard

Created and saved the:

```text
TaskScale AI - Observability
```

Grafana dashboard.

The dashboard contains:

* Processed Jobs
* Completed Jobs
* Failed Jobs
* Queue Size
* Jobs / Second
* Average Job Latency
* Cluster CPU Usage
* Cluster Memory Usage

---

## 4. Dashboard Queries

### Processed Jobs

```promql
sum(taskscale_jobs_completed_total) + sum(taskscale_jobs_failed_total)
```

### Completed Jobs

```promql
sum(taskscale_jobs_completed_total)
```

### Failed Jobs

```promql
sum(taskscale_jobs_failed_total)
```

### Queue Size

```promql
max(taskscale_queue_size)
```

### Jobs / Second

```promql
sum(rate(taskscale_jobs_completed_total[5m]))
```

### Average Job Latency

```promql
sum(rate(taskscale_job_duration_seconds_sum[5m]))
/
sum(rate(taskscale_job_duration_seconds_count[5m]))
```

---

## 5. Kubernetes Monitoring

Verified Kubernetes resource monitoring through Prometheus/Grafana.

The dashboard successfully displays:

* Cluster CPU usage
* Cluster memory usage

This confirms that Kubernetes infrastructure metrics are also available alongside TaskScale application metrics.

---

## 6. Load Test Verification

Used Locust to generate TaskScale jobs and verify that the application metrics change when jobs are processed.

The dashboard showed actual completed-job data and corresponding jobs/sec and latency measurements.

Example observed dashboard values during testing included:

```text
Completed Jobs:       264
Failed Jobs:           0
Queue Size:            0
Jobs / Second:        ~0.8
Average Latency:      ~3.26 seconds
```

These are **observed test values**, not fixed project benchmarks.

---

## 7. Important Finding

During verification, the original Grafana queries were initially incorrect because the actual Prometheus metric names contain the prefix:

```text
taskscale_
```

For example:

```text
jobs_completed_total
```

was incorrect.

The actual metric is:

```text
taskscale_jobs_completed_total
```

After correcting the queries, Grafana successfully displayed TaskScale metrics.

---

## 8. Current Status

| Component                 | Status     |
| ------------------------- | ---------- |
| Prometheus                | Completed  |
| Grafana                   | Completed  |
| TaskScale worker scraping | Completed  |
| TaskScale metrics         | Verified   |
| CPU monitoring            | Completed  |
| Memory monitoring         | Completed  |
| Jobs/sec monitoring       | Completed  |
| Latency monitoring        | Completed  |
| Queue monitoring          | Configured |
| Failure monitoring        | Completed  |
| Dashboard                 | Saved      |

The project specification identifies observability as a dedicated phase covering Prometheus, Grafana, logs, metrics, worker health, and system-performance measurements. 

### Day 36 Status

**Day 36 — Observability Dashboard & Metrics Verification: COMPLETED**, subject to your final queue-size verification during an active load test.

### Not implemented yet

A retry metric is not currently exposed by the application, so a retry dashboard panel was not included. We should add that only when the actual application metric is implemented rather than displaying invented data.

**Next: Day 37.**
