# Rate Limiting

The rate limiting middleware is used to control the frequency of API requests, preventing abuse and protecting server resources.

## Overview

The main purpose of rate limiting:

- **Prevent Abuse**: Limit the request frequency of malicious users
- **Protect Resources**: Prevent server overload
- **Fair Usage**: Ensure all users can access fairly
- **Prevent DDoS**: Mitigate distributed denial-of-service attacks

## Quick Start

### 1. Create Storage

```python
from srf.middleware.throttlemiddleware import MemoryStorage

# Create memory storage
storage = MemoryStorage()
```

### 2. Configure Rate Limit Rules

```python
from srf.middleware.throttlemiddleware import IPRateLimit, UserRateLimit

app.config.RequestLimiter = [
    IPRateLimit(100, 60, storage),      # IP: 100 requests per minute
    UserRateLimit(1000, 60, storage),   # User: 1000 requests per minute
]
```

### 3. Register Middleware

```python
from srf.middleware.throttlemiddleware import throttle_rate
from sanic.response import json

@app.middleware("request")
async def throttle_middleware(request):
    """Rate limiting middleware"""
    if not await throttle_rate(request):
        return json(
            {"error": "Too many requests, please try again later"},
            status=429
        )
```

## Storage Classes

### MemoryStorage

Memory-based storage, suitable for single-machine deployment.

```python
from srf.middleware.throttlemiddleware import MemoryStorage

storage = MemoryStorage()
```

**Features**:

- Easy to use
- High performance
- Data is not persistent
- Does not support sharing between multiple instances

**Use Cases**:

- Development environment
- Single machine deployment
- Small-scale applications

### Redis Storage (Custom)

For multi-instance deployment, it is recommended to use Redis:

```python
import aioredis
import time

class RedisStorage:
    """Redis storage"""

    def __init__(self, redis_pool):
        self.redis = redis_pool

    async def add(self, key):
        """Add a request record"""
        now = time.time()
        await self.redis.zadd(key, now, now)

    async def count(self, key, window):
        """Count the number of requests in the time window"""
        now = time.time()
        cutoff = now - window

        # Remove expired records
        await self.redis.zremrangebyscore(key, '-inf', cutoff)

        # Count the number
        return await self.redis.zcard(key)

    async def cleanup(self, key, window):
        """Clean up expired data"""
        now = time.time()
        cutoff = now - window
        await self.redis.zremrangebyscore(key, '-inf', cutoff)

# Usage
redis_pool = await aioredis.create_redis_pool('redis://localhost:6379')
storage = RedisStorage(redis_pool)
```

## Rate Limiting Strategies

### IPRateLimit - IP Rate Limiting

Rate limiting based on client IP address.

```python
from srf.middleware.throttlemiddleware import IPRateLimit

# 100 requests / 60 seconds
limiter = IPRateLimit(
    limit=100,      # Maximum number of requests
    window=60,      # Time window (seconds)
    storage=storage # Storage instance
)
```

**Use Cases**:

- Prevent a single IP from being abused
- Prevent simple DDoS attacks
- Limit anonymous users

**Notes**:

- Multiple users share an IP in a NAT network
- Can be bypassed using a proxy or VPN

### UserRateLimit - User Rate Limiting

Rate limiting based on authenticated users.

```python
from srf.middleware.throttlemiddleware import UserRateLimit

# 1000 requests / 60 seconds
limiter = UserRateLimit(
    limit=1000,
    window=60,
    storage=storage
)
```

**Use Cases**:

- Limit the request frequency of authenticated users
- Different user levels have different limits
- Prevent account abuse

**Features**:

- More precise control
- Can distinguish user levels
- Requires user login

### PathRateLimit - Path Rate Limiting

Rate limiting based on request path.

```python
from srf.middleware.throttlemiddleware import PathRateLimit

# Specific path rate limiting
limiter = PathRateLimit(
    limit=10,
    window=60,
    storage=storage
)
```

**Use Cases**:

- Protect specific high-cost endpoints
- Limit sensitive operations (e.g., password reset)
- Different endpoints have different limits

### HeaderRateLimit - Request Header Rate Limiting

Rate limiting based on custom request headers.

```python
from srf.middleware.throttlemiddleware import HeaderRateLimit

# Rate limiting based on API Key
limiter = HeaderRateLimit(
    limit=500,
    window=60,
    storage=storage,
    header_name='X-API-Key'
)
```

