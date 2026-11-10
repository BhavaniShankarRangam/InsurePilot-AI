"""Fixed-window rate limiter. Uses Redis when configured, else in-process memory."""

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, UploadFile, status

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
            rkey = f"rl:{key}:{window}:{bucket}"
            count = self._redis.incr(rkey)
            if count == 1:
                self._redis.expire(rkey, window)
            return int(count) <= limit
        mkey = f"{key}:{window}"
        with self._lock:
            stored_bucket, count = self._memory[mkey]
            if stored_bucket != bucket:
                stored_bucket, count = bucket, 0
            count += 1
            self._memory[mkey] = (stored_bucket, count)
            return count <= limit

    def reset(self) -> None:
        with self._lock:
            self._memory.clear()


_limiter: RateLimiter | None = None


def get_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def client_key(request: Request) -> str:
    # uvicorn --proxy-headers resolves X-Forwarded-For into request.client on the hosted image.
    return request.client.host if request.client else "anon"


def rate_limit(scope: str, limit: int | None = None):
    async def dependency(request: Request) -> None:
        settings = get_settings()
        if settings.environment == "test":
            return
        max_hits = limit or settings.rate_limit_per_minute
        if not get_limiter().hit(f"{scope}:{client_key(request)}", max_hits):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Please slow down.")

    return dependency


def demo_quota(scope: str, per_visitor_attr: str, global_attr: str | None = None):
    """Hourly caps that only apply when DEMO_MODE is on. Limits are read from settings at request time."""

    async def dependency(request: Request) -> None:
        s = get_settings()
        if not s.demo_mode:
            return
        lim = get_limiter()
        if not lim.hit(f"demo:{scope}:{client_key(request)}", getattr(s, per_visitor_attr), window=3600):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                f"Demo limit reached: {getattr(s, per_visitor_attr)} per hour. Please try again later.",
                                headers={"Retry-After": "3600"})
        if global_attr and not lim.hit(f"demo:{scope}:global", getattr(s, global_attr), window=3600):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                "The demo is busy right now. Please try again in a little while.",
                                headers={"Retry-After": "600"})

    return dependency


async def read_upload_capped(file: UploadFile) -> bytes:
    """Reads an upload in chunks and stops as soon as it passes the size limit (no full read of a huge file)."""
    max_mb = get_settings().upload_limit_mb
    max_bytes = max_mb * 1024 * 1024
    chunks, total = [], 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(413, f"Files must be under {max_mb} MB")
        chunks.append(chunk)
    return b"".join(chunks)
