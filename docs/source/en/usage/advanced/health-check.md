# Health Check

SRF provides a built-in health check functionality to monitor the status of applications and dependent services.

## Overview

Health checks are an essential part of monitoring systems, and they can:

- Detect whether the application is running normally
- Monitor the availability of dependent services (database, cache, etc.)
- Integrate with load balancers and container orchestration systems
- Provide early warnings to identify issues in time

## Quick Start

### 1. Register Health Check Route

```python
from sanic import Sanic
from srf.health.route import bp as health_bp

app = Sanic("MyApp")

# Register health check blueprint
app.blueprint(health_bp)
```

### 2. Configure Dependent Services

```python
import aioredis
import asyncpg

@app.before_server_start
async def setup_services(app, loop):
    """Initialize dependent services"""
    # Redis
    app.ctx.redis = await aioredis.create_redis_pool('redis://localhost:6379')
    
    # PostgreSQL
    app.ctx.pg = await asyncpg.create_pool(
        host='localhost',
        port=5432,
        user='user',
        password='pass',
        database='mydb'
    )
```

### 3. Access the Health Check Endpoint

```bash
curl http://localhost:8000/health/
```

Response:

```json
{
  "status": "ok",
  "services": {
    "redis": "up",
    "postgres": "up"
  }
}
```

## Built-in Health Checks

SRF provides multiple built-in health check classes.

### RedisCheck

Checks if the Redis service is available.

```python
from srf.health.checks import RedisCheck

# Set redis client in app.ctx
app.ctx.redis = await aioredis.create_redis_pool('redis://localhost:6379')
```

**Check Logic**: Execute `PING` command

### PostgresCheck

Checks if the PostgreSQL database is available.

```python
from srf.health.checks import PostgresCheck
import asyncpg

# Set pg connection pool in app.ctx
app.ctx.pg = await asyncpg.create_pool(
    host='localhost',
    user='user',
    password='pass',
    database='mydb'
)
```

**Check Logic**: Execute `SELECT 1` query

### MongoCheck

Checks if MongoDB is available.

```python
from srf.health.checks import MongoCheck
from motor.motor_asyncio import AsyncIOMotorClient

# Set mongo client in app.ctx
app.ctx.mongo = AsyncIOMotorClient('mongodb://localhost:27017')
```

**Check Logic**: Execute `ping` command

### SQLiteCheck

Checks if the SQLite database is available.

```python
from srf.health.checks import SQLiteCheck
import aiosqlite

# Set sqlite connection in app.ctx
app.ctx.sqlite = await aiosqlite.connect('db.sqlite3')
```

**Check Logic**: Execute `SELECT 1` query

## Custom Health Check

### Create a Custom Check Class

Inherit from `BaseHealthCheck` class:

```python
from srf.health.base import BaseHealthCheck

class CustomServiceCheck(BaseHealthCheck):
    """Custom service health check"""
    
    name = "custom_service"
    
    async def check(self):
        """Perform the check
        
        Returns:
            bool: True indicates healthy, False indicates failure
        
        Raises:
            Exception: Raised when the check fails
        """
        try:
            # Perform check logic
            service = self.app.ctx.custom_service
            result = await service.ping()
            return result is not None
        except Exception as e:
            raise Exception(f"Custom service check failed: {e}")
```

### Register Custom Check

```python
from srf.health.base import HealthCheckRegistry

# Register custom check
HealthCheckRegistry.register(CustomServiceCheck)
```

## Health Check Response

### Success Response

When all services are healthy:

```json
{
  "status": "ok",
  "services": {
    "redis": "up",
    "postgres": "up",
    "mongo": "up"
  }
}
```

HTTP status code: 200

### Failure Response

When there is an issue with a service:

```json
{
  "status": "fail",
  "services": {
    "redis": "up",
    "postgres": "down (connection refused)",
    "mongo": "up"
  }
}
```

HTTP status code: 503 Service Unavailable

## Full Example

```python
from sanic import Sanic
from srf.health.route import bp as health_bp
from srf.health.base import BaseHealthCheck, HealthCheckRegistry
import aioredis
import asyncpg

app = Sanic("MyApp")

# Custom health check
class APIServiceCheck(BaseHealthCheck):
    """External API service check"""
    
    name = "api_service"
    
    async def check(self):
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.example.com/health', timeout=5) as resp:
                    return resp.status == 200
        except Exception as e:
            raise Exception(f"API service unreachable: {e}")

# Register custom check
HealthCheckRegistry.register(APIServiceCheck)

@app.before_server_start
async def setup_services(app, loop):
    """Initialize services"""
    # Redis
    app.ctx.redis = await aioredis.create_redis_pool(
        'redis://localhost:6379',
        minsize=1,
        maxsize=10
    )
    
    # PostgreSQL
    app.ctx.pg = await asyncpg.create_pool(
        host='localhost',
        port=5432,
        user='user',
        password='pass',
        database='mydb',
        min_size=1,
        max_size=10
    )

@app.after_server_stop
async def cleanup_services(app, loop):
    """Cleanup services"""
    app.ctx.redis.close()
    await app.ctx.redis.wait_closed()
    await app.ctx.pg.close()

# Register health check route
app.blueprint(health_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

## Integration with Monitoring Systems

### Kubernetes Liveness Probe

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  containers:
  - name: myapp
    image: myapp:latest
    livenessProbe:
      httpGet:
        path: /health/
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
```

