from prometheus_client import Counter, Gauge, Histogram


jobs_total = Counter(
    "taskscale_jobs_total",
    "Total number of jobs created"
)

jobs_completed_total = Counter(
    "taskscale_jobs_completed_total",
    "Total number of completed jobs"
)

jobs_failed_total = Counter(
    "taskscale_jobs_failed_total",
    "Total number of failed jobs"
)

job_retries_total = Counter(
    "taskscale_job_retries_total",
    "Total number of job retries"
)

job_duration_seconds = Histogram(
    "taskscale_job_duration_seconds",
    "Job execution duration in seconds"
)

queue_size = Gauge(
    "taskscale_queue_size",
    "Current number of jobs waiting in the queue"
)