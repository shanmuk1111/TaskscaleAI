# Cloud Deployment


## TaskScale AI — Day 31 Documentation
## Day 31 — Cloud Deployment on AWS EKS

### 1. Objective

The objective of Day 31 was to deploy the TaskScale AI system to a **cloud Kubernetes environment using AWS EKS**.

The goal was to move the application from the local Docker Desktop Kubernetes environment to AWS and verify that the distributed job-processing system works in the cloud.

---

## 2. AWS Setup

AWS CLI was installed and configured.

The AWS region used for the deployment was:

```text
eu-north-1
```

The AWS Kubernetes cluster was created and the Kubernetes context was connected to the EKS cluster.

The cluster node was verified using:

```powershell
kubectl get nodes
```

The node showed:

```text
STATUS: Ready
VERSION: v1.36.4-eks
```

This confirmed that the Kubernetes cluster was successfully running on AWS.

---

## 3. AWS ECR

Because the Kubernetes workers in AWS cannot use the local Docker images from the development machine, the application images were uploaded to **Amazon Elastic Container Registry (ECR)**.

The following images were used:

```text
taskscale-backend
taskscale-worker
taskscale-scheduler
```

The worker image was successfully available from:

```text
098474709926.dkr.ecr.eu-north-1.amazonaws.com/taskscale-worker:latest
```

The Kubernetes worker pod confirmed that it was running this ECR image.

---

## 4. AWS Kubernetes Deployment

The TaskScale AI components were deployed into the `taskscale` namespace.

The final deployment contained:

```text
AWS EKS
│
├── Backend
├── PostgreSQL
├── Redis
├── Scheduler
└── Worker
```

Final pod status:

```text
Backend       1/1 Running
PostgreSQL    1/1 Running
Redis         1/1 Running
Scheduler     1/1 Running
Worker        1/1 Running
```

This confirmed that all major TaskScale AI components were running successfully in AWS.

---

## 5. Redis Connection Fix

During cloud deployment, the backend initially failed when trying to access Redis.

The problem was caused by the Redis client using:

```text
localhost
```

Inside Kubernetes, `localhost` refers to the current pod, not the Redis pod.

The Redis client was updated to use environment variables:

```python
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
    socket_timeout=None,
    socket_connect_timeout=5
)
```

The Kubernetes environment provided:

```text
REDIS_HOST=redis
REDIS_PORT=6379
```

This allowed the backend and worker to communicate with the Redis Kubernetes service correctly.

---

## 6. Worker Scheduling Issue

The AWS node was a small instance and temporarily reached its pod capacity.

Kubernetes reported that another worker could not be scheduled because there were:

```text
Too many pods
```

The worker deployment was temporarily reduced to one replica so that the required application components could run on the available node.

After this adjustment, the final system successfully ran:

```text
1 Backend
1 PostgreSQL
1 Redis
1 Scheduler
1 Worker
```

---

## 7. HPA Configuration

The TaskScale worker continued to have a Kubernetes Horizontal Pod Autoscaler configured.

The HPA configuration was:

```text
Minimum replicas: 1
Maximum replicas: 5
CPU target: 70%
```

Verification:

```powershell
kubectl get hpa -n taskscale
```

The HPA showed:

```text
MINPODS: 1
MAXPODS: 5
REPLICAS: 1
```

The HPA was therefore available for worker scaling in the AWS Kubernetes environment.

---

## 8. AWS Job Test

A test job was submitted through the TaskScale API:

```json
{
  "type": "aws_cloud_test",
  "input": {
    "message": "TaskScale running on AWS EKS"
  }
}
```

The job was initially:

```text
QUEUED
```

The worker picked up the job and processed it.

The final result was:

```text
Job ID:       1
Type:         aws_cloud_test
Status:       COMPLETED
Retry Count:  0
Worker ID:    worker-970805c6
```

The `/jobs` API successfully returned the completed job.

This verified the complete cloud execution path:

```text
Client
   ↓
AWS EKS Backend
   ↓
PostgreSQL
   ↓
Redis
   ↓
Worker
   ↓
Job Execution
   ↓
PostgreSQL Result
```

---

## 9. Problems Encountered

### Problem 1 — AWS authentication

AWS CLI authentication initially failed because the configured credentials were invalid.

The AWS authentication was corrected before continuing with the cloud deployment.

### Problem 2 — Local Docker images unavailable to EKS

The local Docker images could not directly be used by the AWS Kubernetes nodes.

**Solution:** Images were pushed to Amazon ECR.

### Problem 3 — Redis connection

The application initially attempted to connect to Redis through `localhost`.

**Solution:** Kubernetes service configuration was used:

```text
REDIS_HOST=redis
REDIS_PORT=6379
```

### Problem 4 — Worker pod pending

The worker pod temporarily remained in `Pending` because the EKS node reached its pod capacity.

**Solution:** The worker deployment was reduced to one replica for the final cloud verification.

---

## 10. Final Architecture

```text
                    AWS
                     │
                 Amazon EKS
                     │
        ┌────────────┼────────────┐
        │            │            │
     Backend      Scheduler     Worker
        │                         │
        ├──────────┐              │
        │          │              │
     Redis     PostgreSQL ◄───────┘
        │
   Job Queue
```

Container images were stored in:

```text
Amazon ECR
```

---

## 11. Verification Checklist

| Component   | Status     |
| ----------- | ---------- |
| AWS CLI     | Completed  |
| AWS EKS     | Running    |
| EKS Node    | Ready      |
| Amazon ECR  | Completed  |
| Backend     | Running    |
| PostgreSQL  | Running    |
| Redis       | Running    |
| Scheduler   | Running    |
| Worker      | Running    |
| HPA         | Configured |
| Cloud API   | Working    |
| Cloud Job   | Completed  |
| Job Result  | Stored     |
| Retry Count | 0          |

---

# Day 31 Final Status

**Day 31 — COMPLETED**

The TaskScale AI system was successfully deployed to **AWS EKS**, with its container images stored in **Amazon ECR**. The backend, scheduler, worker, PostgreSQL, and Redis components were running in the AWS Kubernetes environment, and an actual job was submitted through the API and successfully completed.

**Phase 8 — Infrastructure / Cloud Deployment: COMPLETED**
