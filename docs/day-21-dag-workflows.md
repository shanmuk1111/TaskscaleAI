# Day 21 — DAG-Based Workflow

## Objective

Implement DAG-based workflows so that one job can depend on multiple parent jobs.

A DAG allows jobs to form a workflow where a child job starts only after its required parent jobs are completed.

---

# What We Implemented

## 1. Multiple Dependencies

Added support for multiple job dependencies using the `dependencies` field.

Example:

{
    "type": "dag_child",
    "dependencies": [123, 124]
}


This means Job 125 depends on Jobs 123 and 124.

## 2. Database Support

Added the following column to the jobs table:

dependencies JSONB

Default value:

[]

This allows a job to store multiple dependency IDs.

## 3. Dependency Checking

The worker checks the dependencies before executing a job.

Example:

Job 123 ─────┐
             ├──> Job 125
Job 124 ─────┘

Job 125 can execute only when:

Job 123 = COMPLETED
Job 124 = COMPLETED
Testing

### Test 1 — Two Parent Jobs

Created:

Job 123 → dag_parent_1
Job 124 → dag_parent_2
Job 125 → dag_child

Job 125 dependencies:

[123, 124]

Result:

123 → COMPLETED
124 → COMPLETED
125 → COMPLETED

Database verification confirmed:

123 | dag_parent_1 | COMPLETED | []
124 | dag_parent_2 | COMPLETED | []
125 | dag_child    | COMPLETED | [123,124]

### Test 2 — Child Waiting for Dependency

Created a child job that depended on another job that was not yet completed.

Worker output:

Job 138 is waiting for dependencies: [136]

The child did not execute while the dependency was incomplete.

After the dependency completed, the child was released.

### Test 3 — Dependency Release

Created:

Job 139 → Parent
Job 140 → Child

Job 140 depended on Job 139.

Worker output:

Job 139 is RUNNING
Job 139 is COMPLETED
Dependent job 140 released after job 139 completed
Job 140 is RUNNING
Job 140 is COMPLETED

This confirmed that the dependency workflow works correctly.

### Test 4 — Duplicate Execution Protection

Job 140 was received again by the worker.

The worker detected:

Job 140 is already COMPLETED. Skipping duplicate execution.

Then:

ACK sent for duplicate job 140

This confirmed that DAG workflows continue to use the existing duplicate execution protection.

Redis Verification

Checked:

XPENDING taskscale:job_stream workers

Result:

0

All processed messages were acknowledged.

Architecture
Parent Job 1 ─────┐
                  │
                  ├────> Child Job
                  │
Parent Job 2 ─────┘
                         │
                         ↓
                       Worker
                         │
                         ↓
                     COMPLETED

The child executes only after all required parents are completed.

Result

Day 21 successfully implemented DAG-based workflows.

TaskScale AI can now:

Support multiple dependencies
Store dependencies in PostgreSQL
Check dependency status
Wait for incomplete dependencies
Release child jobs after dependencies complete
Process DAG child jobs
Prevent duplicate execution
ACK processed Redis Stream messages