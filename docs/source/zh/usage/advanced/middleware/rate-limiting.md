# 限流

限流中间件用于控制 API 请求频率，防止滥用和保护服务器资源。

## 概述

限流（Rate Limiting）的主要目的：

- **防止滥用**：限制恶意用户的请求频率
- **保护资源**：防止服务器过载
- **公平使用**：确保所有用户都能公平访问
- **防止 DDoS**：缓解分布式拒绝服务攻击

## 快速开始

### 1. 创建存储

```python
from srf.middleware.throttlemiddleware import MemoryStorage

# 创建内存存储
storage = MemoryStorage()
```

### 2. 配置限流规则

```python
from srf.middleware.throttlemiddleware import IPRateLimit, UserRateLimit

app.config.RequestLimiter = [
    IPRateLimit(100, 60, storage),      # IP: 100次/分钟
    UserRateLimit(1000, 60, storage),   # 用户: 1000次/分钟
]
```

### 3. 注册中间件

```python
from srf.middleware.throttlemiddleware import throttle_rate
from sanic.response import json

@app.middleware("request")
async def throttle_middleware(request):
    """限流中间件"""
    if not await throttle_rate(request):
        return json(
            {"error": "请求过于频繁，请稍后再试"},
            status=429
        )
```

## 存储类

### MemoryStorage

基于内存的存储，适用于单机部署。

```python
from srf.middleware.throttlemiddleware import MemoryStorage

storage = MemoryStorage()
```

**特点**：

- 简单易用
- 性能高
- 数据不持久化
- 不支持多实例共享

**适用场景**：

- 开发环境
- 单机部署
- 小规模应用

### Redis 存储（自定义）

对于多实例部署，建议使用 Redis：

```python
import aioredis
import time

class RedisStorage:
    """Redis 存储"""

    def __init__(self, redis_pool):
        self.redis = redis_pool

    async def add(self, key):
        """添加请求记录"""
        now = time.time()
        await self.redis.zadd(key, now, now)

    async def count(self, key, window):
        """统计时间窗口内的请求数"""
        now = time.time()
        cutoff = now - window

        # 删除过期记录
        await self.redis.zremrangebyscore(key, '-inf', cutoff)

        # 统计数量
        return await self.redis.zcard(key)

    async def cleanup(self, key, window):
        """清理过期数据"""
        now = time.time()
        cutoff = now - window
        await self.redis.zremrangebyscore(key, '-inf', cutoff)

# 使用
redis_pool = await aioredis.create_redis_pool('redis://localhost:6379')
storage = RedisStorage(redis_pool)
```

## 限流策略

### IPRateLimit - IP 限流

基于客户端 IP 地址限流。

```python
from srf.middleware.throttlemiddleware import IPRateLimit

# 100次/60秒
limiter = IPRateLimit(
    limit=100,      # 最大请求数
    window=60,      # 时间窗口（秒）
    storage=storage # 存储实例
)
```

**适用场景**：

- 防止单个 IP 滥用
- 防止简单的 DDoS 攻击
- 限制匿名用户

**注意事项**：

- NAT 网络下多个用户共享 IP
- 使用代理或 VPN 可以绕过

### UserRateLimit - 用户限流

基于已认证用户限流。

```python
from srf.middleware.throttlemiddleware import UserRateLimit

# 1000次/60秒
limiter = UserRateLimit(
    limit=1000,
    window=60,
    storage=storage
)
```

**适用场景**：

- 限制认证用户的请求频率
- 不同用户级别使用不同限制
- 防止账号滥用

**特点**：

- 更精确的控制
- 可以区分用户级别
- 需要用户已登录

### PathRateLimit - 路径限流

基于请求路径限流。

```python
from srf.middleware.throttlemiddleware import PathRateLimit

# 特定路径限流
limiter = PathRateLimit(
    limit=10,
    window=60,
    storage=storage
)
```

**适用场景**：

