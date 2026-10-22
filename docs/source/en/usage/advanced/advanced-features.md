# Other Features

SRF provides many practical advanced features to help you build more robust and fully featured API services.

## Feature overview

This chapter covers the following advanced features:

### Operations

- **[Health Checks](health-check.md)**: Monitor the health of the application and its dependencies
- **[Exception Handling](exceptions.md)**: Built-in ViewSet conversions and global Sanic handling recommendations
- **[HTTP Status](http-status.md)**: Standardized status code management

### Middleware

- **[Authentication Middleware](middleware/auth-middleware.md)**: Automatically handle user authentication
- **[CSRF Middleware](middleware/csrf-middleware.md)**: Prevent cross-site request forgery attacks
- **[Rate Limiting Middleware](middleware/rate-limiting.md)**: Prevent API abuse and control request frequency

## Recommendations

### Essential for production

The following features are strongly recommended for production environments:

1. **Health checks**: integrate into monitoring systems to know the service status in real time
2. **Rate limiting middleware**: prevent malicious requests and DDoS attacks
3. **Exception handling**: provide friendly error messages without exposing internal details
4. **Authentication middleware**: automatically handle user authentication

### Helpful in development

The following features help with debugging in development environments:

1. **HTTP status codes**: use semantic constants for more readable code
2. **Exception handling**: quickly locate problems and provide detailed error information

## Feature combination examples

For a complete application skeleton that combines configuration, authentication middleware, routing, health checks, and exception handling, see
[Project Setup](../project-setup.md); for how to integrate rate limiters, see [Rate Limiting Middleware](middleware/rate-limiting.md).

## Monitoring and logging

For basic logging configuration, see [Project Setup](../project-setup.md). The following only covers request/response-level monitoring.

### Request logging middleware

```python
@app.middleware("request")
async def log_request(request):
    """Log request information"""
    logger.info(f"{request.method} {request.path} from {request.ip}")


@app.middleware("response")
async def log_response(request, response):
    """Log response information"""
    logger.info(f"{request.method} {request.path} -> {response.status}")
```

### Performance monitoring

```python
import time


@app.middleware("request")
async def add_start_time(request):
    """Record the request start time"""
    request.ctx.start_time = time.time()


@app.middleware("response")
async def add_process_time(request, response):
    """Calculate the processing time"""
    if hasattr(request.ctx, "start_time"):
        process_time = time.time() - request.ctx.start_time
        response.headers["X-Process-Time"] = str(process_time)
```

## Security best practices

### 1. Use HTTPS

Production environments must use HTTPS:

```python
from sanic.log import logger
from sanic.response import json


# Configure SSL
app.run(host="0.0.0.0", port=443, ssl={"cert": "/path/to/cert.pem", "key": "/path/to/key.pem"})
```

### 2. Limit request size

```python
app.config.REQUEST_MAX_SIZE = 10 * 1024 * 1024  # 10MB
```

### 3. Set timeouts

```python
app.config.REQUEST_TIMEOUT = 60  # 60 seconds
app.config.RESPONSE_TIMEOUT = 60
```

### 4. Hide sensitive information

```python
# Do not enable debug in production
app.run(host="0.0.0.0", port=8000, debug=False)


# Do not expose detailed stack traces in error responses
@app.exception(Exception)
async def handle_exception(request, exception):
    # Log detailed errors to the log
    logger.error(f"Error: {exception}", exc_info=True)

    # Return only a generic error to the client
    return json({"error": "Internal server error"}, status=500)
```

### 5. Validate input

```python
from pydantic import BaseModel, field_validator


class ProductSchema(BaseModel):
    name: str
    price: float

    @field_validator("price")
    @classmethod
    def validate_price(cls, value):
        if value <= 0:
            raise ValueError("Price must be greater than 0")
        if value > 1000000:
            raise ValueError("Price cannot exceed 1,000,000")
        return value
```

## Performance optimization

### 1. Use connection pooling

```python
# PostgreSQL connection pool
register_tortoise(
    app,
    config={
        "connections": {
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": "localhost",
                    "port": 5432,
                    "user": "user",
                    "password": "pass",
                    "database": "db",
                    "minsize": 1,
                    "maxsize": 10,  # Connection pool size
                },
            }
        },
        "apps": {
            "models": {
                "models": ["models"],
                "default_connection": "default",
            }
        },
    },
)
```

### 2. Use caching

```python
from redis.asyncio import Redis, ConnectionPool


@app.before_server_start
async def setup_redis(app, loop):
    pool = ConnectionPool.from_url("redis://localhost:6379", max_connections=10)
    app.ctx.redis = Redis(connection_pool=pool)


# Use caching in a ViewSet
class ProductViewSet(BaseViewSet):
    async def retrieve(self, request, pk):
        # Try to get it from the cache
        redis = request.app.ctx.redis
        cache_key = f"product:{pk}"
        cached = await redis.get(cache_key)

        if cached:
            from sanic.response import json
            import json as json_lib

            return json(json_lib.loads(cached))

        # Get it from the database
        obj = await self.get_object(pk)
        schema = self.get_schema()
        data = schema.model_validate(obj).model_dump(mode="json")

        # Store it in the cache (expires in 10 minutes)
        await redis.setex(cache_key, 600, json_lib.dumps(data))

        from sanic.response import json

        return json(data)
```

!!! warning "Caching and object permissions"
    The example above reads the cache before calling `get_object()`, so a cache hit skips object-level permission checks.
    Endpoints that need object-level permissions should perform permission checks first, or set cache keys scoped to the user.

### 3. Use asynchronous operations

```python
import asyncio


class ProductViewSet(BaseViewSet):
    async def create(self, request):
        # Run multiple asynchronous operations in parallel
        results = await asyncio.gather(Product.all().count(), Category.all(), Brand.all())

        product_count, categories, brands = results
```

## Deployment recommendations

### Using Sanic's built-in multiprocessing

Sanic 25 no longer provides `sanic.worker.GunicornWorker`; use the `sanic` command to start multiple workers directly:

```bash
sanic app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Supervisor

```ini
[program:myapp]
command=/path/to/venv/bin/sanic app:app --host 0.0.0.0 --port 8000 --workers 4
directory=/path/to/app
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/myapp.log
```

### Using an Nginx reverse proxy

```nginx
upstream myapp {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://myapp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/static/;
    }
}
```

## Next steps

- Learn about [Health Checks](health-check.md) in detail
- Study how to use [Rate Limiting Middleware](middleware/rate-limiting.md)
- See best practices for [Exception Handling](exceptions.md)
- Read the [HTTP Status](http-status.md) reference
