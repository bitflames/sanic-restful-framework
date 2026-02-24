from .base import BaseHealthCheck

# import asyncpg, aioredis, motor.motor_asyncio


# Redis
class RedisCheck(BaseHealthCheck):
    name = "redis"

    def __init__(self, redis):
        self.redis = redis

    async def check(self):
        pong = await self.redis.ping()  # TODO based on sanic init
        if not pong:
            raise Exception("Redis ping failed")


# PostgreSQL
class PostgresCheck(BaseHealthCheck):
    name = "postgres"

    def __init__(self, pool):
        self.pool = pool

    async def check(self):
        async with self.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")


# MongoDB
class MongoCheck(BaseHealthCheck):
    name = "mongodb"

    def __init__(self, mongo_client):
        self.mongo = mongo_client

    async def check(self):
        await self.mongo.admin.command("ping")


# sqlite
class SQLiteCheck(BaseHealthCheck):
    name = "sqlite"

    def __init__(self, conn):
        self.conn = conn

    async def check(self):
        def _ping():
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()

        # sqlite is synchronous, so it is packaged as a thread task
        import asyncio

        await asyncio.to_thread(_ping)
