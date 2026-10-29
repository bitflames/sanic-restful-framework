# Authentication Middleware

The authentication middleware reads the JWT from the request and writes the user object from the database into
`request.ctx.user`. `authenticate_request()` supports two modes:

- **`strict=False` (default, optional authentication)**: a request with **no credentials at all**
  (no `Authorization` header) resolves to `request.ctx.user = AnonymousUser()` (see
  `srf.auth.models.AnonymousUser`). A _presented_ token that is malformed, invalid, expired, forged,
  or whose user no longer exists still raises 401 — once the client attempts authentication, the
  attempt must succeed.
- **`strict=True` (mandatory authentication)**: every request must carry a valid, non-expired access
  token; anything else (including requests with no credentials at all) raises 401.

Public endpoints (login, register, refresh, health checks, ...) can alternatively be filtered out by
the caller BEFORE the function runs (whitelist), so they skip authentication entirely.

## Configuration

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx


@app.middleware("request")
async def auth_middleware(request):
    # Filter the whitelist first: public endpoints skip authentication entirely
    if request.path == "/health" or request.path.startswith("/api/auth/"):
        request.ctx.user = None
        return
    await set_user_to_request_ctx(request, strict=True)  # mandatory authentication
```

The application must provide the same secret used to issue tokens:

```python
app.config.JWT_SECRET = "read from a secure environment variable"
```

## Request flow

1. Extract the token from `Authorization: Bearer <token>`. A missing header: `strict=True` raises
   401, otherwise the request falls back to `request.ctx.user = AnonymousUser()`. A malformed header
   always raises 401.
2. Verify the signature and expiry via `request.app.ctx.auth`; an expired, forged, or undecodable
   token raises 401 (in both modes).
3. Call `retrieve_user(request, payload)` to load the user and put the ORM user into
   `request.ctx.user`; a missing or disabled user raises 401.

Note: whitelisted paths skip authentication entirely — even with a valid token, `request.ctx.user`
stays `None`.

## Core functions

### extract_bearer_token

```python
from srf.middleware.authmiddleware import extract_bearer_token

token = extract_bearer_token(request)
```

This function requires the authentication scheme to be Bearer (case-insensitive), and raises 401 when the request header is missing or malformed.

### authenticate_request

```python
from srf.middleware.authmiddleware import authenticate_request

await authenticate_request(request)               # optional auth (default): no token -> AnonymousUser
await authenticate_request(request, strict=True)  # mandatory auth: no token -> 401
user = request.ctx.user
```

### set_user_to_request_ctx

This function passes its arguments through to `authenticate_request` and can be used as application
middleware. `strict=False` (default) is optional authentication: no credentials fall back to
`AnonymousUser`; `strict=True` is mandatory authentication. A presented-but-invalid token always
raises 401 in both modes (see [authenticate_request](#authenticaterequest)).

## Middleware order

If user rate limiting, access logging, or similar logic needs to read `request.ctx.user`, make sure the authentication middleware runs
first. The authentication context may not have been set yet, so read it with:

```python
user = getattr(request.ctx, "user", None)
```

## Security limitations

- Every request with a valid token queries the database.
- The authentication middleware itself does not implement a token blacklist; refresh tokens are managed by the authentication routes.

Production applications can configure token revocation and appropriate user caching as needed.

## Next steps

- Read [Authentication](../../core/authentication.md) to configure token issuance.
- Read [Permissions](../../core/permissions.md) to control the scope of user access.
- Read [Rate Limiting](rate-limiting.md) to protect authentication endpoints.