- 保护特定的高成本端点
- 限制敏感操作（如密码重置）
- 不同端点使用不同限制

### HeaderRateLimit - 请求头限流

基于自定义请求头限流。

```python
from srf.middleware.throttlemiddleware import HeaderRateLimit

# 基于 API Key 限流
limiter = HeaderRateLimit(
    limit=500,
    window=60,
    storage=storage,
    header_name='X-API-Key'
)
```

**适用场景**：

- API Key 限流
- 第三方集成限流
- 租户隔离

## 组合使用

可以同时使用多个限流策略：

```python
from srf.middleware.throttlemiddleware import (
    MemoryStorage,
    IPRateLimit,
    UserRateLimit,
    PathRateLimit,
)

storage = MemoryStorage()

app.config.RequestLimiter = [
    # IP 限流：防止恶意攻击
    IPRateLimit(100, 60, storage),

    # 用户限流：针对认证用户
    UserRateLimit(1000, 60, storage),

    # 路径限流：保护特定端点
    PathRateLimit(10, 60, storage),
]

@app.middleware("request")
async def throttle_middleware(request):
    if not await throttle_rate(request):
        from sanic.response import json
        return json({"error": "请求过于频繁"}, status=429)
```

**检查顺序**：

1. 所有限流器按顺序检查
2. 任一限流器拒绝请求，立即返回 429
3. 所有限流器通过，继续处理请求

## 自定义限流器

### 创建自定义限流器

```python
from srf.middleware.throttlemiddleware import BaseRateLimit
import time

class ApiKeyRateLimit(BaseRateLimit):
    """基于 API Key 的限流"""

    def __init__(self, limit, window, storage, key_limits=None):
        super().__init__(limit, window, storage)
        self.key_limits = key_limits or {}

    def get_key(self, request):
        """生成限流键"""
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return None
        return f"api_key:{api_key}"

    def get_limit(self, request):
        """获取限制数（可以为不同 API Key 设置不同限制）"""
        api_key = request.headers.get('X-API-Key')
        return self.key_limits.get(api_key, self.limit)

    async def allow(self, request):
        """检查是否允许请求"""
        key = self.get_key(request)
        if not key:
            return True

        # 获取当前计数
        count = await self.storage.count(key, self.window)
        limit = self.get_limit(request)

        if count >= limit:
            return False

        # 记录请求
        await self.storage.add(key)
        return True

# 使用
limiter = ApiKeyRateLimit(
    limit=100,
    window=60,
    storage=storage,
    key_limits={
        'premium_key_1': 1000,  # 高级用户
        'basic_key_1': 100,     # 基础用户
    }
)
```

### 动态限流

根据服务器负载动态调整限制：

```python
import psutil

class DynamicRateLimit(BaseRateLimit):
    """动态限流"""

    def get_limit(self, request):
        """根据服务器负载动态调整限制"""
        cpu_percent = psutil.cpu_percent()

        if cpu_percent > 80:
            # 高负载：减少限制
            return self.limit // 2
        elif cpu_percent > 60:
            # 中等负载：正常限制
            return self.limit
        else:
            # 低负载：放宽限制
            return self.limit * 2
```

## 限流响应

### 添加限流信息头

```python
@app.middleware("response")
async def add_rate_limit_headers(request, response):
    """添加限流信息到响应头"""
    if hasattr(request.ctx, 'rate_limit_info'):
        info = request.ctx.rate_limit_info
        response.headers['X-RateLimit-Limit'] = str(info['limit'])
        response.headers['X-RateLimit-Remaining'] = str(info['remaining'])
        response.headers['X-RateLimit-Reset'] = str(info['reset'])
```

修改限流器以提供信息：

