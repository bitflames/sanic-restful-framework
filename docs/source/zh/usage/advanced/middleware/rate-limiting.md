# 限流

SRF 在 `srf.middleware.throttlemiddleware` 中提供限流组件，由应用按需接入。

## 组件声明

- **限流器**：`IPRateLimit`、`UserRateLimit`、`PathRateLimit`、`HeaderRateLimit`，均继承 `BaseRateLimit(limit, window, storage)`；自定义限流器只需实现 `get_key(request)`。
- **存储**：`MemoryStorage`（单进程滑动窗口，仅适合开发）和 `RedisStorage`（多进程可用的固定窗口）。
- **执行入口**：`throttle_rate(request)` 按顺序调用 `app.config.REQUEST_LIMITERS` 中每个限流器的 `allow(request)`，任一返回假即拒绝；未配置时视为不限流。

## 接入示例

```python
from sanic.response import json
from srf.middleware.throttlemiddleware import IPRateLimit, MemoryStorage, throttle_rate

storage = MemoryStorage()
app.config.REQUEST_LIMITERS = [
    IPRateLimit(limit=100, window=60, storage=storage),
]


@app.middleware("request")
async def throttle_middleware(request):
    if not await throttle_rate(request):
        return json({"error": "请求过于频繁"}, status=429)
```

## 使用注意

- `MemoryStorage` 不跨进程共享，多 worker 部署请使用 `RedisStorage`。
- 用户级限流依赖 `request.ctx.user`，认证中间件需先执行。
- 当前实现不生成 `Retry-After` 等响应头；白名单、指标等需应用自行扩展。

## 下一步

- 阅读[认证中间件](auth-middleware.md)确认中间件顺序。
- 阅读[健康检查](../health-check.md)配置监控端点。
