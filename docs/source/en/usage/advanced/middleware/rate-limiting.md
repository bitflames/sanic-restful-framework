# Rate Limiting

SRF provides in-memory counters within a fixed time window and four types of rate limiting keys.

## Quick Start

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
        return json({"error": "Too many requests"}, status=429)
```

`throttle_rate()` calls `allow(request)` for each limiter in `app.config.REQUEST_LIMITERS` in order; it rejects if any returns false. When not configured, it is considered an empty list (no rate limiting).

## MemoryStorage

`MemoryStorage.incr(key, window)` is a synchronous method. It removes timestamps outside the current window for the key, appends this request, and returns the count within the window.

```python
storage = MemoryStorage()
count = storage.incr("ip:127.0.0.1", window=60)
```

This storage is suitable only for development or single-process deployment:

- Not shared across processes or instances.
- Data is lost after restart.
- Each active key stores all request timestamps within the window.
- Expired keys are not automatically cleaned up globally; you can call `storage.cleanup_expired(window)` periodically.

## Built-in Limiters

### IPRateLimit

```python
IPRateLimit(limit=100, window=60, storage=storage)
```

The key is `ip:<request.remote_addr>`. When deployed behind a reverse proxy, ensure that trusted proxies are properly configured, otherwise the client address may be inaccurate.

### UserRateLimit

```python
UserRateLimit(limit=1000, window=60, storage=storage)
```

For authenticated users, the key is `user:<user.id>`; when `request.ctx.user` is not present, all anonymous requests share `"anonymous"`. To limit by user, the authentication middleware must run first.

### PathRateLimit

```python
PathRateLimit(limit=10, window=60, storage=storage)
```

The key is only `path:<request.path>`. This means all users on the same path share a single bucket, not "a limit per user per path".

### HeaderRateLimit

The constructor parameter name is `header`:

```python
HeaderRateLimit(
    header="X-API-Key",
    limit=500,
    window=60,
    storage=storage,
)
```

The key is `header:<header name>:<value>`. If the request header is missing, all requests share a bucket with value `None`; if the request header is used for identification, missing values should be explicitly rejected.

## Custom Limiter

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

`BaseRateLimit.__init__()` only accepts `limit` and `window`; storage is saved by the subclass.

## Using Redis

The built-in limiters require a storage object that provides a synchronous `incr(key, window) -> int`, so you cannot directly pass an asynchronous Redis client or an object that only provides `add()`/`count()`. For production environments, implement a complete asynchronous limiter and use Lua scripts or transactions to ensure atomicity of "clean up, count, append, expire," rather than just replacing the `storage`.

## Production Considerations

The current implementation does not generate `Retry-After` or `X-RateLimit-*` response headers, nor does it support whitelists, tiered strategies, or metrics. `MemoryStorage` is also not suitable for multiple workers. Before public deployment, add shared storage, proxy IP handling, metrics, and testing according to your actual topology.

## Next Steps

- Read [Authentication Middleware](auth-middleware.md) to confirm middleware order.
- Read [Health Check](../health-check.md) to configure monitoring endpoints.