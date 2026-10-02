# TaskScale AI

Fault-Tolerant Distributed Workflow and AI Execution Platform

## Overview

TaskScale AI is a distributed job execution platform designed to process computer tasks using multiple workers.

The platform accepts jobs through a FastAPI backend, places them into a Redis-based queue, and distributes them across multiple worker processes. PostgreSQL stores job and worker state, while Kubernetes manages deployment and worker scaling.

The system is designed to demonstrate distributed task execution, fault tolerance, worker recovery, horizontal scaling, observability, and load testing.

## Problem Statement

Modern applications may need to execute large numbers of independent tasks reliably and efficiently.

A single worker can become a bottleneck or a single point of failure. TaskScale AI addresses this by distributing jobs across multiple workers and providing mechanisms for:

- Distributed job execution
- Queue-based task processing
- Worker health monitoring
- Failed worker detection
- Job recovery
- Horizontal worker scaling
- Metrics and observability
- Load testing and performance analysis

## Architecture

```text
                    ┌─────────────────────┐
                    │       Client        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    FastAPI Backend  │
                    │     REST API        │
                    └───────┬───────┬─────┘
                            │       │
                  ┌─────────┘       └──────────┐
                  ▼                            ▼
          ┌───────────────┐            ┌───────────────┐
          │    Redis      │            │  PostgreSQL   │
          │ Job Queue     │            │ Job/Worker DB │
          └───────┬───────┘            └───────────────┘
                  │
                  ▼
        ┌──────────────────────┐
        │   Worker Pool        │
        │ ┌────┐ ┌────┐ ┌────┐ │
        │ │ W1 │ │ W2 │ │ W3 │ │
        │ └────┘ └────┘ └────┘ │
        │       ...             │
        └──────────┬─────────────┘
                   │
                   ▼
          ┌─────────────────┐
          │ Worker Monitor  │
          │ Failure Recovery│
          └─────────────────┘

        Kubernetes
        ├── Backend
        ├── Workers
        ├── Scheduler
        ├── Worker Monitor
        ├── PostgreSQL
        └── Redis

        Observability
        ├── Prometheus
        └── Grafana