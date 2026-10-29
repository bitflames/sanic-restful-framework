# 限流

SRF 在 `srf.middleware.throttlemiddleware` 中提供限流组件，由应用按需接入。

## 组件声明

- **限流器**：`IPRateLimit`、`UserRateLimit`、`PathRateLimit`、`HeaderRateLimit`，均继承 `BaseRateLimit(limit, window, storage, scope=None)`；`limit` / `window` 必须是正整数。自定义限流器只需实现 `get_key(request)`。
- **存储**：`MemoryStorage`（单进程滑动窗口，仅适合开发）和 `RedisStorage`（多进程可用的固定窗口）。两者的 `allow()` 都是原子的；被拒绝的请求不会增加计数。
- **键维度**：`PathRateLimit` 的键包含用户或 IP；`HeaderRateLimit` 会哈希 header 值，缺失该 header 时回退到 IP。不同 `limit` / `window` 的限流器使用不同的键，不会互相污染。
- **执行入口**：`throttle_rate(request)` 按顺序调用 `app.config.REQUEST_LIMITERS` 中每个限流器的 `allow(request)`，任一返回假即拒绝；未配置时视为不限流。被拒绝时 `request.ctx.throttle_retry_after` 是建议的 `Retry-After` 秒数。

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
        return json(
            {"error": "请求过于频繁"},
            status=429,
            headers={"Retry-After": str(request.ctx.throttle_retry_after)},
        )
```

## 使用注意

- `MemoryStorage` 不跨进程共享，多 worker 部署请使用 `RedisStorage`。
- 用户级限流依赖 `request.ctx.user`，**认证中间件必须先于限流中间件执行**。按下面的顺序注册：

  ```python
  @app.middleware("request")
  async def auth_middleware(request):
      await set_user_to_request_ctx(request, strict=False)

  @app.middleware("request")
  async def throttle_middleware(request):
      if not await throttle_rate(request):
          return json({"error": "请求过于频繁"}, status=429)
  ```

  如果顺序反过来，`UserRateLimit` 会把所有请求都当成匿名请求，退化成按 IP 限流。

- IP 来源：配置了 Sanic 的 `PROXIES_COUNT` / `REAL_IP_HEADER` 时使用 `request.remote_addr`（真实客户端 IP）；否则使用 socket 对端 `request.ip`。SRF 没有额外代理配置。
- 白名单、指标等需应用自行扩展。

## 下一步

- 阅读[认证中间件](auth-middleware.md)确认中间件顺序。
- 阅读[健康检查](../health-check.md)配置监控端点。
