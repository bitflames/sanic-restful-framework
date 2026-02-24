"""Unit tests for srf.middleware (auth and throttle)."""

import pytest
from unittest.mock import MagicMock

from srf.middleware.authmiddleware import (
    extract_bearer_token,
    is_public_endpoint,
)
from srf.middleware.throttlemiddleware import IPRateLimit, MemoryStorage


class TestIsPublicEndpoint:
    def test_tail_in_list_returns_true(self):
        request = MagicMock()
        request.path = "/api/auth/login"
        request.app.config.NON_AUTH_ENDPOINTS = ("login", "register")
        assert is_public_endpoint(request) is True

    def test_tail_not_in_list_returns_false(self):
        request = MagicMock()
        request.path = "/api/projects/1"
        request.app.config.NON_AUTH_ENDPOINTS = ("login",)
        assert is_public_endpoint(request) is False

    def test_missing_config_returns_false(self):
        request = MagicMock()
        request.path = "/api/auth/login"
        request.app.config = {}
        result = is_public_endpoint(request)
        assert result is False  # getattr(config, "NON_AUTH_ENDPOINTS", []) is []


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
    def test_incr_returns_count(self):
        storage = MemoryStorage()
        n = storage.incr("key1", window=60)
        assert n == 1
        n = storage.incr("key1", window=60)
        assert n == 2

    def test_cleanup_expired(self):
        storage = MemoryStorage()
        storage.incr("k1", 1)
        storage.cleanup_expired(window=1)


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
