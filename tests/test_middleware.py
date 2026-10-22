"""Unit tests for authentication and throttling middleware."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sanic.exceptions import Unauthorized
from sanic_jwt.exceptions import InvalidAuthorizationHeader

from srf.middleware.authmiddleware import authenticate_request, extract_bearer_token, set_user_to_request_ctx
from srf.middleware.throttlemiddleware import (
    HeaderRateLimit,
    IPRateLimit,
    MemoryStorage,
    PathRateLimit,
    RedisStorage,
    UserRateLimit,
    throttle_rate,
)


class TestExtractBearerToken:
    @pytest.mark.parametrize(
        ("header", "expected"),
        [("Bearer abc123", "abc123"), ("bearer token with spaces", "token with spaces")],
    )
    def test_valid_bearer(self, header, expected):
        request = MagicMock()
        request.headers = {"Authorization": header}
        assert extract_bearer_token(request) == expected

    @pytest.mark.parametrize("header", [None, "", "Bearer", "Basic xyz", "Bearer "])
    def test_invalid_header_raises_unauthorized(self, header):
        request = MagicMock()
        request.headers = {"Authorization": header} if header is not None else {}
        with pytest.raises(Unauthorized):
            extract_bearer_token(request)


class TestAuthenticateRequest:
    @pytest.mark.asyncio
    async def test_requires_configured_auth(self):
        request = MagicMock()
        del request.app.ctx.auth
        with pytest.raises(Unauthorized, match="not configured"):
            await authenticate_request(request)

    @pytest.mark.asyncio
    async def test_invalid_jwt_becomes_unauthorized(self):
        request = MagicMock()
        request.app.ctx.auth.extract_payload = AsyncMock(side_effect=InvalidAuthorizationHeader("bad token"))
        with pytest.raises(Unauthorized):
            await authenticate_request(request)

    @pytest.mark.asyncio
    async def test_empty_payload_sets_anonymous_user(self):
        request = MagicMock()
        request.app.ctx.auth.extract_payload = AsyncMock(return_value=None)
        request.app.ctx.auth.retrieve_user = AsyncMock()
        await authenticate_request(request)
        assert request.ctx.user is None
        request.app.ctx.auth.retrieve_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_retrieves_authenticated_user(self):
        request = MagicMock()
        user = SimpleNamespace(id=7)
        request.app.ctx.auth.extract_payload = AsyncMock(return_value={"user_id": 7})
        request.app.ctx.auth.retrieve_user = AsyncMock(return_value={"user_id": 7})
        request.ctx.user = user

        await authenticate_request(request)

        request.app.ctx.auth.retrieve_user.assert_awaited_once_with(request, {"user_id": 7})

    @pytest.mark.asyncio
    async def test_unknown_user_is_rejected(self):
        request = MagicMock()
        request.app.ctx.auth.extract_payload = AsyncMock(return_value={"user_id": 404})
        request.app.ctx.auth.retrieve_user = AsyncMock(return_value=None)
        request.ctx.user = None
        with pytest.raises(Unauthorized, match="User not found"):
            await authenticate_request(request)

    @pytest.mark.asyncio
    async def test_request_middleware_delegates_to_authenticate_request(self, monkeypatch):
        import srf.middleware.authmiddleware as middleware

        authenticate = AsyncMock()
        monkeypatch.setattr(middleware, "authenticate_request", authenticate)
        request = MagicMock()
        await set_user_to_request_ctx(request)
        authenticate.assert_awaited_once_with(request)


class TestThrottleStorage:
    @pytest.mark.asyncio
    async def test_memory_storage_counts_hits_in_window(self):
        storage = MemoryStorage()
        assert await storage.incr("key", 60) == 1
        assert await storage.incr("key", 60) == 2

    def test_cleanup_removes_expired_keys(self):
        storage = MemoryStorage(cleanup_every=0)
        storage.data["stale"] = [0.0]
        storage._windows["stale"] = 1
        storage.cleanup_expired()
        assert "stale" not in storage.data
        assert "stale" not in storage._windows

    def test_redis_storage_requires_client(self):
        with pytest.raises(ValueError, match="redis client is required"):
            RedisStorage(None)

    @pytest.mark.asyncio
    async def test_redis_storage_sets_expiry_only_for_first_hit(self):
        redis = AsyncMock()
        redis.incr = AsyncMock(side_effect=[1, 2])
        storage = RedisStorage(redis, prefix="test")

        assert await storage.incr("user:7", 60) == 1
        assert await storage.incr("user:7", 60) == 2
        redis.expire.assert_awaited_once_with("test:user:7", 60)


class TestRateLimiters:
    @pytest.mark.asyncio
    async def test_key_builders(self):
        request = MagicMock()
        request.remote_addr = "127.0.0.1"
        request.path = "/items"
        request.headers = {"X-Client": "abc"}
        request.ctx.user = SimpleNamespace(id=9)
        storage = MemoryStorage()

        assert await IPRateLimit(1, 60, storage).get_key(request) == "ip:127.0.0.1"
        assert await UserRateLimit(1, 60, storage).get_key(request) == "user:9"
        assert await PathRateLimit(1, 60, storage).get_key(request) == "path:/items"
        assert await HeaderRateLimit("X-Client", 1, 60, storage).get_key(request) == "header:X-Client:abc"

    @pytest.mark.asyncio
    async def test_user_limiter_uses_anonymous_bucket(self):
        request = MagicMock()
        request.ctx.user = None
        limiter = UserRateLimit(1, 60, MemoryStorage())
        assert await limiter.get_key(request) == "anonymous"

    @pytest.mark.asyncio
    async def test_limit_denies_request_after_threshold(self):
        limiter = IPRateLimit(1, 60, MemoryStorage())
        request = MagicMock()
        request.remote_addr = "127.0.0.1"
        assert await limiter.allow(request) is True
        assert await limiter.allow(request) is False

    @pytest.mark.asyncio
    async def test_throttle_rate_defaults_to_allow_and_stops_on_denial(self):
        request = MagicMock()
        request.app.config = SimpleNamespace()
        assert await throttle_rate(request) is True

        first = MagicMock()
        first.allow = AsyncMock(return_value=True)
        rejected = MagicMock()
        rejected.allow = AsyncMock(return_value=False)
        never_reached = MagicMock()
        never_reached.allow = AsyncMock(return_value=True)
        request.app.config = SimpleNamespace(REQUEST_LIMITERS=[first, rejected, never_reached])

        assert await throttle_rate(request) is False
        first.allow.assert_awaited_once_with(request)
        rejected.allow.assert_awaited_once_with(request)
        never_reached.allow.assert_not_awaited()
