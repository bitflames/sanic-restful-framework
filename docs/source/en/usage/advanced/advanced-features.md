# Other Features

SRF provides many advanced features that help you build more robust and feature-rich API services.

## Feature Overview

This section covers the following advanced features:

### Operations & Maintenance Related

- **[Health Check](health-check.md)**: Monitor the health status of the application and dependent services
- **[Exception Handling](exceptions.md)**: Unified exception handling mechanism
- **[HTTP Status Codes](http-status.md)**: Standardized status code management

### Middleware

- **[Authentication Middleware](middleware/auth-middleware.md)**: Automatically handle user authentication
- **[CSRF Middleware](middleware/csrf-middleware.md)**: Prevent cross-site request forgery attacks
- **[Rate Limiting Middleware](middleware/rate-limiting.md)**: Prevent API abuse and control request frequency

## Quick Navigation

### Health Check

Monitor the health status of the application and dependent services (Redis, PostgreSQL, MongoDB, etc.):

```python
from srf.health.route import bp as health_bp

app.blueprint(health_bp)

# Access /health/ to check health status
```

### Exception Handling

SRF provides a unified exception handling mechanism that automatically converts exceptions into standard HTTP responses:

```python
from srf.exceptions import TargetObjectAlreadyExist

# Raise custom exception
if await Product.filter(sku=sku).exists():
    raise TargetObjectAlreadyExist("This SKU already exists")
```

### HTTP Status Codes

Use semantic status code constants:

```python
from srf.views.http_status import HTTPStatus
from sanic.response import json

return json(data, status=HTTPStatus.HTTP_201_CREATED)
```

### Authentication Middleware

Automatically validate JWT tokens and set user context:

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx

@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)
```

### Rate Limiting Middleware

Control API request frequency to prevent abuse:

```python
from srf.middleware.throttlemiddleware import IPRateLimit, MemoryStorage

storage = MemoryStorage()
app.config.RequestLimiter = [
    IPRateLimit(100, 60, storage),  # 100 requests per 60 seconds
]
```

### CSRF Protection

Prevent cross-site request forgery attacks (in development).

## Usage Recommendations

### Essential for Production Environments

The following features are strongly recommended for production environments:

1. **Health Check**: Integrate with monitoring systems to understand service status in real-time
2. **Rate Limiting Middleware**: Prevent malicious requests and DDoS attacks
3. **Exception Handling**: Provide friendly error messages without exposing internal details
4. **Authentication Middleware**: Automatically handle user authentication

### Useful for Development Environments

The following features can aid in debugging during development:

1. **HTTP Status Codes**: Use semantic constants for more readable code
2. **Exception Handling**: Quickly locate issues and provide detailed error information

## Feature Combination Example

### Complete Production Environment Configuration

```python
from sanic import Sanic
from srf.config import srfconfig
from srf.middleware.authmiddleware import set_user_to_request_ctx
from srf.middleware.throttlemiddleware import IPRateLimit, UserRateLimit, MemoryStorage, throttle_rate
from srf.health.route import bp as health_bp
from srf.views.http_status import HTTPStatus
from sanic.response import json
from sanic.exceptions import NotFound, Forbidden, Unauthorized

app = Sanic("ProductionApp")
srfconfig.set_app(app)

# 1. Configure rate limiting
storage = MemoryStorage()
app.config.RequestLimiter = [
    IPRateLimit(100, 60, storage),      # IP: 100 requests per minute
    UserRateLimit(1000, 60, storage),   # User: 1000 requests per minute
]

# 2. Register middleware
@app.middleware("request")
async def auth_middleware(request):
    """Authentication middleware"""
    await set_user_to_request_ctx(request)

@app.middleware("request")
async def throttle_middleware(request):
    """Rate limiting middleware"""
    if not await throttle_rate(request):
        return json({"error": "Too many requests"}, status=HTTPStatus.HTTP_429_TOO_MANY_REQUESTS)

# 3. Register health check
app.blueprint(health_bp)

# 4. Unified exception handling
@app.exception(NotFound)
async def handle_not_found(request, exception):
    return json(
        {"error": "Resource not found", "message": str(exception)},
        status=HTTPStatus.HTTP_404_NOT_FOUND
    )

@app.exception(Forbidden)
async def handle_forbidden(request, exception):
    return json(
        {"error": "Insufficient permissions", "message": str(exception)},
        status=HTTPStatus.HTTP_403_FORBIDDEN
    )

@app.exception(Unauthorized)
async def handle_unauthorized(request, exception):
    return json(
        {"error": "Unauthorized", "message": "Please log in"},
        status=HTTPStatus.HTTP_401_UNAUTHORIZED
    )

