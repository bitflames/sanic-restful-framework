# Health Checks

SRF provides built-in health check functionality for monitoring the status of the application and its dependencies.

## Overview

Health checks are an important part of monitoring systems. They can:

- Detect whether the application is running normally
- Monitor the availability of dependent services (databases, caches, etc.)
- Integrate with load balancers and container orchestration systems
- Provide early warning so problems are found in time

## Quick start

Redis is already included in SRF's dependencies; `aiosqlite`, used by the SQLite check, is an optional dependency and requires
`pip install aiosqlite`.

### 1. Register the health check route and configure the check list

The route reads `app.config.HEALTH_CHECK_LIST` (an empty list by default) and runs each check class in it once.

```python
from sanic import Sanic
from srf.health.checks import RedisCheck, SQLiteCheck
from srf.health.route import health_check

app = Sanic("MyApp")
app.config.HEALTH_CHECK_LIST = [RedisCheck, SQLiteCheck]
app.add_route(health_check, "/health", methods=["GET"])
```

### 2. Configure the dependent services

Check classes read clients from `app.ctx` by `name`. The Redis check uses `app.ctx.redis`; the SQLite check requires `app.ctx.sqlite` to be an `aiosqlite.Connection`.

```python
from aiosqlite import connect
from redis.asyncio import Redis


@app.before_server_start
async def setup_services(app):
    app.ctx.redis = Redis.from_url("redis://localhost:6379/0")
    app.ctx.sqlite = await connect("db.sqlite3")
```

### 3. Access the health check endpoint

```bash
curl http://localhost:8000/health
```

The response is a JSON mapping from check names to statuses, for example:

```json
{ "redis": "up", "sqlite": "down" }
```

Even when a check returns `"down"`, the current handler still returns HTTP 200. If the client has not been mounted on `app.ctx` in advance, constructing the check instance raises an exception, which Sanic handles.

## Built-in health checks

SRF provides the following check classes.

### RedisCheck

```python
from srf.health.checks import RedisCheck
from redis.asyncio import Redis

app.ctx.redis = Redis.from_url("redis://localhost:6379/0")
```

The check logic calls `ping()`, with a default timeout of 5 seconds.

### SQLiteCheck

```python
from srf.health.checks import SQLiteCheck
from aiosqlite import connect

app.ctx.sqlite = await connect("db.sqlite3")
```

The check logic executes `SELECT 1`. This check requires `aiosqlite`; the standard library synchronous `sqlite3.Connection` cannot be used.

## Custom health checks

Subclass `BaseHealthCheck`, set `name`, implement `check()`, and add the check class to `HEALTH_CHECK_LIST`. On construction the framework reads `app.ctx.<name>` and sets it as an instance attribute with the same name. `run()` returns `(name, "up")` when the check succeeds, and logs the failure and returns `(name, "down")` when it fails.

```python
from srf.health.checks import BaseHealthCheck


class APIServiceCheck(BaseHealthCheck):
    name = "api_service"
    timeout = 5

    async def check(self):
        await self.api_service.ping()


# The application initializes and creates the API client
app.ctx.api_service = api_client
app.config.HEALTH_CHECK_LIST = [APIServiceCheck]
```

## Complete example

```python
from sanic import Sanic
from redis.asyncio import Redis
from aiosqlite import connect
from srf.health.checks import RedisCheck, SQLiteCheck
from srf.health.route import health_check

app = Sanic("MyApp")
app.config.HEALTH_CHECK_LIST = [RedisCheck, SQLiteCheck]
app.add_route(health_check, "/health", methods=["GET"])


@app.before_server_start
async def setup_services(app):
    app.ctx.redis = Redis.from_url("redis://localhost:6379/0")
    app.ctx.sqlite = await connect("db.sqlite3")


@app.after_server_stop
async def cleanup_services(app):
    await app.ctx.redis.aclose()
    await app.ctx.sqlite.close()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
```

## Best practices

1. Checks should complete quickly and have reasonable timeouts.
2. Checks should avoid side effects.
3. Only add dependencies that need monitoring to `HEALTH_CHECK_LIST`.
4. Initialize the clients that checks depend on at application startup and close them on shutdown.
5. If a load balancer needs a non-200 failure status, wrap `health_check` at the application layer and implement the appropriate status code.

## Next steps

- Learn about [Exception Handling](exceptions.md) to handle health check exceptions
- Study [Rate Limiting](middleware/rate-limiting.md) to protect the health check endpoint
- See [HTTP Status](http-status.md) to learn about using status codes
