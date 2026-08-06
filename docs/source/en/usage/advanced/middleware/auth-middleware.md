# Authentication Middleware

The authentication middleware verifies JWT and writes the user object from the database into `request.ctx.user`.

## Configuration

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx


@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)
```

The application must provide the same key used to issue the Token:

```python
app.config.JWT_SECRET = "read from a secure environment variable"
```

## Request Flow

1. Take the last segment of the URL and check if it is in `app.config.NON_AUTH_ENDPOINTS`.
2. Public endpoints are allowed directly without setting `request.ctx.user`.
3. Non-public endpoints require `Authorization: Bearer <token>`.
4. Decode the Token using HS256 and `app.config.JWT_SECRET`.
5. Call `srf.auth.auth.retrieve_user(payload)` to query the user.
6. Set `request.ctx.user`.

Token missing, format error, expired, invalid, or user not found will throw `Unauthorized` (HTTP 401), no anonymous access is allowed.

## Core Functions

### is_public_endpoint

```python
def is_public_endpoint(request):
    tail = request.path.rstrip("/").rpartition("/")[2]
    return tail in getattr(request.app.config, "NON_AUTH_ENDPOINTS", [])
```

The configuration value is the last segment of the path:

```python
app.config.NON_AUTH_ENDPOINTS = (
    "login",
    "register",
    "send-verification-email",
    "health",
)
```

Do not write `"/api/auth/login"` or `"/api/public/"`; the current implementation does not perform full path matching or prefix matching. The same tail segment will be exempted, for example, `"products"` will match `/products` under multiple different prefixes.

### extract_bearer_token

```python
from srf.middleware.authmiddleware import extract_bearer_token

token = extract_bearer_token(request)
```

This function requires the authentication scheme to be Bearer (case-insensitive) and raises 401 when the header is missing or malformed, rather than returning `None`.

### authenticate_request

```python
from srf.middleware.authmiddleware import authenticate_request

await authenticate_request(request)
user = request.ctx.user
```

This function does not check public endpoints; it is usually called through `set_user_to_request_ctx()`.

## Middleware Order

If logic such as user rate limiting or access logging needs to read `request.ctx.user`, ensure the authentication middleware runs first. Public endpoints do not create `ctx.user`, so use:

```python
user = getattr(request.ctx, "user", None)
```

## Security Restrictions

- Only HS256 is allowed, cannot switch algorithms through configuration.
- Each protected request queries the database.
- No token blacklist, revocation, or refresh mechanism.
- Public rules only look at the path tail, with coarse granularity.

Production applications can rewrite the middleware to use explicit `(HTTP method, full path)` whitelists, configurable algorithms, token revocation, and appropriate user caching.

## Next Steps

- Read [Authentication](../../core/authentication.md) to configure token issuance.
- Read [Permissions](../../core/permissions.md) to control user access.
- Read [Rate Limiting](rate-limiting.md) to protect authentication endpoints.