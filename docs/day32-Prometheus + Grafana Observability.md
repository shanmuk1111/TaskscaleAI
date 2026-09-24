# Day 32 Documentation — Prometheus + Grafana Observability

## 1. Day 32 Goal

The goal of Day 32 was to add **observability** to TaskScale AI using:

* Prometheus
* Grafana
* Application metrics
* Worker metrics
* Kubernetes metrics
* Worker health monitoring

This directly supports Phase 9 of the project specification, which requires monitoring of jobs, latency, failures, retries, CPU, memory, and worker health. 

---

# 2. What We Implemented

### Backend metrics

Added Prometheus metrics to the FastAPI backend:

```text
taskscale_jobs_total
taskscale_jobs_completed_total
taskscale_jobs_failed_total
taskscale_job_retries_total
taskscale_job_duration_seconds
taskscale_queue_size
```

The backend exposes them through:

```text
GET /metrics
```

---

## 3. Worker Metrics

The worker was instrumented with Prometheus counters and a histogram.

The worker now records:

* Completed jobs
* Failed jobs
* Job retries
* Job execution duration

The worker also starts its own metrics server:

```text
Port: 8001
```

Metrics endpoint:

```text
http://127.0.0.1:8001/metrics
```

Example verified metrics:

```text
taskscale_jobs_completed_total 1.0
taskscale_jobs_failed_total 0.0
taskscale_job_retries_total 0.0
```

---

# 4. Kubernetes Monitoring

TaskScale was deployed to the AWS EKS cluster.

Monitoring was installed using:

```text
kube-prometheus-stack
```

Prometheus and Grafana were deployed in the:

```text
monitoring
```

namespace.

TaskScale applications run in:

```text
taskscale
```

namespace.

---

# 5. Backend ServiceMonitor

Created:

```text
k8s/backend-servicemonitor.yaml
```

The ServiceMonitor connects Prometheus to:

```text
TaskScale Backend
       ↓
/metrics
       ↓
Prometheus
```

Prometheus successfully reported the backend target as:

```text
UP
```

---

# 6. Worker Monitoring

Created a Kubernetes Service for the worker metrics:

```text
taskscale-worker
```

Port:

```text
8001
```

Created:

```text
k8s/worker-servicemonitor.yaml
```

The worker metrics flow became:

```text
Worker
  ↓
Port 8001
  ↓
Kubernetes Service
  ↓
ServiceMonitor
  ↓
Prometheus
  ↓
Grafana
```

The Prometheus worker target was successfully verified as:

```text
UP
```

---

# 7. Grafana Dashboard

Created a dashboard:

```text
TaskScale AI Monitoring
```

The dashboard contains the following panels.

### 1. Completed Jobs

```promql
sum(taskscale_jobs_completed_total)
```

### 2. Failed Jobs

```promql
sum(taskscale_jobs_failed_total)
```

### 3. Job Retries

```promql
sum(taskscale_job_retries_total)
```

### 4. Jobs Completed / Second

```promql
sum(rate(taskscale_jobs_completed_total[5m]))
```

### 5. Average Job Duration

```promql
rate(taskscale_job_duration_seconds_sum[5m])
/
rate(taskscale_job_duration_seconds_count[5m])
```

### 6. Available Workers

```promql
kube_deployment_status_replicas_available{
  namespace="taskscale",
  deployment="taskscale-worker"
}
```

### 7. Worker CPU

```promql
sum(
  rate(container_cpu_usage_seconds_total{
    namespace="taskscale",
    pod=~"taskscale-worker-.*",
    container="worker"
  }[5m])
) * 100
```

### 8. Worker Memory

```promql
sum(
  container_memory_working_set_bytes{
    namespace="taskscale",
    pod=~"taskscale-worker-.*",
    container="worker"
  }
)
```

---

# 8. Important Debugging During Day 32

We encountered an issue where test jobs were accidentally being sent to the **local FastAPI server** instead of the EKS backend.

The problem was caused by both:

```text
Local Python server → port 8000
EKS port-forward    → port 8000
```

Because of this, local workers processed jobs instead of the EKS worker.

We solved this by using a separate local port for the EKS backend:

```text
127.0.0.1:8081
        ↓
EKS backend:8000
```

Command:

```powershell
kubectl port-forward --address 127.0.0.1 svc/backend 8081:8000 -n taskscale
```

This allowed us to test the actual EKS pipeline.

---

# 9. End-to-End Test

A test job was submitted through the EKS backend:

```text
POST /jobs
```

The job was successfully stored and added to the Redis stream.

Redis verification:

```text
Stream entries: 2
```

Consumer group:

```text
workers
```

Final group state:

```text
pending: 0
lag: 0
entries-read: 2
```

The EKS worker successfully exposed:

```text
taskscale_jobs_completed_total 1.0
taskscale_jobs_failed_total 0.0
taskscale_job_retries_total 0.0
```

---

# 10. Grafana Verification

Grafana successfully displayed:

| Metric                  |    Result |
| ----------------------- | --------: |
| Completed Jobs          |         1 |
| Failed Jobs             |         0 |
| Job Retries             |         0 |
| Jobs Completed / Second |   Visible |
| Worker Metrics          |   Visible |
| Worker CPU              | Monitored |
| Worker Memory           | Monitored |
| Available Workers       | Monitored |

The final Grafana dashboard showed **Completed Jobs = 1** and **Failed Jobs = 0**.

---

# 11. Final Architecture

After Day 32:

```text
                    ┌───────────────┐
                    │ React Dashboard│
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ FastAPI Backend│
                    │    :8000       │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │     Redis     │
                    │ Job Stream     │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ EKS Worker     │
                    │    :8001       │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  PostgreSQL   │
                    └───────────────┘

                     Monitoring
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
        ┌────────────┐          ┌───────────┐
        │ Prometheus │ ───────► │  Grafana  │
        └────────────┘          └───────────┘
```

---

# 12. What I Learned

Day 32 covered:

1. What application metrics are.
2. How Prometheus collects metrics.
3. How `/metrics` works.
4. How Prometheus ServiceMonitors work.
5. How Kubernetes exposes worker metrics.
6. How Grafana visualizes Prometheus data.
7. How to monitor worker CPU and memory.
8. How to monitor job completion and failures.
9. How to verify metrics end-to-end.
10. How to debug local-vs-EKS port conflicts.
11. How Redis stream and consumer-group state can be used to debug job processing.

The project specification specifically requires Prometheus, Grafana, logs, metrics, error tracking, and worker health monitoring as part of Phase 9. 

---

# 13. Day 32 Status

## **COMPLETED**

Implemented and verified:

```text
Prometheus              ✅
Grafana                 ✅
Backend metrics         ✅
Worker metrics          ✅
ServiceMonitor          ✅
Worker monitoring       ✅
CPU monitoring          ✅
Memory monitoring       ✅
Job completion metric   ✅
Failure metric          ✅
Retry metric            ✅
End-to-end test         ✅
Grafana dashboard       ✅
```

**Day 32 — Prometheus + Grafana Observability: DONE.**
