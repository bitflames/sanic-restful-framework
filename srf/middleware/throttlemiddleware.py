import time
from abc import ABC, abstractmethod
from collections import defaultdict

from sanic import Request


class MemoryStorage:
    """Sliding window in process memory. Single worker only.

    Keeps timestamps per key; ``cleanup_expired()`` drops keys that have
    no hits left inside their window (called automatically every
    ``cleanup_every`` incr calls).
    """

    def __init__(self, cleanup_every: int = 256):
        self.data: dict[str, list[float]] = defaultdict(list)
        self._windows: dict[str, int] = {}
        self._ops = 0
        self.cleanup_every = cleanup_every

    async def incr(self, key: str, window: int) -> int:
        now = time.time()
        bucket = [t for t in self.data[key] if t > now - window]
        bucket.append(now)
        self.data[key] = bucket
        self._windows[key] = window

        self._ops += 1
        if self.cleanup_every > 0 and self._ops >= self.cleanup_every:
            self._ops = 0
            self.cleanup_expired()

        return len(bucket)

    def cleanup_expired(self) -> None:
        """Drop keys whose timestamps are all outside their window."""
        now = time.time()
        for key in list(self.data):
            window = self._windows.get(key, 0)
            if not any(t > now - window for t in self.data[key]):
                del self.data[key]
                self._windows.pop(key, None)


class RedisStorage:
    """Fixed window counter on Redis. Share across Sanic workers.

    First hit in a window: INCR then EXPIRE(window). Later hits only INCR.
    Requires ``app.ctx.redis`` (or any async redis client) at setup.
    """

    def __init__(self, redis, prefix: str = "throttle"):
        if redis is None:
            raise ValueError("redis client is required")
        self.redis = redis
        self.prefix = prefix

    async def incr(self, key: str, window: int) -> int:
        redis_key = f"{self.prefix}:{key}"
        count = int(await self.redis.incr(redis_key))
        if count == 1:
            await self.redis.expire(redis_key, max(int(window), 1))
        return count


class BaseRateLimit(ABC):
    def __init__(self, limit: int, window: int, storage):
        self.limit = limit
        self.window = window  # seconds
        self.storage = storage

    @abstractmethod
    async def get_key(self, request: Request) -> str:
        """Build the throttle key for this request."""

    async def allow(self, request: Request) -> bool:
        key = await self.get_key(request)
        count = await self.storage.incr(key, self.window)
        return count <= self.limit


class IPRateLimit(BaseRateLimit):
    async def get_key(self, request: Request) -> str:
        return f"ip:{request.remote_addr}"


class UserRateLimit(BaseRateLimit):
    async def get_key(self, request: Request) -> str:
        user = getattr(request.ctx, "user", None)
        if not user:
            return "anonymous"
        return f"user:{user.id}"


class PathRateLimit(BaseRateLimit):
    async def get_key(self, request: Request) -> str:
        return f"path:{request.path}"


class HeaderRateLimit(BaseRateLimit):
    def __init__(self, header: str, limit: int, window: int, storage):
        super().__init__(limit, window, storage)
        self.header = header

    async def get_key(self, request: Request) -> str:
        value = request.headers.get(self.header)
        return f"header:{self.header}:{value}"


async def throttle_rate(request: Request):
    limiters = getattr(request.app.config, "REQUEST_LIMITERS", [])
    for limiter in limiters:
        if not await limiter.allow(request):
            return False
    return True
