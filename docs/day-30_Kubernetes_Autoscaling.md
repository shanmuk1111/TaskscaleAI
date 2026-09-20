# Day 30 — Kubernetes Autoscaling

## Objective

The objective of Day 30 was to implement **automatic worker scaling using Kubernetes Horizontal Pod Autoscaler (HPA)**.

The system should automatically increase or decrease the number of worker pods based on CPU utilization.

---

## 1. Metrics Server Setup

First, Kubernetes Metrics Server was installed.

The initial Metrics Server pod was running but not ready:

```text
0/1 Running
```

The logs showed a kubelet certificate verification problem:

```text
tls: failed to verify certificate
x509: cannot validate certificate
because it doesn't contain any IP SANs
```

For the local Docker Desktop Kubernetes environment, the Metrics Server was configured with:

```text
--kubelet-insecure-tls
```

After the configuration, Metrics Server successfully provided resource metrics.

### Verification

```powershell
kubectl top nodes
```

Output included:

```text
NAME                    CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)
desktop-control-plane   990m         24%      1488Mi          39%
```

This confirmed that Kubernetes could collect CPU and memory metrics.

---

## 2. Worker Metrics Verification

Worker pod metrics were checked using:

```powershell
kubectl top pods -n taskscale
```

Example result:

```text
taskscale-worker-...   22m   43Mi
taskscale-worker-...    7m   42Mi
taskscale-worker-...   27m   42Mi
```

This confirmed that CPU and memory metrics were available for the TaskScale workers.

---

## 3. Configure Worker Resources

The worker Deployment initially had no resource requests:

```text
{}
```

CPU requests are required for CPU-utilization-based HPA calculations.

The worker Deployment was therefore configured with:

```yaml
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "256Mi"
```

The configuration was verified successfully.

---

## 4. Create Horizontal Pod Autoscaler

A new Kubernetes manifest was created:

```text
k8s/worker-hpa.yaml
```

Configuration:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: taskscale-worker-hpa
  namespace: taskscale
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: taskscale-worker
  minReplicas: 1
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

The HPA was created using:

```powershell
kubectl apply -f worker-hpa.yaml
```

Result:

```text
horizontalpodautoscaler.autoscaling/taskscale-worker-hpa created
```

---

## 5. Verify HPA Metrics

The HPA was checked with:

```powershell
kubectl describe hpa taskscale-worker-hpa -n taskscale
```

It successfully detected CPU metrics:

```text
resource cpu on pods (as a percentage of request): 9% (9m) / 70%
```

The HPA condition showed:

```text
ScalingActive True
Reason: ValidMetricFound
```

This confirmed that the HPA could successfully calculate the required replica count.

---

# 6. Scale-Down Test

The worker Deployment initially had three replicas.

The HPA was configured with:

```text
Minimum replicas: 1
Maximum replicas: 5
```

When CPU usage remained below the target, Kubernetes automatically reduced the worker replicas:

```text
3 workers
    ↓
2 workers
    ↓
1 worker
```

Final verification:

```text
taskscale-worker   1/1   1   1
```

This successfully demonstrated **automatic scale-down**.

---

# 7. Scale-Up Test

Normal TaskScale jobs mainly use `sleep()`, so they do not necessarily create enough CPU load to trigger CPU-based autoscaling.

For the HPA test, intentional CPU load was generated inside the worker:

```powershell
kubectl exec deployment/taskscale-worker -n taskscale -- python -c "while True: pass"
```

The HPA then detected high CPU utilization.

Example:

```text
TARGETS
cpu: 135%/70%
```

The HPA automatically increased the worker replicas.

Final result:

```text
taskscale-worker-hpa
CPU:      106%/70%
Replicas: 5
```

Worker Deployment:

```text
taskscale-worker   5/5   5   5
```

Therefore:

```text
1 worker → 5 workers
```

was successfully demonstrated.

---

# 8. Final Day 30 Architecture

The autoscaling flow is:

```text
                    Kubernetes Cluster
                           |
                           v
                  Metrics Server
                           |
                           v
                    CPU Metrics
                           |
                           v
                Horizontal Pod Autoscaler
                     /             \
                    /               \
             CPU < 70%           CPU > 70%
                  |                   |
                  v                   v
            Scale Down            Scale Up
                  |                   |
                  v                   v
             1 Worker             Up to 5 Workers
```

The HPA controls:

```text
Deployment: taskscale-worker
Minimum:    1 replica
Maximum:    5 replicas
CPU Target: 70%
```

---

# 9. Problems Encountered

### Problem 1 — Metrics Server not ready

Metrics Server initially showed:

```text
0/1 Running
```

The logs showed a kubelet certificate validation error.

**Solution:** configured:

```text
--kubelet-insecure-tls
```

for the local Kubernetes environment.

---

### Problem 2 — Worker had no resource requests

The worker Deployment returned:

```text
{}
```

for its resource configuration.

**Solution:** added CPU and memory requests/limits.

---

### Problem 3 — HPA initially showed unknown CPU

Initially:

```text
cpu: <unknown>/70%
```

After Metrics Server and worker resource configuration were working, the HPA successfully reported CPU utilization.

---

# 10. Day 30 Verification

| Component            | Status     |
| -------------------- | ---------- |
| Metrics Server       | Working    |
| `kubectl top nodes`  | Working    |
| `kubectl top pods`   | Working    |
| Worker CPU requests  | Configured |
| HPA                  | Created    |
| Minimum replicas     | 1          |
| Maximum replicas     | 5          |
| CPU target           | 70%        |
| Automatic scale-down | Verified   |
| Automatic scale-up   | Verified   |
| Maximum 5 workers    | Verified   |

---

# Day 30 Status

**Day 30 — COMPLETED**

TaskScale AI now supports **Kubernetes-based automatic worker scaling**, with workers automatically scaling between **1 and 5 replicas** according to CPU utilization.