@app.exception(Exception)
async def handle_exception(request, exception):
    import logging
    logging.error(f"Unhandled exception: {exception}", exc_info=True)
    return json(
        {"error": "Server internal error"},
        status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR
    )
```

## Monitoring and Logging

### Logging Configuration

```python
import logging
from sanic.log import logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Use in code
logger.info("Application started")
logger.error("Error occurred", exc_info=True)
```

### Request Logging Middleware

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

### Performance Monitoring

```python
import time

@app.middleware("request")
async def add_start_time(request):
    """Add request start time"""
    request.ctx.start_time = time.time()

@app.middleware("response")
async def add_process_time(request, response):
    """Calculate processing time"""
    if hasattr(request.ctx, 'start_time'):
        process_time = time.time() - request.ctx.start_time
        response.headers['X-Process-Time'] = str(process_time)
```

## Security Best Practices

### 1. Use HTTPS

HTTPS is required in production environments:

```python
# Configure SSL
app.run(
    host="0.0.0.0",
    port=443,
    ssl={
        'cert': '/path/to/cert.pem',
        'key': '/path/to/key.pem'
    }
)
```

### 2. Limit Request Size

```python
app.config.REQUEST_MAX_SIZE = 10 * 1024 * 1024  # 10MB
```

### 3. Set Timeout

```python
app.config.REQUEST_TIMEOUT = 60  # 60 seconds
app.config.RESPONSE_TIMEOUT = 60
```

### 4. Hide Sensitive Information

```python
# Do not enable debug in production
app.run(host="0.0.0.0", port=8000, debug=False)

# Do not expose detailed stack traces in error responses
@app.exception(Exception)
async def handle_exception(request, exception):
    # Log detailed errors to logs
    logger.error(f"Error: {exception}", exc_info=True)
    
    # Return a generic error message to clients
    return json({"error": "Server internal error"}, status=500)
```

### 5. Validate Input

```python
from pydantic import BaseModel, validator

class ProductSchema(BaseModel):
    name: str
    price: float
    
    @validator('price')
    def validate_price(cls, value):
        if value <= 0:
            raise ValueError('Price must be greater than 0')
        if value > 1000000:
            raise ValueError('Price cannot exceed 1 million')
        return value
```

## Performance Optimization

### 1. Use Connection Pooling

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
                }
            }
        },
        "apps": {
            "models": {
                "models": ["models"],
                "default_connection": "default",
            }
        }
    }
)
```

### 2. Use Caching

```python
import aioredis

@app.before_server_start
async def setup_redis(app, loop):
    app.ctx.redis = await aioredis.create_redis_pool(
        'redis://localhost:6379',
        minsize=5,
        maxsize=10
    )

# Use cache in ViewSet
class ProductViewSet(BaseViewSet):
    async def retrieve(self, request, pk):
        # Try to get from cache
        redis = request.app.ctx.redis
        cache_key = f"product:{pk}"
        cached = await redis.get(cache_key)
        
        if cached:
            from sanic.response import json
            import json as json_lib
            return json(json_lib.loads(cached))
        
        # Get from database
        obj = await self.get_object(request, pk)
        schema = self.get_schema(request, is_safe=True)
        data = schema.model_validate(obj).model_dump()
        
        # Store in cache (expires in 10 minutes)
        await redis.setex(cache_key, 600, json_lib.dumps(data))
        
        from sanic.response import json
        return json(data)
```

### 3. Use Asynchronous Operations

```python
import asyncio

class ProductViewSet(BaseViewSet):
    async def create(self, request):
        # Execute multiple asynchronous operations in parallel
        results = await asyncio.gather(
            Product.all().count(),
            Category.all(),
            Brand.all()
        )
        
        product_count, categories, brands = results
```

## Deployment Recommendations

### Use Gunicorn

```bash
gunicorn app:app \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class sanic.worker.GunicornWorker \
  --access-logfile /var/log/access.log \
  --error-logfile /var/log/error.log
```

### Use Supervisor

```ini
[program:myapp]
command=/path/to/venv/bin/gunicorn app:app --bind 0.0.0.0:8000 --workers 4 --worker-class sanic.worker.GunicornWorker
directory=/path/to/app
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/myapp.log
```

### Use Nginx Reverse Proxy

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

## Next Steps

- Learn more about [Health Check](health-check.md)
- Learn how to use [Rate Limiting Middleware](middleware/rate-limiting.md)
- Review best practices for [Exception Handling](exceptions.md)
- Read the [HTTP Status Code](http-status.md) reference