**Use Cases**:

- API Key rate limiting
- Third-party integration rate limiting
- Tenant isolation

## Combining Strategies

Multiple rate limiting strategies can be used simultaneously:

```python
from srf.middleware.throttlemiddleware import (
    MemoryStorage,
    IPRateLimit,
    UserRateLimit,
    PathRateLimit,
)

storage = MemoryStorage()

app.config.RequestLimiter = [
    # IP rate limiting: prevent malicious attacks
    IPRateLimit(100, 60, storage),

    # User rate limiting: for authenticated users
    UserRateLimit(1000, 60, storage),

    # Path rate limiting: protect specific endpoints
    PathRateLimit(10, 60, storage),
]

@app.middleware("request")
async def throttle_middleware(request):
    if not await throttle_rate(request):
        from sanic.response import json
        return json({"error": "Too many requests"}, status=429)
```

**Check Order**:

1. All rate limiters are checked in order
2. If any rate limiter rejects the request, immediately return 429
3. If all rate limiters pass, continue processing the request

## Custom Rate Limiter

### Creating a Custom Rate Limiter

```python
from srf.middleware.throttlemiddleware import BaseRateLimit
import time

class ApiKeyRateLimit(BaseRateLimit):
    """Rate limiting based on API Key"""

    def __init__(self, limit, window, storage, key_limits=None):
        super().__init__(limit, window, storage)
        self.key_limits = key_limits or {}

    def get_key(self, request):
        """Generate a rate limiting key"""
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return None
        return f"api_key:{api_key}"

    def get_limit(self, request):
        """Get the limit (can set different limits for different API Keys)"""
        api_key = request.headers.get('X-API-Key')
        return self.key_limits.get(api_key, self.limit)

    async def allow(self, request):
        """Check if the request is allowed"""
        key = self.get_key(request)
        if not key:
            return True

        # Get current count
        count = await self.storage.count(key, self.window)
        limit = self.get_limit(request)

        if count >= limit:
            return False

        # Record the request
        await self.storage.add(key)
        return True

# Usage
limiter = ApiKeyRateLimit(
    limit=100,
    window=60,
    storage=storage,
    key_limits={
        'premium_key_1': 1000,  # Premium user
        'basic_key_1': 100,     # Basic user
    }
)
```

### Dynamic Rate Limiting

Adjust the limit based on server load:

```python
import psutil

class DynamicRateLimit(BaseRateLimit):
    """Dynamic rate limiting"""

    def get_limit(self, request):
        """Dynamically adjust the limit based on server load"""
        cpu_percent = psutil.cpu_percent()

        if cpu_percent > 80:
            # High load: reduce limit
            return self.limit // 2
        elif cpu_percent > 60:
            # Medium load: normal limit
            return self.limit
        else:
            # Low load: relax the limit
            return self.limit * 2
```

## Rate Limit Response

### Add Rate Limit Headers

```python
@app.middleware("response")
async def add_rate_limit_headers(request, response):
    """Add rate limit information to the response header"""
    if hasattr(request.ctx, 'rate_limit_info'):
        info = request.ctx.rate_limit_info
        response.headers['X-RateLimit-Limit'] = str(info['limit'])
        response.headers['X-RateLimit-Remaining'] = str(info['remaining'])
        response.headers['X-RateLimit-Reset'] = str(info['reset'])
```

Modify the rate limiter to provide information:

```python
class EnhancedRateLimit(BaseRateLimit):
    async def allow(self, request):
        key = self.get_key(request)
        count = await self.storage.count(key, self.window)

        # Save rate limit information to the request context
        import time
        request.ctx.rate_limit_info = {
            'limit': self.limit,
            'remaining': max(0, self.limit - count),
            'reset': int(time.time() + self.window)
        }

        if count >= self.limit:
            return False

        await self.storage.add(key)
        return True
```

### Custom Error Response

```python
@app.middleware("request")
async def throttle_middleware(request):
    if not await throttle_rate(request):
        # Get rate limit information
        info = getattr(request.ctx, 'rate_limit_info', {})

        from sanic.response import json
        return json({
            "error": "Too many requests",
            "message": f"You have exceeded the limit ({info.get('limit', 'N/A')} requests per minute)",
            "retry_after": info.get('reset', 60)
        }, status=429, headers={
            'Retry-After': str(info.get('reset', 60))
        })
```

