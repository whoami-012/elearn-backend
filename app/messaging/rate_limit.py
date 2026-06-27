import asyncio
import time
from collections import defaultdict, deque

from app.messaging.exceptions import messaging_error


class InMemoryRateLimiter:
    """Single-process fallback. Configure a Redis adapter for multi-worker production."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        async with self._lock:
            events = self._events[key]
            while events and events[0] <= now - window_seconds:
                events.popleft()
            if len(events) >= limit:
                retry = max(1, int(window_seconds - (now - events[0])))
                raise messaging_error(
                    429,
                    "RATE_LIMIT_EXCEEDED",
                    "Messaging rate limit exceeded.",
                    headers={"Retry-After": str(retry)},
                )
            events.append(now)


class RedisRateLimiter:
    def __init__(self, url: str) -> None:
        from redis.asyncio import from_url

        self.redis = from_url(url, decode_responses=True)

    async def check(self, key: str, limit: int, window_seconds: int) -> None:
        bucket = int(time.time()) // window_seconds
        redis_key = f"messaging:rate:{key}:{bucket}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(redis_key)
            pipe.expire(redis_key, window_seconds + 1)
            count, _ = await pipe.execute()
        if int(count) > limit:
            retry = window_seconds - (int(time.time()) % window_seconds)
            raise messaging_error(
                429,
                "RATE_LIMIT_EXCEEDED",
                "Messaging rate limit exceeded.",
                headers={"Retry-After": str(retry)},
            )


from app.core.config import settings

rate_limiter = RedisRateLimiter(settings.MESSAGE_REDIS_URL) if settings.MESSAGE_REDIS_URL else InMemoryRateLimiter()
