# 健康检查

SRF 提供了内置的健康检查功能，用于监控应用和依赖服务的状态。

## 概述

健康检查是监控系统的重要组成部分，它可以：

- 检测应用是否正常运行
- 监控依赖服务（数据库、缓存等）的可用性
- 集成到负载均衡器和容器编排系统
- 提供早期预警，及时发现问题

## 快速开始

### 1. 注册健康检查路由

```python
from sanic import Sanic
from srf.health.route import bp as health_bp

app = Sanic("MyApp")

# 注册健康检查蓝图
app.blueprint(health_bp)
```

### 2. 配置依赖服务

```python
import aioredis
import asyncpg

@app.before_server_start
async def setup_services(app, loop):
    """初始化依赖服务"""
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

### 3. 访问健康检查端点

```bash
curl http://localhost:8000/health/
```

响应：

```json
{
  "status": "ok",
  "services": {
    "redis": "up",
    "postgres": "up"
  }
}
```

## 内置健康检查

SRF 提供了多个内置的健康检查类。

### RedisCheck

检查 Redis 服务是否可用。

```python
from srf.health.checks import RedisCheck

# 在 app.ctx 中设置 redis 客户端
app.ctx.redis = await aioredis.create_redis_pool('redis://localhost:6379')
```

**检查逻辑**：执行 `PING` 命令

### PostgresCheck

检查 PostgreSQL 数据库是否可用。

```python
from srf.health.checks import PostgresCheck
import asyncpg

# 在 app.ctx 中设置 pg 连接池
app.ctx.pg = await asyncpg.create_pool(
    host='localhost',
    user='user',
    password='pass',
    database='mydb'
)
```

**检查逻辑**：执行 `SELECT 1` 查询

### MongoCheck

检查 MongoDB 是否可用。

```python
from srf.health.checks import MongoCheck
from motor.motor_asyncio import AsyncIOMotorClient

# 在 app.ctx 中设置 mongo 客户端
app.ctx.mongo = AsyncIOMotorClient('mongodb://localhost:27017')
```

**检查逻辑**：执行 `ping` 命令

### SQLiteCheck

检查 SQLite 数据库是否可用。

```python
from srf.health.checks import SQLiteCheck
import aiosqlite

# 在 app.ctx 中设置 sqlite 连接
app.ctx.sqlite = await aiosqlite.connect('db.sqlite3')
```

**检查逻辑**：执行 `SELECT 1` 查询

## 自定义健康检查

### 创建自定义检查类

继承 `BaseHealthCheck` 类：

```python
from srf.health.base import BaseHealthCheck

class CustomServiceCheck(BaseHealthCheck):
    """自定义服务健康检查"""
    
    name = "custom_service"
    
    async def check(self):
        """执行检查
        
        Returns:
            bool: True 表示健康，False 表示异常
        
        Raises:
            Exception: 检查失败时抛出异常
        """
        try:
            # 执行检查逻辑
            service = self.app.ctx.custom_service
            result = await service.ping()
            return result is not None
        except Exception as e:
            raise Exception(f"Custom service check failed: {e}")
```

### 注册自定义检查

```python
from srf.health.base import HealthCheckRegistry

# 注册自定义检查
HealthCheckRegistry.register(CustomServiceCheck)
```

## 健康检查响应

### 成功响应

所有服务健康时：

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

HTTP 状态码：200

### 失败响应

有服务异常时：

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

HTTP 状态码：503 Service Unavailable

## 完整示例

```python
from sanic import Sanic
from srf.health.route import bp as health_bp
from srf.health.base import BaseHealthCheck, HealthCheckRegistry
import aioredis
import asyncpg

app = Sanic("MyApp")

# 自定义健康检查
class APIServiceCheck(BaseHealthCheck):
    """外部 API 服务检查"""
    
    name = "api_service"
    
    async def check(self):
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.example.com/health', timeout=5) as resp:
                    return resp.status == 200
        except Exception as e:
            raise Exception(f"API service unreachable: {e}")

# 注册自定义检查
HealthCheckRegistry.register(APIServiceCheck)

@app.before_server_start
async def setup_services(app, loop):
    """初始化服务"""
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
    """清理服务"""
    app.ctx.redis.close()
    await app.ctx.redis.wait_closed()
    await app.ctx.pg.close()

# 注册健康检查路由
app.blueprint(health_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

## 集成到监控系统

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

### Prometheus 监控

```python
from prometheus_client import Counter, Gauge
from srf.health.base import BaseHealthCheck

# 定义指标
health_check_total = Counter('health_check_total', 'Total health checks', ['service', 'status'])
service_up = Gauge('service_up', 'Service availability', ['service'])

class PrometheusHealthCheck(BaseHealthCheck):
    """带 Prometheus 指标的健康检查"""
    
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

### Nginx 健康检查

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

## 最佳实践

1. **快速响应**：健康检查应该快速返回（< 5秒）
2. **幂等性**：检查不应该有副作用
3. **依赖检查**：检查关键依赖服务的可用性
4. **合理的超时**：设置适当的超时时间
5. **日志记录**：记录健康检查失败的详细信息
6. **区分严重性**：区分关键服务和非关键服务
7. **缓存结果**：对于开销大的检查，可以缓存结果

## 高级用法

### 缓存健康检查结果

```python
import time
from srf.health.base import BaseHealthCheck

class CachedHealthCheck(BaseHealthCheck):
    """带缓存的健康检查"""
    
    name = "cached_service"
    cache_ttl = 60  # 缓存60秒
    
    def __init__(self, app):
        super().__init__(app)
        self._cache = None
        self._cache_time = 0
    
    async def check(self):
        now = time.time()
        
        # 检查缓存
        if self._cache is not None and (now - self._cache_time) < self.cache_ttl:
            return self._cache
        
        # 执行检查
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
        """实际的检查逻辑"""
        # 执行耗时的检查
        pass
```

### 详细的健康检查响应

```python
from srf.health.route import bp
from sanic.response import json

@bp.route('/health/detailed', methods=['GET'])
async def detailed_health_check(request):
    """详细的健康检查"""
    from srf.health.base import HealthCheckRegistry
    
    results = {}
    overall_status = "ok"
    
    for check_class in HealthCheckRegistry.checks:
        check = check_class(request.app)
        name, status = await check.run()
        
        # 解析状态
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

## 监控指标

### 关键指标

1. **可用性**：服务可用的时间百分比
2. **响应时间**：健康检查的平均响应时间
3. **失败率**：健康检查失败的百分比
4. **恢复时间**：从失败到恢复的时间

### 告警策略

```python
# 连续失败3次触发告警
if consecutive_failures >= 3:
    send_alert("Service is down")

# 响应时间超过阈值
if response_time > 5.0:
    send_alert("Service is slow")

# 可用性低于阈值
if availability < 0.99:
    send_alert("Service availability is low")
```

## 故障排查

### 常见问题

1. **连接超时**：检查网络连接和防火墙
2. **认证失败**：检查凭证配置
3. **连接池耗尽**：增加连接池大小
4. **健康检查太慢**：优化检查逻辑或增加超时时间

### 调试健康检查

```python
import logging

logger = logging.getLogger(__name__)

class DebugHealthCheck(BaseHealthCheck):
    """带调试信息的健康检查"""
    
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

## 下一步

- 了解 [异常处理](exceptions.md) 处理健康检查异常
- 学习 [限流](middleware/rate-limiting.md) 保护健康检查端点
- 查看 [HTTP 状态码](http-status.md) 了解状态码使用
