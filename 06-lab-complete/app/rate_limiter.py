"""Redis-backed sliding-window rate limit, shared across workers and restarts."""
import hashlib
import time
import uuid

from fastapi import HTTPException
from redis.exceptions import RedisError

from app.config import settings
from app.redis_client import r


_WINDOW_SECONDS = 60
_LIMIT_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local cutoff = tonumber(ARGV[2])
local member = ARGV[3]
local limit = tonumber(ARGV[4])
local window = tonumber(ARGV[5])

redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local count = tonumber(redis.call('ZCARD', key))
if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = window
    if oldest[2] then
        retry_after = math.ceil(window - (now - tonumber(oldest[2])))
    end
    if retry_after < 1 then retry_after = 1 end
    return {0, retry_after}
end

redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, window * 2)
return {1, 0}
"""


def check_rate_limit(key: str) -> None:
    now = time.time()
    cutoff = now - _WINDOW_SECONDS
    limit = max(1, settings.rate_limit_per_minute)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    redis_key = f"rate-limit:{digest}"
    member = f"{now:.6f}:{uuid.uuid4().hex}"

    try:
        allowed, retry_after = r.eval(
            _LIMIT_SCRIPT,
            1,
            redis_key,
            now,
            cutoff,
            member,
            limit,
            _WINDOW_SECONDS,
        )
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Rate limiter unavailable") from exc

    if int(allowed) != 1:
        seconds = max(1, int(retry_after))
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(seconds)},
        )
