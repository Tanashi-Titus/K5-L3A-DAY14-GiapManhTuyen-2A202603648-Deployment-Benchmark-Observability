"""Daily LLM budget tracking in Redis."""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from redis.exceptions import RedisError

from app.config import settings
from app.redis_client import r


# USD per 1K tokens (mock gpt-4o-mini pricing used in this lab).
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006


def _today_key() -> str:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"llm-cost:daily:{day}"


def _ttl_until_next_day() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(60, int((tomorrow - now).total_seconds()) + 60)


def check_budget() -> None:
    try:
        current = float(r.get(_today_key()) or 0.0)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Cost guard unavailable") from exc

    if current >= settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail="Daily LLM budget exceeded")


_RECORD_SCRIPT = """
local key = KEYS[1]
local cost = tonumber(ARGV[1])
local budget = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])
local current = tonumber(redis.call('GET', key) or '0')
if current + cost > budget then
    return {0, current}
end
local total = redis.call('INCRBYFLOAT', key, cost)
redis.call('EXPIRE', key, ttl)
return {1, tonumber(total)}
"""


def record_cost(input_tokens: int, output_tokens: int) -> float:
    input_tokens = max(0, int(input_tokens))
    output_tokens = max(0, int(output_tokens))
    cost = (
        input_tokens / 1000 * PRICE_INPUT_PER_1K
        + output_tokens / 1000 * PRICE_OUTPUT_PER_1K
    )

    try:
        accepted, _total = r.eval(
            _RECORD_SCRIPT,
            1,
            _today_key(),
            cost,
            settings.daily_budget_usd,
            _ttl_until_next_day(),
        )
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Cost guard unavailable") from exc

    if int(accepted) != 1:
        raise HTTPException(status_code=402, detail="Daily LLM budget exceeded")
    return cost
