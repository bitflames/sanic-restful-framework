import asyncio

from sanic.log import error_logger


class HealthCheckRegistry:
    def __init__(self):
        self.checks = []

    def register(self, check_class):
        self.checks.append(check_class)

    def get_checks(self):
        return self.checks


class BaseHealthCheck:
    name: str
    timeout = 5  # seconds

    # def __init_subclass__(cls, **kwargs):
    #     HealthCheckRegistry.register(cls)

    def __init__(self, app):
        """
        app: Sanic application instance.

        Requires ``app.ctx.<name>`` to already be set. Missing client is a
        programming error and must not be reported as a check ``down``.
        """
        self.app = app
        client = getattr(app.ctx, self.name, None)
        if client is None:
            raise ValueError(f"{self.name} not found in app.ctx")
        setattr(self, self.name, client)

    async def check(self):
        raise NotImplementedError("Must implement check()")

    async def run(self):
        try:
            await self.check()
            return (self.name, "up")
        except Exception as e:  # noqa: BLE001
            error_logger.exception("Health check %s failed: %s", self.name, e)
            return (self.name, "down")


# Redis
class RedisCheck(BaseHealthCheck):
    """
    Redis health check
    """

    name = "redis"

    async def check(self):
        try:
            async with asyncio.timeout(self.timeout):
                pong = await self.redis.ping()
                if not pong:
                    raise RuntimeError("Redis returned abnormal ping response")
        except TimeoutError:
            raise RuntimeError(f"Redis health check timed out after {self.timeout}s") from None


# sqlite
class SQLiteCheck(BaseHealthCheck):
    """
    aiosqlite health check.

    Requires ``app.ctx.sqlite`` to be an ``aiosqlite.Connection`` (not stdlib sqlite3).
    """

    name = "sqlite"

    async def check(self):
        try:
            async with asyncio.timeout(self.timeout):
                async with self.sqlite.execute("SELECT 1") as cursor:
                    row = await cursor.fetchone()
                    if row != (1,):
                        raise RuntimeError("Unexpected SQLite response")
        except TimeoutError:
            raise RuntimeError(f"SQLite health check timed out after {self.timeout}s") from None
