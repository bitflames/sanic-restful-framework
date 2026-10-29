"""Unit tests for authentication and throttling middleware."""

import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sanic.exceptions import Unauthorized
from sanic_jwt.exceptions import (
    InvalidAuthorizationHeader,
    MissingAuthorizationCookie,
    MissingAuthorizationHeader,
    MissingAuthorizationQueryArg,
)

from srf.auth.models import AnonymousUser
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
    async def test_malformed_header_becomes_unauthorized(self):
        request = MagicMock()
        request.app.ctx.auth._get_token = MagicMock(side_effect=InvalidAuthorizationHeader("bad token"))
        with pytest.raises(Unauthorized):
            await authenticate_request(request)

    @pytest.mark.asyncio
    async def test_missing_token_strict_is_unauthorized(self):
        """Strict mode: no credentials at all is also a 401."""
        request = MagicMock()
        request.app.ctx.auth._get_token = MagicMock(side_effect=MissingAuthorizationHeader())
        request.app.ctx.auth.extract_payload = AsyncMock()
        request.app.ctx.auth.retrieve_user = AsyncMock()
        with pytest.raises(Unauthorized, match="Authentication required"):
            await authenticate_request(request, strict=True)
        request.app.ctx.auth.extract_payload.assert_not_called()
        request.app.ctx.auth.retrieve_user.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_token_optional_becomes_anonymous(self):
        """Optional mode (default): no credentials -> AnonymousUser, no 401."""
        request = MagicMock()
        request.app.ctx.auth._get_token = MagicMock(side_effect=MissingAuthorizationHeader())
        request.app.ctx.auth.extract_payload = AsyncMock()
        request.app.ctx.auth.retrieve_user = AsyncMock()

        await authenticate_request(request)

        assert isinstance(request.ctx.user, AnonymousUser)
        assert request.ctx.user.is_active is False
        assert request.ctx.user.is_authenticated is False
        request.app.ctx.auth.extract_payload.assert_not_called()
        request.app.ctx.auth.retrieve_user.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("missing_exc", [MissingAuthorizationCookie, MissingAuthorizationQueryArg])
    async def test_missing_cookie_or_query_token_optional_becomes_anonymous(self, missing_exc):
        """Cookie/query-string auth with no credentials is still anonymous in optional mode."""
        request = MagicMock()
        request.app.ctx.auth._get_token = MagicMock(side_effect=missing_exc())
        request.app.ctx.auth.extract_payload = AsyncMock()
        request.app.ctx.auth.retrieve_user = AsyncMock()

        await authenticate_request(request)

        assert isinstance(request.ctx.user, AnonymousUser)
        request.app.ctx.auth.extract_payload.assert_not_called()
        request.app.ctx.auth.retrieve_user.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("missing_exc", [MissingAuthorizationCookie, MissingAuthorizationQueryArg])
    async def test_missing_cookie_or_query_token_strict_is_unauthorized(self, missing_exc):
        request = MagicMock()
        request.app.ctx.auth._get_token = MagicMock(side_effect=missing_exc())

        with pytest.raises(Unauthorized, match="Authentication required"):
            await authenticate_request(request, strict=True)

    @pytest.mark.asyncio
    async def test_rejected_token_is_unauthorized(self):
        """Expired or forged tokens both fail verification -> 401."""
        request = MagicMock()
        request.app.ctx.auth.extract_payload = AsyncMock(return_value=None)
        request.app.ctx.auth.retrieve_user = AsyncMock()
        with pytest.raises(Unauthorized, match="Invalid or expired token"):
            await authenticate_request(request)
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
        authenticate.assert_awaited_once_with(request, strict=False)

    @pytest.mark.asyncio
    async def test_request_middleware_forwards_strict_flag(self, monkeypatch):
        import srf.middleware.authmiddleware as middleware

        authenticate = AsyncMock()
        monkeypatch.setattr(middleware, "authenticate_request", authenticate)
        request = MagicMock()
        await set_user_to_request_ctx(request, strict=True)
        authenticate.assert_awaited_once_with(request, strict=True)


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
    async def test_redis_storage_incr_is_one_atomic_script(self):
        redis = AsyncMock()
        redis.eval = AsyncMock(side_effect=[1, 2])
        storage = RedisStorage(redis, prefix="test")

        assert await storage.incr("user:7", 60) == 1
        assert await storage.incr("user:7", 60) == 2
        assert redis.eval.await_count == 2
        args = redis.eval.await_args_list[0].args
        assert "INCR" in args[0]
        assert args[1:] == (1, "test:user:7", 60)

    def test_allow_lua_repairs_missing_ttl(self):
        assert "redis.call('EXPIRE', KEYS[1], ttl)" in RedisStorage.ALLOW_LUA

    @pytest.mark.asyncio
    async def test_redis_storage_allow_returns_retry_after(self):
        redis = AsyncMock()
        storage = RedisStorage(redis, prefix="test")

        redis.eval = AsyncMock(return_value=[1, 0])
        assert await storage.allow("k", 60, 5) == (True, 0)

        redis.eval = AsyncMock(return_value=[0, 42])
        assert await storage.allow("k", 60, 5) == (False, 42)

    @pytest.mark.asyncio
    async def test_memory_storage_allow_does_not_count_rejected_hits(self):
        storage = MemoryStorage()

        assert await storage.allow("k", 60, 1) == (True, 0)
        allowed, retry_after = await storage.allow("k", 60, 1)
        assert allowed is False
        assert retry_after >= 1
        # The rejected hit was not appended: the bucket still has one entry.
        assert len(storage.data["k"]) == 1


