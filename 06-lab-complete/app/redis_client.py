"""Lazy Redis client shared by readiness, rate limiting, and budget tracking."""
import redis
from redis.exceptions import RedisError

from app.config import settings


# Creating the client does not connect; the app can start while Redis is unavailable.
r = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def redis_healthy() -> bool:
    try:
        return bool(r.ping())
    except RedisError:
        return False
