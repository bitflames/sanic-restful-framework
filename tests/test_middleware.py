"""Unit tests for srf.middleware (auth and throttle)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from srf.config import settings
from srf.middleware.authmiddleware import (
    extract_bearer_token,
    is_public_endpoint,
)
from srf.middleware.throttlemiddleware import (
    IPRateLimit,
    MemoryStorage,
    RedisStorage,
    throttle_rate,
)


@pytest.fixture
def public_endpoints_via_app():
    """Bind NON_AUTH_ENDPOINTS through settings.set_app; restore afterward."""
    previous_app = getattr(settings, "app", None)

    def _bind(endpoints):
        app = MagicMock()
        app.config = SimpleNamespace(NON_AUTH_ENDPOINTS=endpoints)
        settings.set_app(app)

    yield _bind

    if previous_app is None:
        if hasattr(settings, "app"):
            delattr(settings, "app")
    else:
        object.__setattr__(settings, "app", previous)


class TestIsPublicEndpoint:
    def test_full_path_match_returns_true(self, public_endpoints_via_app):
        public_endpoints_via_app(("/api/auth/login", "/api/auth/register"))
        request = MagicMock()
        request.path = "/api/auth/login"
        assert is_public_endpoint(request) is True

    def test_suffix_only_does_not_match(self, public_endpoints_via_app):
        """Old tail-segment matching would treat /api/admin/login as public; full path must not."""
        public_endpoints_via_app(("/api/auth/login",))
        request = MagicMock()
        request.path = "/api/admin/login"
        assert is_public_endpoint(request) is False

    def test_unlisted_path_returns_false(self, public_endpoints_via_app):
        public_endpoints_via_app(("/api/auth/login",))
        request = MagicMock()
        request.path = "/api/projects/1"
        assert is_public_endpoint(request) is False

    def test_default_refresh_is_public(self):
        request = MagicMock()
        request.path = "/api/auth/refresh"
        assert is_public_endpoint(request) is True


class TestExtractBearerToken:
    def test_valid_bearer(self):
        request = MagicMock()
        request.headers = {"Authorization": "Bearer abc123"}
        assert extract_bearer_token(request) == "abc123"

    def test_missing_header_raises(self):
        from sanic.exceptions import Unauthorized

        request = MagicMock()
        request.headers = {}
        with pytest.raises(Unauthorized, match="Authentication required"):
            extract_bearer_token(request)

    def test_invalid_format_raises(self):
        from sanic.exceptions import Unauthorized

        request = MagicMock()
        request.headers = {"Authorization": "InvalidFormat"}
        with pytest.raises(Unauthorized, match="Invalid authorization"):
            extract_bearer_token(request)

    def test_not_bearer_scheme_raises(self):
        from sanic.exceptions import Unauthorized

        request = MagicMock()
        request.headers = {"Authorization": "Basic xyz"}
        with pytest.raises(Unauthorized, match="Invalid authorization"):
            extract_bearer_token(request)


class TestThrottleMemoryStorage:
    @pytest.mark.asyncio
    async def test_incr_returns_count(self):
        storage = MemoryStorage()
        n = await storage.incr("key1", window=60)
        assert n == 1
        n = await storage.incr("key1", window=60)
        assert n == 2

    @pytest.mark.asyncio
    async def test_cleanup_expired_drops_stale_keys(self):
        storage = MemoryStorage(cleanup_every=0)
        await storage.incr("k1", 1)
        storage.data["k1"] = [0.0]
        storage._windows["k1"] = 1
        storage.cleanup_expired()
        assert "k1" not in storage.data

    @pytest.mark.asyncio
    async def test_periodic_cleanup_runs(self):
        storage = MemoryStorage(cleanup_every=2)
        storage.cleanup_expired = MagicMock()
        await storage.incr("a", 60)
        await storage.incr("b", 60)
        storage.cleanup_expired.assert_called_once()


class TestRedisStorage:
    def test_requires_redis_client(self):
        with pytest.raises(ValueError, match="redis client is required"):
            RedisStorage(None)

    @pytest.mark.asyncio
    async def test_incr_sets_expire_on_first_hit(self):
        redis = AsyncMock()
        redis.incr = AsyncMock(return_value=1)
        redis.expire = AsyncMock()
        storage = RedisStorage(redis, prefix="throttle")

        count = await storage.incr("ip:1.2.3.4", window=60)

        assert count == 1
        redis.incr.assert_awaited_once_with("throttle:ip:1.2.3.4")
        redis.expire.assert_awaited_once_with("throttle:ip:1.2.3.4", 60)

    @pytest.mark.asyncio
    async def test_incr_skips_expire_after_first_hit(self):
        redis = AsyncMock()
        redis.incr = AsyncMock(return_value=2)
        redis.expire = AsyncMock()
        storage = RedisStorage(redis)

        count = await storage.incr("ip:1.2.3.4", window=30)

        assert count == 2
        redis.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_shared_redis_counts_across_storage_instances(self):
        """Two workers share one Redis client → same counter."""
        redis = AsyncMock()
        redis.incr = AsyncMock(side_effect=[1, 2, 3])
        redis.expire = AsyncMock()
        storage_a = RedisStorage(redis)
        storage_b = RedisStorage(redis)

        assert await storage_a.incr("ip:9.9.9.9", 60) == 1
        assert await storage_b.incr("ip:9.9.9.9", 60) == 2
        assert await storage_a.incr("ip:9.9.9.9", 60) == 3


class TestIPRateLimit:
    @pytest.mark.asyncio
    async def test_allow_under_limit(self):
        storage = MemoryStorage()
        limiter = IPRateLimit(limit=2, window=60, storage=storage)
        request = MagicMock()
        request.remote_addr = "127.0.0.1"
        assert await limiter.allow(request) is True
        assert await limiter.allow(request) is True
        assert await limiter.allow(request) is False

    @pytest.mark.asyncio
    async def test_redis_storage_with_ip_limiter(self):
        redis = AsyncMock()
        redis.incr = AsyncMock(side_effect=[1, 2, 3])
        redis.expire = AsyncMock()
        storage = RedisStorage(redis)
        limiter = IPRateLimit(limit=2, window=60, storage=storage)
        request = MagicMock()
        request.remote_addr = "10.0.0.1"

        assert await limiter.allow(request) is True
        assert await limiter.allow(request) is True
        assert await limiter.allow(request) is False


class TestThrottleRate:
    @pytest.mark.asyncio
    async def test_empty_limiters_allows(self):
        request = MagicMock()
        request.app.config = SimpleNamespace(REQUEST_LIMITERS=[])
        assert await throttle_rate(request) is True

    @pytest.mark.asyncio
    async def test_missing_config_defaults_to_empty(self):
        request = MagicMock()
        request.app.config = SimpleNamespace()
        assert await throttle_rate(request) is True

    @pytest.mark.asyncio
    async def test_denies_when_limiter_rejects(self):
        limiter = MagicMock()
        limiter.allow = AsyncMock(return_value=False)
        request = MagicMock()
        request.app.config = SimpleNamespace(REQUEST_LIMITERS=[limiter])
        assert await throttle_rate(request) is False
        limiter.allow.assert_awaited_once_with(request)
