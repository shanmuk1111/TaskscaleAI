import requests
import time

BASE_URL = "http://localhost:8000"
TOTAL_JOBS = 1000

job = {
    "type": "ai_summarization",
    "input": {
        "text": "TaskScale AI 1000 job load test"
    }
}

submitted = 0
rejected = 0
job_ids = []

start = time.time()

while submitted < TOTAL_JOBS:

    try:
        response = requests.post(
            f"{BASE_URL}/jobs",
            json=job,
            timeout=10
        )

        if response.status_code in (200, 201):

            data = response.json()
            job_ids.append(data["id"])
            submitted += 1

            if submitted % 100 == 0:
                print(f"Accepted: {submitted}/{TOTAL_JOBS}")

        elif response.status_code == 429:

            rejected += 1
            time.sleep(0.5)

        else:

            print(
                f"Unexpected status: "
                f"{response.status_code} - {response.text}"
            )
            time.sleep(1)

    except Exception as e:

        print(f"Request error: {e}")
        time.sleep(1)


submission_time = time.time() - start

print()
print("===== 1000 JOB SUBMISSION =====")
print(f"Accepted:       {submitted}")
print(f"429 retries:    {rejected}")
print(f"Submission time: {submission_time:.2f} sec")
print(f"Submission rate: {submitted / submission_time:.2f} jobs/sec")
print()
print("All 1000 jobs were accepted.")