# Rate Limiting

SRF provides rate limiting components in `srf.middleware.throttlemiddleware`, which the application integrates as needed.

## Component overview

- **Rate limiters**: `IPRateLimit`, `UserRateLimit`, `PathRateLimit`, `HeaderRateLimit`, all inheriting `BaseRateLimit(limit, window, storage, scope=None)`; `limit` / `window` must be positive integers. A custom limiter only needs to implement `get_key(request)`.
- **Storage**: `MemoryStorage` (single-process sliding window, suitable only for development) and `RedisStorage` (fixed window usable across processes). Both implement an atomic `allow()`; rejected requests do not increase the counter.
- **Key dimensions**: `PathRateLimit` includes the user or IP in its key; `HeaderRateLimit` hashes the header value and falls back to the IP when the header is missing. Limiters with different `limit` / `window` use different keys and do not pollute each other.
- **Entry point**: `throttle_rate(request)` calls `allow(request)` on each limiter in `app.config.REQUEST_LIMITERS` in order, and rejects the request as soon as any returns falsy; when nothing is configured, no rate limiting is applied. On rejection, `request.ctx.throttle_retry_after` holds the suggested `Retry-After` value in seconds.

## Integration example

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
            {"error": "Too many requests"},
            status=429,
            headers={"Retry-After": str(request.ctx.throttle_retry_after)},
        )
```

## Usage notes

- `MemoryStorage` is not shared across processes; use `RedisStorage` for multi-worker deployments.
- User-level rate limiting depends on `request.ctx.user`, so the **authentication middleware must run before the throttle middleware**. Register them in this order:

  ```python
  @app.middleware("request")
  async def auth_middleware(request):
      await set_user_to_request_ctx(request, strict=False)

  @app.middleware("request")
  async def throttle_middleware(request):
      if not await throttle_rate(request):
          return json({"error": "Too many requests"}, status=429)
  ```

  In the opposite order, `UserRateLimit` treats every request as anonymous and degrades to IP-based limiting.

- IP source: when Sanic's `PROXIES_COUNT` / `REAL_IP_HEADER` is configured, `request.remote_addr` (the real client IP) is used; otherwise the socket peer `request.ip` is used. SRF adds no extra proxy configuration.
- Allowlists, metrics, and similar features must be extended by the application.

## Next steps

- Read [Authentication Middleware](auth-middleware.md) to confirm middleware order.
- Read [Health Checks](../health-check.md) to configure the monitoring endpoint.
