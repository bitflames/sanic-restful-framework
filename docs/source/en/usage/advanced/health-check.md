# Health Check

SRF provides a built-in health check feature to monitor the status of the application and dependent services.

## Overview

Health checks are an essential part of monitoring systems, and they can:

- Detect whether the application is running normally
- Monitor the availability of dependent services (database, cache, etc.)
- Integrate with load balancers and container orchestration systems
- Provide early warnings to identify issues promptly

## Quick Start

### 1. Register Health Check Route and Configure Check List

The route reads `app.config.HEALTH_CHECK_LIST` (default is empty list), and performs each check class in it once.

```python
from sanic import Sanic
from srf.health.route import bp as health_bp
from srf.health.checks import RedisCheck, SQLiteCheck

app = Sanic("MyApp")

# Configure the checks to be performed (order corresponds to services in response)
app.config.HEALTH_CHECK_LIST = [RedisCheck, SQLiteCheck]

# Register the health check blueprint
app.blueprint(health_bp)
```

### 2. Configure Dependent Services

Each check class retrieves the client from `app.ctx.<name>`. Built-in checks correspond to:

- `RedisCheck.name == "redis"` → `app.ctx.redis`
- `SQLiteCheck.name == "sqlite"` → `app.ctx.sqlite`

```python
from redis.asyncio import Redis
import sqlite3

@app.before_server_start
async def setup_services(app, loop):
    """Initialize dependent services"""
    app.ctx.redis = Redis.from_url("redis://localhost:6379")
    # SQLiteCheck uses this connection in a thread, so allow cross-thread access.
    app.ctx.sqlite = sqlite3.connect(
        "db.sqlite3", check_same_thread=False
    )
```

### 3. Access the Health Check Endpoint

```bash
curl http://localhost:8000/health/
```

Response when all are healthy (HTTP 200):

```json
{
  "status": "ok",
  "services": {
    "redis": "up",
    "sqlite": "up"
  }
}
```

Response when some service is unhealthy (HTTP 500):

```json
{
  "status": "fail",
  "services": {
    "redis": "up",
    "sqlite": "down (unable to open database file)"
  }
}
```

## Built-in Health Checks

SRF provides several built-in health check classes.

### RedisCheck

```python
from srf.health.checks import RedisCheck
from redis.asyncio import Redis

app.ctx.redis = Redis.from_url("redis://localhost:6379")

```

**Check Logic**: Execute the `PING` command.

### SQLiteCheck

```python
from srf.health.checks import SQLiteCheck
import sqlite3

app.ctx.sqlite = sqlite3.connect("db.sqlite3", check_same_thread=False)
```

**Check Logic**: Execute `SELECT 1` query.

## Custom Health Check

Inherit from `BaseHealthCheck`, set `name`, implement `check()`, and add the class to `HEALTH_CHECK_LIST`.  
During construction, it reads the client from `app.ctx.<name>` and attaches it to `self.<name>`.  
The base class defaults to `timeout = 5` (seconds); built-in Redis/SQLite checks use `asyncio.timeout(self.timeout)`.

```python
from srf.health.base import BaseHealthCheck

class APIServiceCheck(BaseHealthCheck):
    """Check for external API service"""

    name = "api_service"
    timeout = 5  # Can override BaseHealthCheck.timeout

    async def check(self):
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.example.com/health", timeout=self.timeout
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"unexpected status {resp.status}")


# Mount the client before using
# app.ctx.api_service = ...

app.config.HEALTH_CHECK_LIST = [
    RedisCheck,
    SQLiteCheck,
    APIServiceCheck,
]
```

Throw an exception in `check()` when the check fails; `run()` will format it into `"down (<error message>)"`.

## Full Example

```python
from sanic import Sanic
from redis.asyncio import Redis, ConnectionPool
import sqlite3

from srf.health.route import bp as health_bp
from srf.health.checks import RedisCheck, SQLiteCheck
from srf.health.base import BaseHealthCheck

app = Sanic("MyApp")


class APIServiceCheck(BaseHealthCheck):
    name = "api_service"

    async def check(self):
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.example.com/health", timeout=5
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"API unreachable: {resp.status}")


app.config.HEALTH_CHECK_LIST = [RedisCheck, SQLiteCheck, APIServiceCheck]


@app.before_server_start
async def setup_services(app, loop):
    pool = ConnectionPool.from_url("redis://localhost:6379", max_connections=10)
    app.ctx.redis = Redis(connection_pool=pool)
    app.ctx.sqlite = sqlite3.connect(
        "db.sqlite3", check_same_thread=False
    )
    # Client required for custom checks (example placeholder; replace with your SDK in real scenarios)
    app.ctx.api_service = object()


@app.after_server_stop
async def cleanup_services(app, loop):
    await app.ctx.redis.aclose()
    app.ctx.sqlite.close()


app.blueprint(health_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```



## Best Practices

1. **Fast Response**: Health checks should return quickly (< 5 seconds)
2. **Idempotency**: Checks should not have side effects
3. **Dependency Checks**: Check availability of critical dependent services
4. **Reasonable Timeout**: Set appropriate timeout values
5. **Logging**: Log detailed information about failed health checks
6. **Severity Differentiation**: Distinguish between critical and non-critical services
7. **Selective Configuration**: Only include checks that are truly needed in `HEALTH_CHECK_LIST`

## Next Steps

- Learn about [Exception Handling](exceptions.md) to handle health check exceptions
- Study [Rate Limiting](middleware/rate-limiting.md) to protect the health check endpoint
- Review [HTTP Status Codes](http-status.md) to understand usage