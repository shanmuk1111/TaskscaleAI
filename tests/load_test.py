from locust import HttpUser, task, between


class TaskScaleUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def create_job(self):
        payload = {
            "type": "ai_summarization",
            "input": {
                "text": "TaskScale load testing job."
            }
        }

        self.client.post(
            "/jobs",
            json=payload
        )