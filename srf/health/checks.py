import asyncio

from .base import BaseHealthCheck


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
