# TaskScale AI — Day 20 Documentation

# Day 20 — Job Dependencies

## Objective

The goal of Day 20 was to implement job dependencies.

A job should be able to depend on another job and should not execute until its dependency has successfully completed.

This is an important part of the Phase 5 Advanced Distributed Systems features. The project specification describes a workflow as a sequence of jobs that depend on each other.

## 1. Problem

Before Day 20, jobs could be processed independently.

For example:

Job A
Job B
Job C

There was no relationship between them.

However, real applications often require jobs to execute in a specific order.

Example:

      Upload File
           ↓
      Extract Text
           ↓
      AI Processing
           ↓
      Generate Report

The project specification gives this type of multi-step workflow as a core concept.

Therefore, TaskScale needs a way for one job to depend on another job.

## 2. Solution

A depends_on field was added to the jobs table.

Example:

Job 115
depends_on = NULL

Job 116
depends_on = 115

This means:

Job 115
   ↓
Job 116

Job 116 cannot execute until Job 115 is completed.

## 3. Database Change

The jobs table was updated with:

depends_on

The database structure was verified using:

\d jobs

The resulting table contained:

depends_on | integer

This allows a job to reference another job by its ID.

## 4. API Support

The job creation API was updated to accept a dependency.

Example parent job:

{
  "type": "dependency_parent",
  "input": {
    "message": "Parent job"
  },
  "priority": 5,
  "idempotency_key": "day20-parent"
}

The parent does not have a dependency:

depends_on = null

A child job can then reference the parent:

{
  "type": "dependency_child",
  "input": {
    "message": "Child job"
  },
  "priority": 5,
  "depends_on": 115,
  "idempotency_key": "day20-child"
}

The API correctly returned:

depends_on: 115


## 5. Worker Dependency Checking

The worker now checks the dependency before processing a job.

### The basic flow is:
        
        Worker receives job
                ↓
        Does job have dependency?
                ↓
              Yes
                ↓
        Find parent job
                ↓
        Is parent COMPLETED?
              /       \
            No         Yes
            ↓           ↓
        Wait          Process
            ↓
        Retry
        
The worker checks:

if job.depends_on is not None:

Then it retrieves the parent job from PostgreSQL.

## 6. Parent Job Not Found

If the dependency does not exist, the child job cannot safely execute.

The worker marks the job as:

FAILED

and stores an error explaining that the dependency was not found.

This prevents the system from executing a job when its required input job does not exist.

## 7. Parent Job Not Completed

If the parent exists but is not yet completed, the worker does not execute the child.

Example:

Parent:
RUNNING

Child:
QUEUED

The worker prints:

Job 116 is waiting for dependency 115

The child is then placed back into the Redis Stream and its current message is acknowledged.

This allows the worker to continue processing other work instead of permanently holding the child job.

## 8. Successful Dependency Execution

When the parent reaches:

COMPLETED

the child can be processed normally.

The final flow becomes:

         Parent Job
             ↓
         RUNNING
             ↓
         COMPLETED
             ↓
         Child Job
             ↓
         RUNNING
             ↓
         COMPLETED
         
         
## 9. Testing

A new parent and child were created for testing.

Parent
Job 117
Type: day20_parent_test
Status: QUEUED
Child
Job 118
Type: day20_child_test
Status: QUEUED
Depends on: 117

The worker processed them in the correct order.

Worker output:

Job 117 is RUNNING
Job 117 is COMPLETED
ACK sent for job 117

Job 118 is RUNNING
Job 118 is COMPLETED
ACK sent for job 118

This proves that the child job was processed after the parent completed.

## 10. PostgreSQL Verification

The database was checked using:

SELECT id, type, status, depends_on
FROM jobs
WHERE id IN (115, 116)
ORDER BY id;

The result showed:

115 | dependency_parent | COMPLETED | NULL
116 | dependency_child  | COMPLETED | 115

This confirmed that the dependency relationship was stored correctly.

## 11. Redis Verification

After processing the jobs, Redis Streams were checked:

XPENDING taskscale:job_stream workers

Result:

(integer) 0

This confirms that there were no unacknowledged messages remaining in the worker consumer group.

## 12. Architecture

The dependency-aware execution flow is now:

             FastAPI
                ↓
           PostgreSQL
                ↓
        Redis Priority Queue
                ↓
            Scheduler
                ↓
          Redis Stream
                ↓
             Worker
                ↓
       Check dependency
          /          \
       Waiting      Completed
          ↓             ↓
     Redis Stream     Execute
                        ↓
                    PostgreSQL


## 13. Engineering Concepts Learned

Day 20 introduced the following distributed-system concepts:

Job dependencies
Parent/child jobs
Dependency validation
Ordered execution
Redis Stream requeueing
Worker-side dependency checking
PostgreSQL relationship between jobs
Workflow foundations

This moves TaskScale from simple independent job execution toward multi-step workflows.

The master specification explicitly requires support for multi-step workflows and identifies DAG-based workflows as a Phase 5 feature.

## 14. Result
Day 20 Status: ✅ COMPLETE

Implemented:

✅ depends_on database field
✅ API dependency support
✅ Parent job lookup
✅ Dependency validation
✅ Waiting for incomplete parent
✅ Child job requeue
✅ Parent → child execution order
✅ Redis Stream acknowledgement
✅ Dependency testing

The dependency system is now ready to be extended into DAG-based workflows.

## 15. Next Step

Day 21 — DAG Workflows

Day 20 supports a simple dependency:

A
↓
B

Day 21 will extend this into a DAG:

        A
       / \
      B   C
       \ /
        D

This will allow TaskScale to execute more complex multi-step workflows, which is the next advanced workflow capability specified for Phase 5.