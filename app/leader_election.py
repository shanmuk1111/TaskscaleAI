import uuid

from app.queue.redis_client import redis_client


LEADER_KEY = "taskscale:scheduler_leader"
LEADER_TIMEOUT = 10


def become_leader():
    leader_id = str(uuid.uuid4())

    acquired = redis_client.set(
        LEADER_KEY,
        leader_id,
        nx=True,
        ex=LEADER_TIMEOUT
    )

    if acquired:
        return leader_id

    return None


def is_leader(leader_id):
    current_leader = redis_client.get(LEADER_KEY)
    return current_leader == leader_id


def renew_leadership(leader_id):
    current_leader = redis_client.get(LEADER_KEY)

    if current_leader == leader_id:
        redis_client.expire(
            LEADER_KEY,
            LEADER_TIMEOUT
        )
        return True

    return False


def release_leadership(leader_id):
    current_leader = redis_client.get(LEADER_KEY)

    if current_leader == leader_id:
        redis_client.delete(LEADER_KEY)
        return True

    return False