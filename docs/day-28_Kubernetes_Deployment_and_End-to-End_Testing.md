# Day 28 — Kubernetes Deployment and End-to-End Testing

## Objective

Deploy TaskScale AI components into Kubernetes and verify that the complete distributed job execution system works inside the Kubernetes environment.

The main goal of Day 28 was to move the application from Docker-based execution to Kubernetes and verify:

* Kubernetes cluster
* PostgreSQL
* Redis
* FastAPI backend
* Scheduler
* Worker
* Job creation
* Job execution
* Job completion
* System statistics

---

# 1. Kubernetes Cluster Setup

Docker Desktop Kubernetes was configured and verified.

Kubernetes node:

```text
desktop-control-plane
Status: Ready
Version: v1.36.1
```

The Kubernetes namespace created for TaskScale AI was:

```text
taskscale
```

---

# 2. PostgreSQL Deployment

PostgreSQL was deployed inside Kubernetes.

Service:

```text
postgres
Port: 5432
Type: ClusterIP
```

The PostgreSQL pod was successfully running.

The TaskScale database was created and the required tables were initialized.

Tables:

```text
jobs
workers
```

This was important because the Kubernetes PostgreSQL instance was a new database and initially did not contain the TaskScale tables.

---

# 3. Redis Deployment

Redis was deployed inside Kubernetes.

Service:

```text
redis
Port: 6379
Type: ClusterIP
```

The Redis pod was successfully running.

Redis is used by TaskScale for queue and job-stream communication.

---

# 4. Backend Deployment

The TaskScale FastAPI backend was deployed using the Docker image:

```text
taskscale-backend:latest
```

The Kubernetes backend initially produced:

```text
ErrImageNeverPull
```

### Problem

The Kubernetes node was using:

```text
containerd://2.3.1
```

while the Docker image existed in Docker's image store.

Therefore, Kubernetes could not see the locally built image.

### Solution

The Docker image was exported and imported into the Kubernetes containerd image store.

The successful command was:

```powershell
cmd /c "docker save taskscale-backend:latest | docker exec -i desktop-control-plane ctr -n k8s.io images import -"
```

The image then became visible to Kubernetes:

```text
taskscale-backend:latest
```

The backend pod successfully started.

Backend logs confirmed:

```text
Application startup complete.
Uvicorn running on http://0.0.0.0:8000
```

---

# 5. Backend Service

The backend was exposed using a Kubernetes NodePort service:

```text
backend
Type: NodePort
Port: 8000
NodePort: 30080
```

Direct NodePort access through `localhost:30080` was not available in the Docker Desktop environment.

Therefore, Kubernetes port forwarding was used:

```powershell
kubectl port-forward service/backend 8001:8000 -n taskscale
```

The API was then accessible through:

```text
http://localhost:8001
```

The FastAPI documentation endpoint was successfully tested:

```text
/docs
```

---

# 6. Database Schema Problem

When `/jobs/stats` was first tested, the backend returned:

```text
500 Internal Server Error
```

The backend logs showed:

```text
psycopg2.errors.UndefinedTable:
relation "jobs" does not exist
```

### Cause

The Kubernetes PostgreSQL instance was a fresh database and did not contain the TaskScale tables.

### Solution

The SQLAlchemy models were used to create the tables:

```python
Base.metadata.create_all(bind=engine)
```

After initialization, PostgreSQL contained:

```text
jobs
workers
```

The `/jobs/stats` endpoint then worked correctly.

---

# 7. Worker and Scheduler Deployment

Initially, the Kubernetes environment contained:

```text
Backend
PostgreSQL
Redis
```

but the test job remained:

```text
QUEUED
```

because there was no Kubernetes worker processing it.

The TaskScale worker and scheduler were then deployed using the same backend image.

Worker:

```text
taskscale-worker
```

Scheduler:

```text
taskscale-scheduler
```

Both successfully started in Kubernetes.

---

# 8. Kubernetes End-to-End Job Test

A test job was submitted through the Kubernetes-hosted API.

Job:

```text
ID: 1
Type: kubernetes_test
```

Initial state:

```text
QUEUED
```

The Kubernetes worker then processed the job.

Final state:

```text
COMPLETED
```

Worker assigned:

```text
worker-2cf2ccd5
```

Retry count:

```text
0
```

The job successfully moved through the complete execution pipeline.

---

# 9. Final Statistics

The final `/jobs/stats` response showed:

```text
total_jobs:       1
queued_jobs:      0
running_jobs:     0
completed_jobs:   1
failed_jobs:      0
queue_size:       0
success_rate:     100.0
total_retries:    0
worker_utilization: 0.0
```

The average latency reported was:

```text
168.79 seconds
```

This value includes the time the test job spent waiting while the Kubernetes worker and scheduler were being deployed. It should **not** be treated as the actual worker execution time.

---

# 10. Final Kubernetes Architecture

The Kubernetes deployment now follows:

```text
                    Client
                      |
                      v
              Kubernetes Service
                      |
                      v
              FastAPI Backend
                      |
             +--------+--------+
             |                 |
             v                 v
        PostgreSQL           Redis
             |                 |
             |                 v
             |             Scheduler
             |                 |
             |                 v
             |              Worker
             |                 |
             +<----------------+
                      |
                      v
                  Job Result
```

---

# 11. Problems Solved During Day 28

### Problem 1 — Kubernetes could not find the Docker image

Error:

```text
ErrImageNeverPull
```

Solution:

Imported the Docker image into Kubernetes containerd.

---

### Problem 2 — PostgreSQL had no `jobs` table

Error:

```text
relation "jobs" does not exist
```

Solution:

Created the SQLAlchemy database tables inside the Kubernetes PostgreSQL database.

---

### Problem 3 — Port 8000 was already occupied

Error:

```text
Only one usage of each socket address is normally permitted
```

Solution:

Used another local port:

```text
localhost:8001
```

with Kubernetes port forwarding.

---

### Problem 4 — Job remained queued

Cause:

The Kubernetes worker and scheduler had not yet been deployed.

Solution:

Deployed:

```text
taskscale-worker
taskscale-scheduler
```

The queued job was then successfully processed.

---

# 12. Day 28 Result

**Day 28 — COMPLETED**

Kubernetes successfully runs the TaskScale AI distributed execution system.

Verified components:

```text
Kubernetes       ✓
PostgreSQL       ✓
Redis            ✓
FastAPI Backend  ✓
Scheduler        ✓
Worker           ✓
Job Creation     ✓
Job Processing   ✓
Job Completion   ✓
Statistics       ✓
```

The Kubernetes environment successfully processed a real TaskScale job from creation to completion.

---

## Key Learning

Day 28 demonstrated that TaskScale AI is not dependent on running everything directly on the local machine.

The system can run as separate Kubernetes workloads:

```text
Backend
PostgreSQL
Redis
Scheduler
Worker
```

and these components can communicate through Kubernetes services.

This completes **Phase 8 — Infrastructure**, specifically the Docker/Kubernetes deployment portion. The master specification also lists worker scaling, autoscaling, and cloud deployment as Phase 8 items; those are separate future infrastructure tasks rather than claims that they were completed on Day 28. 