### Docker Compose Health Check

```yaml
version: '3.8'

services:
  web:
    image: myapp:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Prometheus Monitoring

```python
from prometheus_client import Counter, Gauge
from srf.health.base import BaseHealthCheck

# Define metrics
health_check_total = Counter('health_check_total', 'Total health checks', ['service', 'status'])
service_up = Gauge('service_up', 'Service availability', ['service'])

class PrometheusHealthCheck(BaseHealthCheck):
    """Health check with Prometheus metrics"""
    
    name = "redis"
    
    async def check(self):
        try:
            result = await self.app.ctx.redis.ping()
            health_check_total.labels(service=self.name, status='success').inc()
            service_up.labels(service=self.name).set(1)
            return True
        except Exception as e:
            health_check_total.labels(service=self.name, status='failure').inc()
            service_up.labels(service=self.name).set(0)
            raise e
```

### Nginx Health Check

```nginx
upstream myapp {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    
    location /health/ {
        proxy_pass http://myapp;
        proxy_connect_timeout 5s;
        proxy_read_timeout 5s;
    }
    
    location / {
        proxy_pass http://myapp;
    }
}
```

## Best Practices

1. **Fast Response**: Health checks should return quickly (< 5 seconds)
2. **Idempotency**: Checks should have no side effects
3. **Dependency Check**: Check availability of critical dependent services
4. **Reasonable Timeout**: Set appropriate timeout values
5. **Logging**: Log detailed information for failed health checks
6. **Severity Differentiation**: Distinguish between critical and non-critical services
7. **Cache Results**: For expensive checks, cache results

## Advanced Usage

### Cache Health Check Results

```python
import time
from srf.health.base import BaseHealthCheck

class CachedHealthCheck(BaseHealthCheck):
    """Health check with caching"""
    
    name = "cached_service"
    cache_ttl = 60  # Cache for 60 seconds
    
    def __init__(self, app):
        super().__init__(app)
        self._cache = None
        self._cache_time = 0
    
    async def check(self):
        now = time.time()
        
        # Check cache
        if self._cache is not None and (now - self._cache_time) < self.cache_ttl:
            return self._cache
        
        # Perform check
        try:
            result = await self._do_check()
            self._cache = True
            self._cache_time = now
            return True
        except Exception as e:
            self._cache = False
            self._cache_time = now
            raise e
    
    async def _do_check(self):
        """Actual check logic"""
        # Perform time-consuming check
        pass
```

### Detailed Health Check Response

```python
from srf.health.route import bp
from sanic.response import json

@bp.route('/health/detailed', methods=['GET'])
async def detailed_health_check(request):
    """Detailed health check"""
    from srf.health.base import HealthCheckRegistry
    
    results = {}
    overall_status = "ok"
    
    for check_class in HealthCheckRegistry.checks:
        check = check_class(request.app)
        name, status = await check.run()
        
        # Parse status
        is_up = "down" not in status.lower()
        
        results[name] = {
            "status": "up" if is_up else "down",
            "message": status,
            "timestamp": time.time()
        }
        
        if not is_up:
            overall_status = "fail"
    
    return json({
        "status": overall_status,
        "timestamp": time.time(),
        "services": results
    }, status=200 if overall_status == "ok" else 503)
```

## Monitoring Metrics

### Key Metrics

1. **Availability**: Percentage of time the service is available
2. **Response Time**: Average response time of health checks
3. **Failure Rate**: Percentage of failed health checks
4. **Recovery Time**: Time from failure to recovery

### Alerting Strategy

```python
# Trigger alert on 3 consecutive failures
if consecutive_failures >= 3:
    send_alert("Service is down")

# Response time exceeds threshold
if response_time > 5.0:
    send_alert("Service is slow")

# Availability falls below threshold
if availability < 0.99:
    send_alert("Service availability is low")
```

## Troubleshooting

### Common Issues

1. **Connection Timeout**: Check network connection and firewall
2. **Authentication Failure**: Check credential configuration
3. **Connection Pool Exhaustion**: Increase connection pool size
4. **Health Check Too Slow**: Optimize check logic or increase timeout

### Debugging Health Check

```python
import logging

logger = logging.getLogger(__name__)

class DebugHealthCheck(BaseHealthCheck):
    """Health check with debug information"""
    
    name = "debug_service"
    
    async def check(self):
        logger.info(f"Starting health check for {self.name}")
        
        try:
            start_time = time.time()
            result = await self._do_check()
            duration = time.time() - start_time
            
            logger.info(f"Health check {self.name} completed in {duration:.2f}s")
            return result
        except Exception as e:
            logger.error(f"Health check {self.name} failed: {e}", exc_info=True)
            raise e
```

## Next Steps

- Learn about [Exception Handling](exceptions.md) for handling health check exceptions
- Study [Rate Limiting](middleware/rate-limiting.md) to protect the health check endpoint
- Review [HTTP Status Codes](http-status.md) for understanding status code usage