## Complete Example

```python
from sanic import Sanic
from srf.middleware.throttlemiddleware import (
    MemoryStorage,
    IPRateLimit,
    UserRateLimit,
    PathRateLimit,
    throttle_rate
)
from sanic.response import json

app = Sanic("MyApp")

# Create storage
storage = MemoryStorage()

# Configure rate limiting rules
app.config.RequestLimiter = [
    # IP rate limiting: 100 requests per minute
    IPRateLimit(100, 60, storage),

    # User rate limiting: 1000 requests per minute
    UserRateLimit(1000, 60, storage),

    # Path rate limiting: 10 requests per minute for specific paths
    PathRateLimit(10, 60, storage),
]

# Rate limiting middleware
@app.middleware("request")
async def throttle_middleware(request):
    """Rate limiting middleware"""
    # Skip health check endpoint
    if request.path == '/health/':
        return

    if not await throttle_rate(request):
        return json({
            "error": "Too many requests",
            "message": "Please try again later"
        }, status=429, headers={
            'Retry-After': '60'
        })

# Add rate limit headers
@app.middleware("response")
async def add_rate_limit_headers(request, response):
    """Add rate limit information"""
    if hasattr(request.ctx, 'rate_limit_info'):
        info = request.ctx.rate_limit_info
        response.headers['X-RateLimit-Limit'] = str(info.get('limit', ''))
        response.headers['X-RateLimit-Remaining'] = str(info.get('remaining', ''))
        response.headers['X-RateLimit-Reset'] = str(info.get('reset', ''))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

## Best Practices

1. **Tiered Rate Limiting**: Set different limits for different user levels
2. **Reasonable Limits**: Not too strict to affect normal usage
3. **Clear Error Messages**: Tell users when they can retry
4. **Monitoring and Alerts**: Monitor rate limiting triggers
5. **Whitelist**: Set a whitelist for specific IPs or users
6. **Logging**: Log rate-limited requests
7. **Use Redis**: Use Redis storage in production environments

## Performance Optimization

### 1. Use Redis

```python
import aioredis

@app.before_server_start
async def setup_redis(app, loop):
    app.ctx.redis = await aioredis.create_redis_pool(
        'redis://localhost:6379',
        minsize=5,
        maxsize=10
    )

# Use Redis storage
storage = RedisStorage(app.ctx.redis)
```

### 2. Regular Cleanup

```python
from sanic import Sanic
import asyncio

async def cleanup_task(app):
    """Regularly clean up expired data"""
    while True:
        await asyncio.sleep(300)  # 5 minutes

        # Cleanup logic
        # ...

@app.before_server_start
async def start_cleanup(app, loop):
    app.add_task(cleanup_task(app))
```

### 3. Batch Operations

```python
# Batch get counts for multiple keys
async def get_counts_batch(keys, window):
    pipeline = redis.pipeline()
    for key in keys:
        pipeline.zcount(key, time.time() - window, '+inf')
    return await pipeline.execute()
```

## Monitoring and Alerting

### Record Rate Limit Events

```python
import logging

logger = logging.getLogger(__name__)

@app.middleware("request")
async def throttle_middleware(request):
    if not await throttle_rate(request):
        # Record rate limit event
        logger.warning(
            f"Rate limit exceeded: "
            f"IP={request.ip}, "
            f"Path={request.path}, "
            f"User={getattr(request.ctx, 'user', None)}"
        )

        # Send alert
        # await send_alert(...)

        return json({"error": "Too many requests"}, status=429)
```

### Metric Statistics

```python
from prometheus_client import Counter

rate_limit_exceeded = Counter(
    'rate_limit_exceeded_total',
    'Total rate limit exceeded',
    ['path', 'method']
)

@app.middleware("request")
async def throttle_middleware(request):
    if not await throttle_rate(request):
        rate_limit_exceeded.labels(
            path=request.path,
            method=request.method
        ).inc()

        return json({"error": "Too many requests"}, status=429)
```

## Next Steps

- Learn [Authentication Middleware](auth-middleware.md) for combined use
- Read [Health Check](../health-check.md) to monitor service status
- View [Exception Handling](../exceptions.md) to handle rate limiting errors
