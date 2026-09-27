# Day 35 Documentation — Prometheus & Grafana Observability

## 1. Objective

The objective of Day 35 was to add **monitoring and observability** to the TaskScale AI Kubernetes deployment.

The goal was to deploy Prometheus and Grafana and connect them to the existing TaskScale backend and worker metrics.

---

## 2. Initial System Check

First, the Kubernetes cluster was checked for existing monitoring components.

### Namespaces

```powershell
kubectl get namespace
```

The cluster contained:

```text
default
kube-node-lease
kube-public
kube-system
local-path-storage
taskscale
```

There was initially **no monitoring namespace**.

### ServiceMonitor Check

```powershell
kubectl get servicemonitor -A
```

Initially this returned:

```text
error: the server doesn't have a resource type "servicemonitor"
```

This confirmed that the Prometheus Operator CRDs were not installed.

### Prometheus/Grafana Check

```powershell
kubectl get pods -A | Select-String "prometheus|grafana"
```

No Prometheus or Grafana pods were present.

---

## 3. Helm Verification

Helm was already installed and working.

```powershell
helm version
```

Result:

```text
Version: v4.3.0
Kubernetes: v1.37
```

Therefore, Helm was used to install the monitoring stack.

---

## 4. Prometheus Helm Repository

The Prometheus Community Helm repository was already configured.

```powershell
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
```

The repository was then updated:

```powershell
helm repo update
```

The update completed successfully.

---

## 5. Installing Prometheus and Grafana

The Kubernetes monitoring stack was installed using:

```powershell
helm install monitoring prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace
```

Installation result:

```text
NAME: monitoring
NAMESPACE: monitoring
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
```

This installed the `kube-prometheus-stack`, which provides the main monitoring components required by TaskScale.

---

## 6. Monitoring Components

The monitoring namespace was verified:

```powershell
kubectl get pods -n monitoring
```

The following components became healthy:

```text
Prometheus
Grafana
Alertmanager
Prometheus Operator
kube-state-metrics
Node Exporter
```

Final status:

```text
alertmanager                         2/2 Running
grafana                              3/3 Running
prometheus-operator                  1/1 Running
kube-state-metrics                   1/1 Running
node-exporter                        1/1 Running
prometheus                            2/2 Running
```

This confirmed that the monitoring stack was successfully deployed.

---

## 7. ServiceMonitor Support

After installing the Prometheus Operator, the `ServiceMonitor` resource became available:

```powershell
kubectl get servicemonitor -A
```

The monitoring stack created its own ServiceMonitors for Kubernetes components.

Examples included:

```text
monitoring-grafana
monitoring-kube-state-metrics
monitoring-prometheus
monitoring-prometheus-node-exporter
monitoring-kubelet
```

---

## 8. TaskScale ServiceMonitors

TaskScale already contained ServiceMonitor configuration files:

```text
k8s/backend-servicemonitor.yaml
k8s/worker-servicemonitor.yaml
```

They were applied using:

```powershell
kubectl apply -f k8s/backend-servicemonitor.yaml
kubectl apply -f k8s/worker-servicemonitor.yaml
```

Result:

```text
servicemonitor.monitoring.coreos.com/taskscale-backend created
servicemonitor.monitoring.coreos.com/taskscale-worker created
```

The ServiceMonitors were created in the `monitoring` namespace.

Verification:

```powershell
kubectl get servicemonitor -A | Select-String "taskscale"
```

Result:

```text
monitoring   taskscale-backend
monitoring   taskscale-worker
```

This confirmed that Prometheus now has ServiceMonitor definitions for the TaskScale backend and workers.

---

## 9. Grafana Access

Grafana was exposed locally using Kubernetes port forwarding:

```powershell
kubectl port-forward svc/monitoring-grafana 3000:80 -n monitoring
```

The command successfully returned:

```text
Forwarding from 127.0.0.1:3000 -> 3000
```

Grafana can therefore be accessed through:

```text
http://localhost:3000
```

The default Grafana username is:

```text
admin
```

The administrator password can be retrieved from the Kubernetes secret.

---

## 10. Architecture After Day 35

The monitoring architecture is now:

```text
                 TaskScale Kubernetes Cluster
                           │
             ┌─────────────┴─────────────┐
             │                           │
       TaskScale Backend            TaskScale Workers
             │                           │
             │ Metrics                   │ Metrics
             └─────────────┬─────────────┘
                           │
                    ServiceMonitors
                           │
                           ▼
                      Prometheus
                           │
                           ▼
                        Grafana
```

Prometheus collects metrics, while Grafana provides the visualization layer.

---

## 11. What Was Completed

### Completed

* [x] Checked existing Kubernetes monitoring
* [x] Verified Helm
* [x] Added/updated Prometheus Community repository
* [x] Installed kube-prometheus-stack
* [x] Created monitoring namespace
* [x] Installed Prometheus
* [x] Installed Grafana
* [x] Installed Alertmanager
* [x] Installed Prometheus Operator
* [x] Installed Node Exporter
* [x] Installed kube-state-metrics
* [x] Enabled ServiceMonitor resources
* [x] Created TaskScale backend ServiceMonitor
* [x] Created TaskScale worker ServiceMonitor
* [x] Exposed Grafana locally

---

## 12. Result

Day 35 successfully added the **observability foundation** to TaskScale AI.

The project now has a monitoring stack capable of collecting and visualizing application and Kubernetes metrics. The TaskScale backend and worker services have been registered through ServiceMonitors so that their Prometheus metrics can be monitored.

The next observability step is to **verify the actual TaskScale metrics in Prometheus and build a custom Grafana dashboard** for jobs, queue size, worker activity, retries, failures, and job duration.