class TestRateLimiters:
    @pytest.mark.asyncio
    async def test_key_builders(self):
        request = MagicMock()
        request.remote_addr = "127.0.0.1"
        request.path = "/items"
        request.headers = {"X-Client": "abc"}
        request.ctx.user = SimpleNamespace(id=9)
        storage = MemoryStorage()
        header_digest = hashlib.sha256(b"abc").hexdigest()[:16]

        assert await IPRateLimit(1, 60, storage).get_key(request) == "ip:127.0.0.1"
        assert await UserRateLimit(1, 60, storage).get_key(request) == "user:9"
        assert await PathRateLimit(1, 60, storage).get_key(request) == "path:user:9:/items"
        assert await HeaderRateLimit("X-Client", 1, 60, storage).get_key(request) == f"header:X-Client:{header_digest}"

    @pytest.mark.asyncio
    async def test_missing_header_falls_back_to_ip(self):
        request = MagicMock()
        request.remote_addr = "127.0.0.1"
        request.headers = {}
        limiter = HeaderRateLimit("X-Client", 1, 60, MemoryStorage())
        assert await limiter.get_key(request) == "header:X-Client:missing:127.0.0.1"

    @pytest.mark.asyncio
    async def test_ip_falls_back_to_socket_peer_when_no_proxy_config(self):
        request = MagicMock()
        request.remote_addr = ""
        request.ip = "192.0.2.10"
        limiter = IPRateLimit(1, 60, MemoryStorage())
        assert await limiter.get_key(request) == "ip:192.0.2.10"

    @pytest.mark.parametrize("limit", [0, -1, True, 1.5, "1"])
    def test_rejects_invalid_limit(self, limit):
        with pytest.raises(ValueError, match="limit must be a positive integer"):
            IPRateLimit(limit, 60, MemoryStorage())

    @pytest.mark.parametrize("window", [0, -1, True, 1.5, "60"])
    def test_rejects_invalid_window(self, window):
        with pytest.raises(ValueError, match="window must be a positive integer"):
            IPRateLimit(1, window, MemoryStorage())

    @pytest.mark.asyncio
    async def test_limiters_with_different_settings_do_not_share_a_bucket(self):
        storage = MemoryStorage()
        request = MagicMock()
        request.remote_addr = "127.0.0.1"
        request.ctx.user = SimpleNamespace(id=9)

        short = UserRateLimit(1, 60, storage)
        long = UserRateLimit(5, 3600, storage)
        assert await short.allow(request) is True
        assert await long.allow(request) is True
        assert len(storage.data) == 2

    @pytest.mark.asyncio
    async def test_user_limiter_falls_back_to_ip_without_user(self):
        request = MagicMock()
        request.ctx.user = None
        request.remote_addr = "127.0.0.1"
        limiter = UserRateLimit(1, 60, MemoryStorage())
        assert await limiter.get_key(request) == "anon:127.0.0.1"

    @pytest.mark.asyncio
    async def test_user_limiter_treats_anonymous_user_placeholder_as_ip(self):
        request = MagicMock()
        request.ctx.user = AnonymousUser()
        request.remote_addr = "10.0.0.7"
        limiter = UserRateLimit(1, 60, MemoryStorage())
        assert await limiter.get_key(request) == "anon:10.0.0.7"

    @pytest.mark.asyncio
    async def test_anonymous_clients_do_not_share_a_bucket(self):
        limiter = UserRateLimit(1, 60, MemoryStorage())
        first = MagicMock()
        first.ctx.user = AnonymousUser()
        first.remote_addr = "10.0.0.7"
        second = MagicMock()
        second.ctx.user = AnonymousUser()
        second.remote_addr = "10.0.0.8"

        assert await limiter.get_key(first) != await limiter.get_key(second)
        assert await limiter.allow(first) is True
        assert await limiter.allow(second) is True
        assert await limiter.allow(first) is False

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

    @pytest.mark.asyncio
    async def test_throttle_rate_exposes_retry_after(self):
        request = MagicMock()
        request.remote_addr = "127.0.0.1"
        request.app.config = SimpleNamespace(REQUEST_LIMITERS=[IPRateLimit(1, 60, MemoryStorage())])

        assert await throttle_rate(request) is True
        assert await throttle_rate(request) is False
        assert request.ctx.throttle_retry_after >= 1
