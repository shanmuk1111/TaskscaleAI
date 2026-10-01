import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
TOTAL_JOBS = 1000
POLL_INTERVAL = 1
POLL_TIMEOUT = 1800

JOB_PAYLOAD = {
    "type": "ai_summarization",
    "input": {"text": "TaskScale AI Day 41 clean benchmark"}
}


def kubectl(*args):
    try:
        result = subprocess.run(
            ["kubectl", *args],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.stdout.strip()
    except Exception as exc:
        return f"ERROR: {exc}"


def get_worker_count():
    output = kubectl(
        "get", "deployment", "taskscale-worker", "-n", "taskscale",
        "-o", "jsonpath={.status.readyReplicas}"
    )
    try:
        return int(output)
    except ValueError:
        return None


def get_hpa_cpu():
    output = kubectl(
        "get", "hpa", "taskscale-worker-hpa", "-n", "taskscale",
        "-o", "jsonpath={.status.currentMetrics[0].resource.current.averageUtilization}"
    )
    try:
        return int(output)
    except ValueError:
        return None


def get_postgres_counts():
    sql = (
        "SELECT "
        "COUNT(*) FILTER (WHERE status='COMPLETED'), "
        "COUNT(*) FILTER (WHERE status='QUEUED'), "
        "COUNT(*) FILTER (WHERE status='RUNNING'), "
        "COUNT(*) FILTER (WHERE status='FAILED') "
        "FROM jobs;"
    )

    output = kubectl(
        "exec", "-n", "taskscale",
        "taskscale-postgres-76fc9879f7-g4l98", "--",
        "psql", "-U", "postgres", "-d", "taskscale",
        "-t", "-A", "-c", sql
    )

    if output.startswith("ERROR:"):
        return None

    try:
        values = output.strip().split("|")
        return {
            "completed": int(values[0]),
            "queued": int(values[1]),
            "running": int(values[2]),
            "failed": int(values[3]),
        }
    except (ValueError, IndexError):
        return None


def get_max_job_id():
    output = kubectl(
        "exec", "-n", "taskscale",
        "taskscale-postgres-76fc9879f7-g4l98", "--",
        "psql", "-U", "postgres", "-d", "taskscale",
        "-t", "-A", "-c", "SELECT COALESCE(MAX(id), 0) FROM jobs;"
    )

    try:
        return int(output.strip())
    except ValueError:
        raise RuntimeError(f"Could not read maximum job ID. Output: {output}")


def get_benchmark_counts(start_id):
    sql = (
        "SELECT "
        "COUNT(*) FILTER (WHERE status='COMPLETED'), "
        "COUNT(*) FILTER (WHERE status='QUEUED'), "
        "COUNT(*) FILTER (WHERE status='RUNNING'), "
        "COUNT(*) FILTER (WHERE status='FAILED'), "
        "COUNT(*) "
        f"FROM jobs WHERE id > {start_id};"
    )

    output = kubectl(
        "exec", "-n", "taskscale",
        "taskscale-postgres-76fc9879f7-g4l98", "--",
        "psql", "-U", "postgres", "-d", "taskscale",
        "-t", "-A", "-c", sql
    )

    try:
        values = output.strip().split("|")
        return {
            "completed": int(values[0]),
            "queued": int(values[1]),
            "running": int(values[2]),
            "failed": int(values[3]),
            "total": int(values[4]),
        }
    except (ValueError, IndexError):
        return None


def main():
    session = requests.Session()

    print("========== TASKSCALE DAY 41 CLEAN BENCHMARK ==========")

    # Clean boundary: capture the last existing job before this test.
    start_id = get_max_job_id()
    before_counts = get_postgres_counts()

    workers_before = get_worker_count()
    hpa_cpu_before = get_hpa_cpu()

    print(f"Starting job ID boundary: {start_id}")
    print(f"Database before test: {before_counts}")
    print(f"Workers before test: {workers_before}")
    print(f"HPA CPU before test: {hpa_cpu_before}%")
    print(f"Submitting exactly {TOTAL_JOBS} jobs...")

    job_ids = []
    rejected_429 = 0
    other_errors = 0

    submit_start = time.time()

    while len(job_ids) < TOTAL_JOBS:
        try:
            response = session.post(
                f"{BASE_URL}/jobs",
                json=JOB_PAYLOAD,
                timeout=30,
            )
        except requests.RequestException as exc:
            other_errors += 1
            print(f"\nRequest error: {exc}")
            time.sleep(1)
            continue

        if response.status_code in (200, 201):
            body = response.json()
            job_id = body.get("id") or body.get("job_id")

            if job_id is None:
                raise RuntimeError(
                    f"API accepted a job but returned no ID: {body}"
                )

            job_ids.append(int(job_id))

            if len(job_ids) % 100 == 0:
                print(f"Submitted: {len(job_ids)}/{TOTAL_JOBS}")

        elif response.status_code == 429:
            rejected_429 += 1
            time.sleep(0.5)

        else:
            other_errors += 1
            print(
                f"\nHTTP {response.status_code}: "
                f"{response.text[:300]}"
            )
            time.sleep(0.5)

    submit_end = time.time()

    expected_first_id = start_id + 1
    expected_last_id = start_id + TOTAL_JOBS

    print("\nSubmission complete.")
    print(f"Expected benchmark IDs: {expected_first_id} -> {expected_last_id}")
    print("Waiting for those jobs to finish...")

    benchmark_end = None
    final_counts = None

    deadline = time.time() + POLL_TIMEOUT

    while time.time() < deadline:
        counts = get_benchmark_counts(start_id)

        if counts is not None:
            done = counts["completed"] + counts["failed"]

            print(
                f"\rBenchmark jobs: {counts['total']}/{TOTAL_JOBS} | "
                f"Completed: {counts['completed']} | "
                f"Running: {counts['running']} | "
                f"Queued: {counts['queued']} | "
                f"Failed: {counts['failed']}",
                end="",
                flush=True,
            )

            # Require exactly TOTAL_JOBS benchmark rows before declaring
            # the benchmark complete.
            if counts["total"] >= TOTAL_JOBS and done >= TOTAL_JOBS:
                final_counts = counts
                benchmark_end = time.time()
                break

        time.sleep(POLL_INTERVAL)

    print()

    if final_counts is None:
        final_counts = get_benchmark_counts(start_id)
        benchmark_end = time.time()

    workers_after = get_worker_count()
    hpa_cpu_after = get_hpa_cpu()

    submission_seconds = submit_end - submit_start
    end_to_end_seconds = benchmark_end - submit_start

    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": "Day 41 clean 1000-job benchmark",
        "job_id_start_boundary": start_id,
        "expected_first_job_id": expected_first_id,
        "expected_last_job_id": expected_last_id,
        "jobs_requested": TOTAL_JOBS,
        "jobs_accepted_by_api": len(job_ids),
        "http_429_retries": rejected_429,
        "other_http_errors": other_errors,
        "workers_before": workers_before,
        "workers_after": workers_after,
        "hpa_cpu_before_percent": hpa_cpu_before,
        "hpa_cpu_after_percent": hpa_cpu_after,
        "database_before": before_counts,
        "benchmark_final_counts": final_counts,
        "submission_seconds": round(submission_seconds, 3),
        "end_to_end_seconds": round(end_to_end_seconds, 3),
        "submission_rate_jobs_per_second": round(
            len(job_ids) / submission_seconds, 3
        ),
        "completion_rate_jobs_per_second": (
            round(TOTAL_JOBS / end_to_end_seconds, 3)
            if final_counts
            and final_counts["completed"] == TOTAL_JOBS
            and final_counts["failed"] == 0
            else None
        ),
        "benchmark_completed_exactly": bool(
            final_counts
            and final_counts["total"] == TOTAL_JOBS
            and final_counts["completed"] == TOTAL_JOBS
            and final_counts["failed"] == 0
            and final_counts["queued"] == 0
            and final_counts["running"] == 0
        ),
    }

    output_file = Path("day41_benchmark_results.json")
    output_file.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print("\n========== FINAL RESULT ==========")
    print(json.dumps(result, indent=2))
    print("==================================")
    print(f"\nSaved to: {output_file.resolve()}")

    if not result["benchmark_completed_exactly"]:
        print(
            "\nWARNING: The benchmark did not reach an exact "
            "1000/1000 terminal state."
        )


if __name__ == "__main__":
    main()
