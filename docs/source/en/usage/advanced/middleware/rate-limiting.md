# Rate Limiting

SRF provides rate limiting components in `srf.middleware.throttlemiddleware`, which the application integrates as needed.

## Component overview

- **Rate limiters**: `IPRateLimit`, `UserRateLimit`, `PathRateLimit`, `HeaderRateLimit`, all inheriting `BaseRateLimit(limit, window, storage)`; a custom limiter only needs to implement `get_key(request)`.
- **Storage**: `MemoryStorage` (single-process sliding window, suitable only for development) and `RedisStorage` (fixed window usable across processes).
- **Entry point**: `throttle_rate(request)` calls `allow(request)` on each limiter in `app.config.REQUEST_LIMITERS` in order, and rejects the request as soon as any returns falsy; when nothing is configured, no rate limiting is applied.

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
        return json({"error": "Too many requests"}, status=429)
```

## Usage notes

- `MemoryStorage` is not shared across processes; use `RedisStorage` for multi-worker deployments.
- User-level rate limiting depends on `request.ctx.user`, so the authentication middleware must run first.
- The current implementation does not generate response headers such as `Retry-After`; allowlists, metrics, and similar features must be extended by the application.

## Next steps

- Read [Authentication Middleware](auth-middleware.md) to confirm middleware order.
- Read [Health Checks](../health-check.md) to configure the monitoring endpoint.
