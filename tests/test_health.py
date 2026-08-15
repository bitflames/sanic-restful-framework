"""Unit tests for srf.health."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from srf.health.checks import BaseHealthCheck, HealthCheckRegistry, RedisCheck, SQLiteCheck
from srf.health.viewset import health_check


def make_app(**clients):
    return SimpleNamespace(ctx=SimpleNamespace(**clients))


class TestHealthCheckRegistry:
    def test_register_and_get_checks(self):
        registry = HealthCheckRegistry()
        assert registry.get_checks() == []
        registry.register("check_a")
        registry.register("check_b")
        assert registry.get_checks() == ["check_a", "check_b"]


class ConcreteHealthCheck(BaseHealthCheck):
    name = "concrete"

    async def check(self):
        pass


class FailingHealthCheck(BaseHealthCheck):
    name = "failing"

    async def check(self):
        raise RuntimeError("service down")


class TestBaseHealthCheck:
    def test_default_timeout(self):
        assert BaseHealthCheck.timeout == 5

    def test_subclass_without_name_raises_on_init(self):
        class NoName(BaseHealthCheck):
            async def check(self):
                pass

        with pytest.raises(AttributeError, match="name"):
            NoName(make_app())

    @pytest.mark.asyncio
    async def test_run_success(self):
        c = ConcreteHealthCheck(make_app(concrete=object()))
        name, status = await c.run()
        assert name == "concrete"
        assert status == "up"

    @pytest.mark.asyncio
    async def test_run_failure(self):
        c = FailingHealthCheck(make_app(failing=object()))
        with patch("srf.health.checks.error_logger.exception") as log_exc:
            name, status = await c.run()
        assert name == "failing"
        assert status == "down"
        assert "service down" not in status
        log_exc.assert_called_once()
        assert log_exc.call_args.args[0] == "Health check %s failed: %s"
        assert log_exc.call_args.args[1:] == ("failing", log_exc.call_args.args[2])
        assert str(log_exc.call_args.args[2]) == "service down"

    @pytest.mark.asyncio
    async def test_base_check_raises(self):
        """BaseHealthCheck.check() must be overridden."""

        class Incomplete(BaseHealthCheck):
            name = "incomplete"

        c = Incomplete(make_app(incomplete=object()))
        with pytest.raises(NotImplementedError, match="Must implement check"):
            await c.check()

    def test_missing_client_raises(self):
        with pytest.raises(ValueError, match="redis not found in app.ctx"):
            RedisCheck(make_app())


class TestBuiltinChecks:
    @pytest.mark.asyncio
    async def test_redis_check(self):
        redis = AsyncMock()
        redis.ping = AsyncMock(return_value=True)
        check = RedisCheck(make_app(redis=redis))
        assert await check.run() == ("redis", "up")

    @pytest.mark.asyncio
    async def test_redis_check_ping_false(self):
        redis = AsyncMock()
        redis.ping = AsyncMock(return_value=False)
        check = RedisCheck(make_app(redis=redis))
        with patch("srf.health.checks.error_logger.exception") as log_exc:
            name, status = await check.run()
        assert name == "redis"
        assert status == "down"
        assert "abnormal ping" in str(log_exc.call_args.args[2])

    @pytest.mark.asyncio
    async def test_sqlite_check(self):
        cursor = AsyncMock()
        cursor.fetchone = AsyncMock(return_value=(1,))
        execute_cm = MagicMock()
        execute_cm.__aenter__ = AsyncMock(return_value=cursor)
        execute_cm.__aexit__ = AsyncMock(return_value=False)

        conn = MagicMock()
        conn.execute = MagicMock(return_value=execute_cm)

        check = SQLiteCheck(make_app(sqlite=conn))
        assert await check.run() == ("sqlite", "up")
        conn.execute.assert_called_once_with("SELECT 1")
        cursor.fetchone.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sqlite_check_with_aiosqlite_memory(self):
        import aiosqlite

        db = await aiosqlite.connect(":memory:")
        try:
            check = SQLiteCheck(make_app(sqlite=db))
            assert await check.run() == ("sqlite", "up")
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_sqlite_check_unexpected_row(self):
        cursor = AsyncMock()
        cursor.fetchone = AsyncMock(return_value=(0,))
        execute_cm = MagicMock()
        execute_cm.__aenter__ = AsyncMock(return_value=cursor)
        execute_cm.__aexit__ = AsyncMock(return_value=False)
        conn = MagicMock()
        conn.execute = MagicMock(return_value=execute_cm)

        check = SQLiteCheck(make_app(sqlite=conn))
        with patch("srf.health.checks.error_logger.exception") as log_exc:
            name, status = await check.run()
        assert name == "sqlite"
        assert status == "down"
        assert "Unexpected SQLite response" in str(log_exc.call_args.args[2])


class TestHealthViewset:
    @pytest.mark.asyncio
    async def test_empty_health_check_list_returns_ok(self):
        request = MagicMock()
        request.app.config.HEALTH_CHECK_LIST = []
        response = await health_check(request)
        assert response.status == 200
        assert response.body == b"{}"

    @pytest.mark.asyncio
    async def test_configured_checks_are_run(self):
        redis = AsyncMock()
        redis.ping = AsyncMock(return_value=True)
        request = MagicMock()
        request.app = make_app(redis=redis)
        request.app.config = SimpleNamespace(HEALTH_CHECK_LIST=[RedisCheck])
        response = await health_check(request)
        assert response.status == 200
        assert b'"redis":"up"' in response.body or b'"redis": "up"' in response.body
        redis.ping.assert_awaited()

    @pytest.mark.asyncio
    async def test_missing_client_fails_endpoint(self):
        redis = AsyncMock()
        redis.ping = AsyncMock(return_value=True)
        request = MagicMock()
        request.app = make_app(redis=redis)
        request.app.config = SimpleNamespace(HEALTH_CHECK_LIST=[RedisCheck, SQLiteCheck])

        with pytest.raises(ValueError, match="sqlite not found in app.ctx"):
            await health_check(request)

    @pytest.mark.asyncio
    async def test_checks_run_in_parallel(self):
        started = {}

        class FirstCheck(BaseHealthCheck):
            name = "first"

            async def check(self):
                started["first"] = asyncio.get_running_loop().time()
                await asyncio.sleep(0.05)

        class SecondCheck(BaseHealthCheck):
            name = "second"

            async def check(self):
                started["second"] = asyncio.get_running_loop().time()
                await asyncio.sleep(0.05)

        request = MagicMock()
        request.app = make_app(first=object(), second=object())
        request.app.config = SimpleNamespace(HEALTH_CHECK_LIST=[FirstCheck, SecondCheck])

        t0 = asyncio.get_running_loop().time()
        response = await health_check(request)
        elapsed = asyncio.get_running_loop().time() - t0

        assert response.status == 200
        assert abs(started["first"] - started["second"]) < 0.04
        assert elapsed < 0.09
