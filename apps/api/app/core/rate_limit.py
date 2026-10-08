"""Fixed-window rate limiter. Uses Redis when configured, else in-process memory."""

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


class RateLimiter:
    def __init__(self) -> None:
        self._memory: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))
        self._lock = Lock()
        self._redis = None
        url = get_settings().redis_url
        if url:
            try:
                import redis

                self._redis = redis.Redis.from_url(url)
                self._redis.ping()
            except Exception:
                self._redis = None

    def hit(self, key: str, limit: int, window: int = 60) -> bool:
        bucket = int(time.time() // window)
        if self._redis is not None:
            rkey = f"rl:{key}:{bucket}"
            count = self._redis.incr(rkey)
            if count == 1:
                self._redis.expire(rkey, window)
            return int(count) <= limit
        with self._lock:
            stored_bucket, count = self._memory[key]
            if stored_bucket != bucket:
                stored_bucket, count = bucket, 0
            count += 1
            self._memory[key] = (stored_bucket, count)
            return count <= limit


_limiter: RateLimiter | None = None


def get_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def rate_limit(scope: str, limit: int | None = None):
    async def dependency(request: Request) -> None:
        settings = get_settings()
        if settings.environment == "test":
            return
        client = request.client.host if request.client else "anon"
        max_hits = limit or settings.rate_limit_per_minute
        if not get_limiter().hit(f"{scope}:{client}", max_hits):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Please slow down.")

    return dependency
