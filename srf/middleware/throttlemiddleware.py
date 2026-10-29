import hashlib
import math
import time
from abc import ABC, abstractmethod
from collections import defaultdict

from sanic import Request

from srf.config import settings


def get_client_ip(request: Request) -> str:
    """Best-effort client IP without extra proxy configuration.

    Sanic's ``remote_addr`` is derived from proxy headers only when the app
    configures them (``PROXIES_COUNT`` / ``REAL_IP_HEADER`` /
    ``FORWARDED_SECRET``); otherwise it is empty. Fall back to the socket peer
    ``request.ip`` so a default deployment still gets per-client buckets.
    """
    return getattr(request, "remote_addr", "") or getattr(request, "ip", "") or "unknown"


def _client_identity(request: Request) -> str:
    """Authenticated user id when available, otherwise the client IP."""
    user = getattr(request.ctx, "user", None)
    if user is not None and not getattr(user, "is_anonymous", False) and getattr(user, "id", None) is not None:
        return f"user:{user.id}"
    return f"ip:{get_client_ip(request)}"


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
        self._maybe_cleanup()
        return len(bucket)

    async def allow(self, key: str, window: int, limit: int) -> tuple[bool, int]:
        """Record a hit only when it is allowed; returns ``(allowed, retry_after)``.

        Rejected requests must not extend the sliding window, otherwise a client
        that keeps retrying can lock itself out indefinitely.
        """
        now = time.time()
        bucket = [t for t in self.data[key] if t > now - window]
        if len(bucket) >= limit:
            self.data[key] = bucket
            self._windows[key] = window
            retry_after = math.ceil(bucket[0] + window - now) if bucket else window
            return False, max(retry_after, 1)

        bucket.append(now)
        self.data[key] = bucket
        self._windows[key] = window
        self._maybe_cleanup()
        return True, 0

    def _maybe_cleanup(self) -> None:
        self._ops += 1
        if self.cleanup_every > 0 and self._ops >= self.cleanup_every:
            self._ops = 0
            self.cleanup_expired()

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

    Both ``incr()`` and ``allow()`` are single Lua scripts, so the counter and
    its TTL are always written atomically. A key without TTL (for example one
    left by an older SRF version) gets a TTL on the next hit.
    Requires ``app.ctx.redis`` (or any async redis client) at setup.
    """

    INCR_WITH_TTL_LUA = """
local count = redis.call('INCR', KEYS[1])
if redis.call('TTL', KEYS[1]) < 0 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""

    ALLOW_LUA = """
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
if current >= tonumber(ARGV[1]) then
    local ttl = redis.call('TTL', KEYS[1])
    if ttl < 0 then
        ttl = tonumber(ARGV[2])
        redis.call('EXPIRE', KEYS[1], ttl)
    end
    return {0, ttl}
end

local count = redis.call('INCR', KEYS[1])
if redis.call('TTL', KEYS[1]) < 0 then
    redis.call('EXPIRE', KEYS[1], ARGV[2])
end
return {1, 0}
"""

    def __init__(self, redis, prefix: str | None = None):
        if redis is None:
            raise ValueError("redis client is required")
        self.redis = redis
        self.prefix = prefix or settings.THROTTLE_REDIS_PREFIX

    async def incr(self, key: str, window: int) -> int:
        redis_key = f"{self.prefix}:{key}"
        return int(await self.redis.eval(self.INCR_WITH_TTL_LUA, 1, redis_key, max(int(window), 1)))

    async def allow(self, key: str, window: int, limit: int) -> tuple[bool, int]:
        result = await self.redis.eval(
            self.ALLOW_LUA,
            1,
            f"{self.prefix}:{key}",
            int(limit),
            max(int(window), 1),
        )
        allowed, retry_after = int(result[0]), int(result[1])
        return bool(allowed), max(retry_after, 0)


class BaseRateLimit(ABC):
    def __init__(self, limit: int, window: int, storage, scope: str | None = None):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if isinstance(window, bool) or not isinstance(window, int) or window <= 0:
            raise ValueError("window must be a positive integer")
        self.limit = limit
        self.window = window  # seconds
        self.storage = storage
        # Limiter identity: without it, two limiters that resolve to the same
        # user/IP would share one counter and one TTL.
        self.scope = scope or f"{type(self).__name__}:{limit}:{window}"
        self.retry_after = 0

    @abstractmethod
    async def get_key(self, request: Request) -> str:
        """Build the throttle key for this request."""

    async def allow(self, request: Request) -> bool:
        key = f"{self.scope}:{await self.get_key(request)}"
        if hasattr(self.storage, "allow"):
            allowed, retry_after = await self.storage.allow(key, self.window, self.limit)
        else:  # custom storage implementing only incr()
            count = await self.storage.incr(key, self.window)
            allowed = count <= self.limit
            retry_after = 0 if allowed else self.window
        self.retry_after = max(int(retry_after), 0)
        return allowed


class IPRateLimit(BaseRateLimit):
    async def get_key(self, request: Request) -> str:
        return f"ip:{get_client_ip(request)}"


class UserRateLimit(BaseRateLimit):
    # Register the throttle middleware AFTER the auth middleware: this limiter
    # reads ``request.ctx.user``, otherwise every request looks anonymous.
    async def get_key(self, request: Request) -> str:
        user = getattr(request.ctx, "user", None)
        # AnonymousUser is a truthy placeholder (useful for permissions), so
        # truthiness alone is not enough to tell it apart from a real user.
        if user is not None and not getattr(user, "is_anonymous", False) and getattr(user, "id", None) is not None:
            return f"user:{user.id}"
        # No authenticated identity: throttle by client IP so anonymous callers
        # do not all share one global bucket.
        return f"anon:{get_client_ip(request)}"


class PathRateLimit(BaseRateLimit):
    async def get_key(self, request: Request) -> str:
        # Include the caller identity; a path-only key would make every client
        # of that path share one bucket.
        return f"path:{_client_identity(request)}:{request.path}"


class HeaderRateLimit(BaseRateLimit):
    def __init__(self, header: str, limit: int, window: int, storage, scope: str | None = None):
        super().__init__(limit, window, storage, scope=scope)
        self.header = header

    async def get_key(self, request: Request) -> str:
        value = request.headers.get(self.header)
        if not value:
            # Do not let every request without the header share one bucket.
            return f"header:{self.header}:missing:{get_client_ip(request)}"
        # Hash the value: it may be an API key or token and must not land in a
        # Redis key verbatim.
        digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]
        return f"header:{self.header}:{digest}"


async def throttle_rate(request: Request):
    """Run all configured limiters; return ``False`` on the first denial.

    On denial ``request.ctx.throttle_retry_after`` holds the suggested
    ``Retry-After`` value in seconds (0 when the storage cannot provide one).
    """
    limiters = getattr(request.app.config, "REQUEST_LIMITERS", None)
    if limiters is None:
        limiters = settings.REQUEST_LIMITERS

    request.ctx.throttle_retry_after = 0
    for limiter in limiters:
        if not await limiter.allow(request):
            request.ctx.throttle_retry_after = getattr(limiter, "retry_after", 0)
            return False
    return True
