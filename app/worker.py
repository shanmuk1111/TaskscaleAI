import time
import uuid
import threading

from app.database.database import SessionLocal
from app.models.job import Job
from app.models.worker import Worker
from app.queue.redis_client import redis_client
import redis

# --------------------------------
# Worker identity
# --------------------------------

worker_id = f"worker-{uuid.uuid4().hex[:8]}"

print(f"Worker started: {worker_id}")


# --------------------------------
# Register worker
# --------------------------------

db = SessionLocal()

try:
    worker = Worker(
        worker_id=worker_id,
        status="ALIVE"
    )

    db.add(worker)
    db.commit()

    print(f"Worker {worker_id} registered")

finally:
    db.close()

# Initialize Redis Stream and consumer group
STREAM_NAME = "taskscale:job_stream"
GROUP_NAME = "workers"

try:
    redis_client.xgroup_create(
        name=STREAM_NAME,
        groupname=GROUP_NAME,
        id="0",
        mkstream=True
    )
    print(f"Redis consumer group '{GROUP_NAME}' created")
except redis.exceptions.ResponseError as e:
    if "BUSYGROUP" in str(e):
        print(f"Redis consumer group '{GROUP_NAME}' already exists")
    else:
        raise
    
    
# --------------------------------
# Heartbeat function
# --------------------------------

def send_heartbeat():
    while True:
        db = SessionLocal()

        try:
            worker = (
                db.query(Worker)
                .filter(Worker.worker_id == worker_id)
                .first()
            )

            if worker:
                worker.last_heartbeat = func.now()
                worker.status = "ALIVE"

                db.commit()

                print(f"Heartbeat sent: {worker_id}")

        except Exception as e:
            db.rollback()
            print(f"Heartbeat error: {e}")

        finally:
            db.close()

        time.sleep(3)


# --------------------------------
# Start heartbeat thread
# --------------------------------

from sqlalchemy.sql import func

heartbeat_thread = threading.Thread(
    target=send_heartbeat,
    daemon=True
)

heartbeat_thread.start()


def fail_dependent_jobs(db, failed_job_id):
    dependent_jobs = (
        db.query(Job)
        .filter(Job.status == "QUEUED")
        .all()
    )

    for dependent_job in dependent_jobs:

        dependency_ids = [
            dep_id
            for dep_id in (dependent_job.dependencies or [])
            if dep_id != 0
        ]

        if (
            dependent_job.depends_on is not None
            and dependent_job.depends_on != 0
        ):
            dependency_ids.append(dependent_job.depends_on)

        if failed_job_id in dependency_ids:

            dependent_job.status = "FAILED"

            dependent_job.error = (
                f"Dependency job {failed_job_id} failed"
            )

            db.commit()

            print(
                f"Dependent job {dependent_job.id} "
                f"marked FAILED because job "
                f"{failed_job_id} failed"
            )

            # Continue propagation
            fail_dependent_jobs(
                db,
                dependent_job.id
            )

# --------------------------------
# Job processing
# --------------------------------