```python
class EnhancedRateLimit(BaseRateLimit):
    async def allow(self, request):
        key = self.get_key(request)
        count = await self.storage.count(key, self.window)

        # 保存限流信息到请求上下文
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

### 自定义错误响应

```python
@app.middleware("request")
async def throttle_middleware(request):
    if not await throttle_rate(request):
        # 获取限流信息
        info = getattr(request.ctx, 'rate_limit_info', {})

        from sanic.response import json
        return json({
            "error": "请求过于频繁",
            "message": f"您已超过限制（{info.get('limit', 'N/A')} 次/分钟）",
            "retry_after": info.get('reset', 60)
        }, status=429, headers={
            'Retry-After': str(info.get('reset', 60))
        })
```

## 完整示例

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

# 创建存储
storage = MemoryStorage()

# 配置限流规则
app.config.RequestLimiter = [
    # IP 限流：100 次/分钟
    IPRateLimit(100, 60, storage),

    # 用户限流：1000 次/分钟
    UserRateLimit(1000, 60, storage),

    # 路径限流：特定路径 10 次/分钟
    PathRateLimit(10, 60, storage),
]

# 限流中间件
@app.middleware("request")
async def throttle_middleware(request):
    """限流中间件"""
    # 跳过健康检查端点
    if request.path == '/health/':
        return

    if not await throttle_rate(request):
        return json({
            "error": "请求过于频繁",
            "message": "请稍后再试"
        }, status=429, headers={
            'Retry-After': '60'
        })

# 添加限流信息头
@app.middleware("response")
async def add_rate_limit_headers(request, response):
    """添加限流信息"""
    if hasattr(request.ctx, 'rate_limit_info'):
        info = request.ctx.rate_limit_info
        response.headers['X-RateLimit-Limit'] = str(info.get('limit', ''))
        response.headers['X-RateLimit-Remaining'] = str(info.get('remaining', ''))
        response.headers['X-RateLimit-Reset'] = str(info.get('reset', ''))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

## 最佳实践

1. **分级限流**：为不同用户级别设置不同限制
2. **合理的限制**：不要太严格影响正常使用
3. **清晰的错误信息**：告诉用户何时可以重试
4. **监控和告警**：监控限流触发情况
5. **白名单**：为特定 IP 或用户设置白名单
6. **日志记录**：记录被限流的请求
7. **使用 Redis**：生产环境使用 Redis 存储

## 性能优化

### 1. 使用 Redis

```python
import aioredis

@app.before_server_start
async def setup_redis(app, loop):
    app.ctx.redis = await aioredis.create_redis_pool(
        'redis://localhost:6379',
        minsize=5,
        maxsize=10
    )

# 使用 Redis 存储
storage = RedisStorage(app.ctx.redis)
```

### 2. 定期清理

```python
from sanic import Sanic
import asyncio

async def cleanup_task(app):
    """定期清理过期数据"""
    while True:
        await asyncio.sleep(300)  # 5分钟

        # 清理逻辑
        # ...

@app.before_server_start
async def start_cleanup(app, loop):
    app.add_task(cleanup_task(app))
```

### 3. 批量操作

```python
# 批量获取多个键的计数
async def get_counts_batch(keys, window):
    pipeline = redis.pipeline()
    for key in keys:
        pipeline.zcount(key, time.time() - window, '+inf')
    return await pipeline.execute()
```

## 监控和告警

### 记录限流事件

```python
import logging

logger = logging.getLogger(__name__)

@app.middleware("request")
async def throttle_middleware(request):
    if not await throttle_rate(request):
        # 记录限流事件
        logger.warning(
            f"Rate limit exceeded: "
            f"IP={request.ip}, "
            f"Path={request.path}, "
            f"User={getattr(request.ctx, 'user', None)}"
        )

        # 发送告警
        # await send_alert(...)

        return json({"error": "请求过于频繁"}, status=429)
```

### 统计指标

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

        return json({"error": "请求过于频繁"}, status=429)
```

## 下一步

- 学习 [认证中间件](auth-middleware.md) 结合使用
- 阅读 [健康检查](../health-check.md) 监控服务状态
- 查看 [异常处理](../exceptions.md) 处理限流错误
