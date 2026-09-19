import asyncio

from app.provider_runtime import ProviderRateLimiter, with_retries


def test_rate_limiter_constructs():
    limiter = ProviderRateLimiter(60)
    assert limiter.interval == 1


def test_with_retries_retries_failures():
    state = {"count": 0}

    async def operation():
        state["count"] += 1
        if state["count"] < 3:
            raise RuntimeError("temporary")
        return "ok"

    assert asyncio.run(with_retries(operation, attempts=3, base_delay=0)) == "ok"
    assert state["count"] == 3
