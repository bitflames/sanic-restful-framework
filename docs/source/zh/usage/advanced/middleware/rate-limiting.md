# 限流

SRF 提供固定时间窗口内的内存计数器和四种限流键。

## 快速开始

```python
from sanic.response import json
from srf.middleware.throttlemiddleware import (
    IPRateLimit,
    MemoryStorage,
    UserRateLimit,
    throttle_rate,
)

storage = MemoryStorage()
app.config.REQUEST_LIMITERS = [
    IPRateLimit(limit=100, window=60, storage=storage),
    UserRateLimit(limit=1000, window=60, storage=storage),
]


@app.middleware("request")
async def throttle_middleware(request):
    if not await throttle_rate(request):
        return json({"error": "请求过于频繁"}, status=429)
```

`throttle_rate()` 按顺序调用 `app.config.REQUEST_LIMITERS` 中每个限流器的
`allow(request)`；任一个返回假即拒绝。未配置时视为空列表（不限流）。

## MemoryStorage

`MemoryStorage.incr(key, window)` 是同步方法。它删除当前 key 中窗口外的
时间戳、追加本次请求并返回窗口内数量。

```python
storage = MemoryStorage()
count = storage.incr("ip:127.0.0.1", window=60)
```

该存储只适用于开发或单进程部署：

- 不跨进程或实例共享。
- 重启后数据丢失。
- 每个活跃 key 保存窗口内所有请求时间戳。
- 过期 key 不会自动全局清理；可定期调用
  `storage.cleanup_expired(window)`。

## 内置限流器

### IPRateLimit

```python
IPRateLimit(limit=100, window=60, storage=storage)
```

key 为 `ip:<request.remote_addr>`。部署在反向代理后时，应先正确配置可信代理，
否则客户端地址可能不准确。

### UserRateLimit

```python
UserRateLimit(limit=1000, window=60, storage=storage)
```

已认证用户的 key 为 `user:<user.id>`；没有 `request.ctx.user` 时，所有匿名
请求共享 `"anonymous"`。如需按用户限流，认证中间件必须先运行。

### PathRateLimit

```python
PathRateLimit(limit=10, window=60, storage=storage)
```

key 只有 `path:<request.path>`。这意味着同一路径上的所有用户共享一个桶，
并不是“每个用户在每个路径上的限制”。

### HeaderRateLimit

构造参数名是 `header`：

```python
HeaderRateLimit(
    header="X-API-Key",
    limit=500,
    window=60,
    storage=storage,
)
```

key 为 `header:<头名>:<值>`。缺少该请求头时，所有请求共享值为 `None` 的桶；
如果请求头用于身份识别，应先显式拒绝缺失值。

## 自定义限流器

```python
from srf.middleware.throttlemiddleware import BaseRateLimit


class MethodRateLimit(BaseRateLimit):
    def __init__(self, limit, window, storage):
        super().__init__(limit, window)
        self.storage = storage

    async def get_key(self, request):
        return f"method:{request.method}"

    async def allow(self, request):
        key = await self.get_key(request)
        return self.storage.incr(key, self.window) <= self.limit
```

`BaseRateLimit.__init__()` 只接收 `limit` 和 `window`；存储由子类自行保存。

## 使用 Redis

内置限流器要求存储对象提供同步 `incr(key, window) -> int`，因此不能直接把
异步 Redis 客户端或仅提供 `add()`/`count()` 的对象传进去。生产环境应实现
完整的异步限流器，并用 Lua 脚本或事务保证“清理、计数、追加、过期”原子化，
而不是只替换 `storage`。

## 生产限制

当前实现没有自动生成 `Retry-After` 或 `X-RateLimit-*` 响应头，没有白名单、
分级策略和指标。`MemoryStorage` 也不适用于多 worker。公开部署前应根据实际
拓扑补充共享存储、代理 IP 处理、指标和测试。

## 下一步

- 阅读[认证中间件](auth-middleware.md)确认中间件顺序。
- 阅读[健康检查](../health-check.md)配置监控端点。
