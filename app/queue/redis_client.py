import redis

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
    socket_timeout=None,
    socket_connect_timeout=5
)