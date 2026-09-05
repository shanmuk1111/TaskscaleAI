# Day 13 — Database Transactions

## Objective

Understand and implement proper database transaction handling in TaskScale AI.

The main goals were:

- Understand database transactions
- Understand `COMMIT`
- Understand `ROLLBACK`
- Handle database failures safely
- Test both successful and failed database operations
- Verify that failed transactions do not leave unwanted data in PostgreSQL

---

# 1. What is a Database Transaction?

A database transaction is a group of database operations treated as one unit of work.

A successful transaction follows:

        BEGIN
          ↓
        Database changes
          ↓
        COMMIT

If something goes wrong:

        BEGIN
          ↓
        Database changes
          ↓
        ERROR
          ↓
        ROLLBACK

The rollback removes the uncommitted changes from the current transaction.

## 2. Important SQLAlchemy Operations
db.add()
db.add(new_job)

Adds an object to the current SQLAlchemy transaction.

It does not mean that the change is permanently saved yet.

db.commit()
db.commit()

Makes the changes in the current transaction permanent in PostgreSQL.

db.rollback()
db.rollback()

Undoes uncommitted changes when a database operation fails.

A rollback cannot undo changes that were already committed.

db.refresh()
db.refresh(new_job)

Reloads the object from PostgreSQL after the database operation.

This is useful for getting database-generated values such as the newly created job ID.

## 3. Existing Database Configuration

TaskScale already uses SQLAlchemy sessions in:

app/database/database.py

The session configuration is:

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

autocommit=False means that database changes are explicitly committed by the application.

The application controls when to use:

db.commit()

and:

db.rollback()

## 4. Problem in the Original Job Creation Code

The original code was:

db.add(new_job)
db.commit()
db.refresh(new_job)

redis_client.xadd(
    "taskscale:job_stream",
    {
        "job_id": str(new_job.id)
    }
)

The PostgreSQL operation was not protected by explicit exception handling.

If the database operation failed, the session could remain in a failed transaction state.

## 5. Transaction Handling Added

The database operation was changed to:

try:
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
except Exception:
    db.rollback()
    raise

The flow is now:

        Create Job
            ↓
        db.add()
            ↓
        db.commit()
            ↓
        Success

If an error occurs:

        Create Job
            ↓
        db.add()
            ↓
        db.commit()
            ↓
        Database Error
            ↓
        db.rollback()
            ↓
        Raise Error

## 6. Why rollback() is Important

Suppose the database operation fails.

        Without rollback:

        Database Error
            ↓
        SQLAlchemy session remains in failed transaction state

With rollback:

        Database Error
            ↓
        db.rollback()
            ↓
        Uncommitted changes are discarded
            ↓
        Session can be used safely again


## 7. Normal Transaction Test

A normal job was created through the FastAPI Swagger UI.

The job successfully followed the TaskScale workflow:

        FastAPI
           ↓
        PostgreSQL
           ↓
        Redis Stream
           ↓
        Worker
           ↓
        RUNNING
           ↓
        COMPLETED
           ↓
        XACK

The worker output showed:

Worker ... picked up job 73
Job 73 is RUNNING
Job 73 is COMPLETED
ACK sent for job 73

This confirmed that the transaction change did not break the normal job execution flow.

## 8. Failed Transaction Test

A failure was intentionally created by sending a type value longer than the database allows.

The database model contains:

type = Column(String(100), nullable=False)

A value longer than 100 characters was submitted.

The API returned:

500 Internal Server Error

This was expected for the test because the current API does not yet provide custom database error responses.

## 9. PostgreSQL Verification

After the failed request, PostgreSQL was checked using:

SELECT id, type, idempotency_key
FROM jobs
WHERE idempotency_key = 'transaction-test-001';

The result was:

(0 rows)

This confirmed that the failed database operation did not leave the job stored in PostgreSQL.

The transaction behaved as expected:

    db.add()
      ↓
    db.commit()
      ↓
    ERROR
      ↓
    db.rollback()
      ↓
    Job not stored

## 10. PostgreSQL and Redis Are Separate

An important distributed-systems lesson from Day 13 is that:

PostgreSQL transaction
        ≠
Redis operation

For example:

db.commit()

redis_client.xadd(...)

The PostgreSQL transaction cannot automatically roll back a Redis operation.

If PostgreSQL commits successfully but Redis fails:

PostgreSQL → Job saved ✅
Redis      → Job not added ❌

This is a distributed consistency problem.

It is different from a normal PostgreSQL transaction problem.

## 11. What We Implemented

Day 13 implemented explicit rollback handling around PostgreSQL job creation:

try:
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
except Exception:
    db.rollback()
    raise

No changes were made to the Redis Stream operation during this step.

## 12. Day 13 Testing
Test 1 — Normal Job

Result:

Job created successfully
Worker received job
Job became RUNNING
Job became COMPLETED
Redis ACK sent

Status:

PASS
Test 2 — Database Failure

Result:

500 Internal Server Error

PostgreSQL verification:

(0 rows)

Status:

PASS


## 13. What I Learned

By the end of Day 13:

A transaction groups database changes into one unit of work.
db.add() adds an object to the current transaction.
db.commit() permanently saves the transaction.
db.rollback() removes uncommitted changes after a failure.
db.refresh() reloads database values into the SQLAlchemy object.
PostgreSQL transactions do not automatically include Redis.
A committed database change cannot be undone by a later rollback.
Worker failure recovery from previous days is still necessary because a worker can crash after committing RUNNING.


## 14. Day 13 Status
Database Transactions
        ↓
Understanding        ✅
Implementation       ✅
Normal Test          ✅
Failure Test         ✅
PostgreSQL Verify    ✅
Day 13 — COMPLETED ✅