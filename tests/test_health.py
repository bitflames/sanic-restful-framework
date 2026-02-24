"""Unit tests for srf.health."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from srf.health.base import BaseHealthCheck, HealthCheckRegistry


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
    @pytest.mark.asyncio
    async def test_run_success(self):
        c = ConcreteHealthCheck()
        name, status = await c.run()
        assert name == "concrete"
        assert status == "up"

    @pytest.mark.asyncio
    async def test_run_failure(self):
        c = FailingHealthCheck()
        name, status = await c.run()
        assert name == "failing"
        assert status.startswith("down (")

    @pytest.mark.asyncio
    async def test_base_check_raises(self):
        """BaseHealthCheck.check() must be overridden."""
        class Incomplete(BaseHealthCheck):
            name = "incomplete"

        c = Incomplete()
        with pytest.raises(NotImplementedError, match="Must implement check"):
            await c.check()
