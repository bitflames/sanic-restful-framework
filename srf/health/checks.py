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
    name = "base"
    timeout = 5  # seconds

    def __init__(self, app):
        """
        app: Sanic application instance
        """

        self.app = app
        client = getattr(app.ctx, self.name, None)
        if client is None:
            raise ValueError(f"{self.name} not found in app.ctx")
        setattr(self, self.name, client)

    # def __init_subclass__(cls, **kwargs):
    #     HealthCheckRegistry.register(cls)

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
    SQLite health check
    """

    name = "sqlite"

    async def check(self):
        def _ping():
            with self.sqlite.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()

        try:
            async with asyncio.timeout(self.timeout):
                await asyncio.to_thread(_ping)
        except TimeoutError:
            raise RuntimeError(f"SQLite health check timed out after {self.timeout}s") from None
