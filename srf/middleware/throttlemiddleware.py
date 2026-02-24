import time
from abc import ABC, abstractmethod
from collections import defaultdict

from sanic import Request


class MemoryStorage:
    def __init__(self):
        self.data = defaultdict(list)

    def incr(self, key: str, window: int) -> int:
        now = time.time()
        bucket = self.data[key]

        # clean outdated key
        self.data[key] = [t for t in bucket if t > now - window]
        self.data[key].append(now)
        return len(self.data[key])

    def cleanup_expired(self, window: int) -> None:
        """Remove keys whose timestamps are all outside the window. Call periodically to limit memory growth."""
        now = time.time()
        expired = [k for k, bucket in self.data.items() if not any(t > now - window for t in bucket)]
        for k in expired:
            del self.data[k]


class BaseRateLimit(ABC):
    """
    rate_limiter = CompositeRateLimit(
        IPRateLimit(100, 60, storage),
        UserRateLimit(1000, 60, storage),
    )

    allowed = await rate_limiter.allow(request)

    """

    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window  # seconds

    @abstractmethod
    async def get_key(self, request: Request) -> str:
        """gen throttle key"""

    @abstractmethod
    async def allow(self, request: Request) -> bool:
        """is it allow pass"""


class IPRateLimit(BaseRateLimit):
    def __init__(self, limit: int, window: int, storage):
        super().__init__(limit, window)
        self.storage = storage

    async def get_key(self, request: Request) -> str:
        return f"ip:{request.remote_addr}"

    async def allow(self, request: Request) -> bool:
        key = await self.get_key(request)
        return self.storage.incr(key, self.window) <= self.limit


class UserRateLimit(BaseRateLimit):
    def __init__(self, limit: int, window: int, storage):
        super().__init__(limit, window)
        self.storage = storage

    async def get_key(self, request: Request) -> str:
        user = getattr(request.ctx, "user", None)
        if not user:
            return "anonymous"
        return f"user:{user.id}"

    async def allow(self, request: Request) -> bool:
        key = await self.get_key(request)
        return self.storage.incr(key, self.window) <= self.limit


class PathRateLimit(BaseRateLimit):
    def __init__(self, limit: int, window: int, storage):
        super().__init__(limit, window)
        self.storage = storage

    async def get_key(self, request: Request) -> str:
        return f"path:{request.path}"

    async def allow(self, request: Request) -> bool:
        key = await self.get_key(request)
        return self.storage.incr(key, self.window) <= self.limit


class HeaderRateLimit(BaseRateLimit):
    def __init__(self, header: str, limit: int, window: int, storage):
        super().__init__(limit, window)
        self.header = header
        self.storage = storage

    async def get_key(self, request: Request) -> str:
        value = request.headers.get(self.header)
        return f"header:{self.header}:{value}"

    async def allow(self, request: Request) -> bool:
        key = await self.get_key(request)
        return self.storage.incr(key, self.window) <= self.limit


async def throttle_rate(request: Request):
    for limiter in request.app.config.RequestLimiter:
        if not await limiter.allow(request):
            return False
    return True
