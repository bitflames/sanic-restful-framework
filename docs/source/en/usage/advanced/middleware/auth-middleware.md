# Authentication Middleware

The authentication middleware reads the JWT from the request and writes the user object from the database into
`request.ctx.user`. When there is no authentication information, `request.ctx.user` is set to `None` and the request continues;
permission classes can use this to distinguish anonymous users from authenticated users.

## Configuration

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx


@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)
```

The application must provide the same secret used to issue tokens:

```python
app.config.JWT_SECRET = "read from a secure environment variable"
```

## Request flow

1. Extract the JWT payload from `request.app.ctx.auth`.
2. When there is no payload, set `request.ctx.user` to `None` and continue processing the request.
3. When there is a payload, call `retrieve_user(request, payload)` to load the user and put the ORM user into
   `request.ctx.user`.

When the `Authorization` header format is invalid, JWT is not initialized, or the user corresponding to the token does not exist, it returns 401;
when the token is missing or the signature/expiry check fails, the payload is `None` and the request continues as an anonymous request
(`request.ctx.user` is `None`), with the permission classes deciding whether to reject it.

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

await authenticate_request(request)
user = request.ctx.user
```

### set_user_to_request_ctx

This function calls `authenticate_request(request)` and can be used directly as application middleware. When there is no authentication information,
`request.ctx.user` is `None`; when a valid token is present, it is the corresponding ORM user.

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