while True:
    job = None

    try:
        result = redis_client.xreadgroup(
        groupname="workers",
        consumername=worker_id,
        streams={STREAM_NAME: ">"},
        count=1,
        block=5000
        )

        if not result:
            print("Worker is waiting for a job...")
            continue

        stream_name, messages = result[0]

        for message_id, message_data in messages:
            job_id = int(message_data["job_id"])

            print(
                f"Worker {worker_id} picked up job {job_id} "
                f"(message {message_id})"
            )

            db = SessionLocal()
            job = None

            try:
                job = db.query(Job).filter(Job.id == int(job_id)).first()

                if job is None:
                    print(f"Job {job_id} was not found in PostgreSQL")

                    redis_client.xack(
                        STREAM_NAME,
                        GROUP_NAME,
                        message_id
                    )

                    continue

                # Duplicate execution protection
                if job.status == "COMPLETED":
                    print(
                        f"Job {job.id} is already COMPLETED. "
                        f"Skipping duplicate execution."
                    )

                    redis_client.xack(
                        STREAM_NAME,
                        GROUP_NAME,
                        message_id
                    )

                    print(f"ACK sent for duplicate job {job.id}")
                    continue
                
                # --------------------------------
                # Check job dependencies
                # --------------------------------
                dependencies = job.dependencies or []

                dependency_ids = []

                # Treat 0 as no dependency
                if job.depends_on is not None and job.depends_on != 0:
                    dependency_ids.append(job.depends_on)

                if job.dependencies:
                    dependency_ids.extend(
                        dep_id for dep_id in job.dependencies
                        if dep_id != 0
                    )

                # Remove duplicates
                dependency_ids = list(set(dependency_ids))

                if dependency_ids:

                    parent_jobs = (
                        db.query(Job)
                        .filter(Job.id.in_(dependency_ids))
                        .all()
                    )

                    found_ids = {parent.id for parent in parent_jobs}

                    # Dependency does not exist
                    missing_ids = set(dependency_ids) - found_ids

                    if missing_ids:
                        print(
                            f"Job {job.id} has missing dependencies: "
                            f"{list(missing_ids)}"
                        )

                        job.status = "FAILED"
                        job.error = (
                            f"Dependency jobs not found: {list(missing_ids)}"
                        )

                        db.commit()

                        redis_client.xack(
                        STREAM_NAME,
                        GROUP_NAME,
                        message_id
                        )

                        continue

                    # Dependencies exist but are not completed
                    # Check for failed dependencies
                    failed_dependencies = [
                        parent.id
                        for parent in parent_jobs
                        if parent.status == "FAILED"
                    ]

                    if failed_dependencies:
                        print(
                            f"Job {job.id} has failed dependencies: "
                            f"{failed_dependencies}"
                        )

                        job.status = "FAILED"
                        job.error = (
                            f"Dependency jobs failed: {failed_dependencies}"
                        )

                        db.commit()

                        redis_client.xack(
                                                STREAM_NAME,
                                                GROUP_NAME,
                                                message_id
                                                )

                        print(
                            f"Job {job.id} marked FAILED because "
                            f"its dependencies failed"
                        )

                        continue


                    # Dependencies are still running or queued
                    incomplete_dependencies = [
                        parent.id
                        for parent in parent_jobs
                        if parent.status != "COMPLETED"
                    ]

                    if incomplete_dependencies:
                        print(
                            f"Job {job.id} is waiting for dependencies: "
                            f"{incomplete_dependencies}"
                        )

                        # Keep job QUEUED.
                        # Do not immediately put it back into Redis.
                        redis_client.xack(
                                                STREAM_NAME,
                                                GROUP_NAME,
                                                message_id
                                                )

                        continue
                    
                # --------------------------------
                # Atomic job claim
                # --------------------------------

                claim_result = (
                    db.query(Job)
                    .filter(
                        Job.id == job.id,
                        Job.status == "QUEUED"
                    )
                    .update(
                        {
                            Job.worker_id: worker_id,
                            Job.status: "RUNNING"
                        },
                        synchronize_session=False
                    )
                )

                db.commit()

                if claim_result == 0:
                    print(
                        f"Job {job.id} could not be claimed. "
                        f"Another worker may already own it."
                    )

                    redis_client.xack(
                                            STREAM_NAME,
                                            GROUP_NAME,
                                            message_id
                                            )

                    continue

                print(f"Job {job.id} is RUNNING")

                # --------------------------------
                # Job processing
                # --------------------------------

                if job.input.get("fail_once") and job.retry_count == 0:
                    raise Exception("Simulated temporary failure")

                if job.input.get("force_fail"):
                    raise Exception("Simulated permanent failure")


                # --------------------------------
                # AI workload
                # --------------------------------

                if job.type == "ai_summarization":

                    text = job.input.get("text", "")

                    if not text:
                        raise Exception("AI summarization requires text input")

                    print(
                        f"AI summarization started for job {job.id}"
                    )

                    # Temporary AI processing simulation.
                    # Real AI model integration will be added later.

                    time.sleep(3)

                    summary = (
                        text[:200] +
                        ("..." if len(text) > 200 else "")
                    )

                    job.result = {
                        "job_type": "ai_summarization",
                        "summary": summary,
                        "job_id": job.id,
                        "worker_id": worker_id
                    }

                    print(
                        f"AI summarization completed for job {job.id}"
                    )


                # --------------------------------
                # Normal workload
                # --------------------------------

                else:

                    time.sleep(5)

                    job.result = {
                        "message": "Job processed successfully",
                        "job_id": job.id,
                        "worker_id": worker_id
                    }

                # --------------------------------
                # Job succeeded
                # --------------------------------

                job.status = "COMPLETED"
                job.completed_at = func.now()
                
                db.commit()

                # --------------------------------
                # Wake up dependent jobs
                # --------------------------------

                dependent_jobs = (
                    db.query(Job)
                    .filter(
                        Job.status == "QUEUED",
                        (
                            Job.depends_on == job.id
                        ) | (
                            Job.dependencies.contains([job.id])
                        )
                    )
                    .all()
                )

                for dependent_job in dependent_jobs:
                    redis_client.xadd(
                        STREAM_NAME,
                        {"job_id": str(dependent_job.id)}
                    )

                    print(
                        f"Dependent job {dependent_job.id} "
                        f"released after job {job.id} completed"
                    )

                # ACK only after successful processing
                redis_client.xack(
                    STREAM_NAME,
                    "workers",
                    message_id
                )

                print(
                    f"Job {job.id} is COMPLETED"
                )

                print(
                    f"ACK sent for job {job.id}"
                )

            except Exception as e:

                db.rollback()

                if job is not None:

                    job.retry_count += 1
                    job.error = str(e)

                    if job.retry_count < job.max_retries:

                        # Put the job back into QUEUED state
                        # so another worker attempt can claim it.
                        job.status = "QUEUED"
                        job.worker_id = None

                        db.commit()

                        print(
                            f"Job {job.id} failed. "
                            f"Retry {job.retry_count}/{job.max_retries}"
                        )

                        time.sleep(2)

                        # Put retry into the Stream
                        redis_client.xadd(
                            STREAM_NAME,
                            {
                                "job_id": str(job.id)
                            }
                        )

                        # ACK the failed attempt
                        redis_client.xack(
                        STREAM_NAME,
                        GROUP_NAME,
                        message_id
                        )

                        print(
                            f"Job {job.id} added back to Redis Stream"
                        )

                        # ACK the failed attempt
                        redis_client.xack(
                        STREAM_NAME,
                        GROUP_NAME,
                        message_id
                        )

                        print(
                            f"Job {job.id} added back to Redis Stream"
                        )

                    else:

                        job.status = "FAILED"
                        db.commit()

                        print(
                            f"Job {job.id} permanently FAILED"
                        )

                        # Propagate failure to dependent jobs
                        fail_dependent_jobs(
                            db,
                            job.id
                        )

                        # Put permanently failed job into DLQ
                        redis_client.rpush(
                            "taskscale:dead_letters",
                            str(job.id)
                        )

                        # ACK the original Stream message
                        redis_client.xack(
                        STREAM_NAME,
                        GROUP_NAME,
                        message_id
                        )

                        print(
                            f"Job {job.id} added to Dead Letter Queue"
                        )

            finally:
                db.close()

    except Exception as e:
        print(f"Worker error: {e}")