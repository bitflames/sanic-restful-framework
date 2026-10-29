# Authentication

SRF provides login and token generation through `sanic-jwt`, and provides a separate request middleware that
validates the Bearer token, loads the user, and writes it to `request.ctx.user`.

## Prerequisites

Before enabling JWT, set `JWT_SECRET` in the Sanic configuration (there is no longer a requirement to set the
`SECRET_KEY` environment variable before import):

```python
from sanic import Sanic
from srf.config import settings

app = Sanic("MyApp")
app.config.JWT_SECRET = "read from a secure environment variable"
app.config.SECRET_KEY = "read from another secure environment variable"
settings.set_app(app)
```

`JWT_SECRET` is used for JWT signing; `SECRET_KEY` is used to compute the HMAC digest of refresh tokens, and the database stores only the digest, never the raw token.
Set both to different strong random secrets. Plaintext refresh tokens already in the database before an upgrade, as well as old tokens after changing `SECRET_KEY`, will fail validation, so users need to log in again.

## Registering authentication routes

Using `register_all_auth_urls()` is recommended: it initializes JWT and registers the login,
registration, logout, email verification, and GitHub social login routes in one call:

```python
from srf.auth.route import register_all_auth_urls

register_all_auth_urls(app, prefix="/api/auth")
```

JWT initialization reads and validates `JWT_SECRET` and `SECRET_KEY` from `app.config`, raising
`ServerError` when either is missing.

If you only need a subset, compose the three fine-grained functions:

| Function                                      | Registered endpoints                                                                                 |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `register_jwt_urls(app, prefix)`              | `POST {prefix}/login`, `GET {prefix}/me`, `GET {prefix}/verify`, `POST {prefix}/refresh` (sanic-jwt) |
| `register_auth_urls(instance, prefix)`        | `POST {prefix}/register`, `POST {prefix}/verify_email`, `POST {prefix}/logout`                       |
| `register_social_auth_urls(instance, prefix)` | The three GitHub OAuth endpoints                                                                     |

Notes:

- `register_jwt_urls()` only accepts a Sanic app instance. Initializing sanic-jwt on a Blueprint
  would attach `ctx.auth` to the blueprint, while the auth middleware reads `request.app.ctx.auth`
  and therefore would not find it.
- None of these functions forward keyword arguments to `sanic_jwt.Initialize`. To customize
  sanic-jwt behavior (for example `leeway` or `claim_iss`), call `sanic_jwt.Initialize` directly.

## Login

The default login endpoint is `POST /api/auth/login`. The request fields are `account` and `password`; `account` can be an email address or a username:

```bash
# Email login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"account":"user@example.com","password":"password123"}'
```

Response (returned by `sanic-jwt`):

```json
{
  "access_token": "******",
  "refresh_token": "******"
}
```

`authenticate()` uses `UserLoginSchema` (`account`, `password`),
queries `srf.auth.models.User`, checks whether the user is enabled and verifies the password. sanic-jwt's
`build_payload()` only puts `user_id` into the access token (plus `exp`); `username` and role names are
returned by `retrieve_user()` on `/me` or refresh, and are never written into the token.

## Refreshing tokens

After the access token expires, exchange it for a new one by presenting the access token (expired is
fine) together with the refresh token:

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh-token>"}'
```

The response contains only the new `access_token`; sanic-jwt does not rotate refresh tokens. Refresh
tokens are persisted as HMAC digests with an absolute lifetime of `JWT_REFRESH_TOKEN_EXPIRES`
(30 days by default); after expiry or logout the user must log in again.

Two other sanic-jwt endpoints: `GET /api/auth/me` returns the current user (`{"me": {...}}`), and
`GET /api/auth/verify` checks token validity. Both are protected: a missing or invalid
`Authorization: Bearer` header returns 401.

## Password and token algorithms

SRF stores passwords as **bcrypt(SHA-256(password))**: the password is first encoded as UTF-8 and
hashed with SHA-256, then bcrypt generates the password hash using a random salt. Login performs the same
preprocessing and then verifies with `bcrypt.checkpw()`.

## Authentication middleware

SRF ships a separate request middleware, `set_user_to_request_ctx`: it validates the
`Authorization: Bearer` token and writes the user into `request.ctx.user`. By default
(`strict=False`) authentication is optional — a request with no token falls back to
`AnonymousUser`, while a presented-but-invalid token returns 401; `strict=True` enforces
mandatory authentication. For the configuration example, whitelist filtering, and request
flow, see [Authentication Middleware](../advanced/middleware/auth-middleware.md).

This cleanly separates the semantics: 401 (authentication failure) comes from the middleware,
403 (authorization failure) from permission classes such as `IsAuthenticated`.

## Getting the current user

```python
from sanic.response import json
from srf.views import BaseViewSet


class ProductViewSet(BaseViewSet):
    async def create(self, request):
        user = self.get_current_user(request)
        if user is None or getattr(user, "is_anonymous", False):
            return json({"error": "Not logged in"}, status=401)
        # ...
```

`get_current_user()` returns `request.ctx.user` first, and falls back to
`request.auth` when it does not exist.

## Registration and email verification codes

`register_all_auth_urls()` registers the following authentication routes (besides the four sanic-jwt JWT endpoints):

- `POST /api/auth/register`
- `POST /api/auth/verify_email`
- `POST /api/auth/logout`

`register` issues tokens on success, so the application must already have called `register_jwt_urls()` (or `register_all_auth_urls()`). When JWT is not configured, the endpoint returns 500 and does not consume the verification code.

After `USER_REGISTER_EMAIL_CODE_TIMES_LIMIT` failed attempts the code is deleted and the endpoint returns 429 (`TooManyRequest`); the client must request a new verification code.

Email verification code settings are defined in `srf.config.settings`:

| Option                                 | Default                                  | Purpose                                                                                     |
| -------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------- |
| `USER_REGISTER_EMAIL_VERIFY_CODE_TTL`  | `60`                                     | Verification code lifetime in seconds                                                       |
| `USER_REGISTER_EMAIL_CODE`             | `USER_REGISTER:EMAIL_CODE:{email}`       | Key format for the verification code in Redis; `{email}` is replaced with the email address |
| `USER_REGISTER_EMAIL_CODE_TIMES`       | `USER_REGISTER:EMAIL_CODE_TIMES:{email}` | Key format for the number of failed attempts in Redis                                       |
| `USER_REGISTER_EMAIL_CODE_TIMES_LIMIT` | `10`                                     | Maximum allowed failed verification attempts                                                |

### Registration flow

```bash
# 1. Send the email verification code (repeated requests within the validity period return 429)
curl -X POST http://localhost:8000/api/auth/verify_email \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'

# 2. Read the 6-digit verification code from the email and submit the registration
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","username":"zhangsan","password1":"Passw0rd123","password2":"Passw0rd123","confirmations":"123456"}'

# 3. Successful registration returns access_token / refresh_token; then access with the token
curl http://localhost:8000/api/users/self \
  -H "Authorization: Bearer <access-token>"

# 4. Log out (revoke the current user's refresh token)
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer <access-token>"
```

## Registering the user resource API

`register_all_auth_urls()` only registers authentication flow routes and does not automatically register the user management resource. When you need the user profile and password change APIs, explicitly import `UserViewSet` and register it with `SanicRouter`:

```python
from srf.auth.viewset import UserViewSet
from srf.route import SanicRouter

user_router = SanicRouter(app, prefix="api")
user_router.register("users", UserViewSet, name="users")
```

This resource provides `GET /api/users/self`, `POST /api/users/change-password`, `POST /api/users/<user-id>/reset-password` (superuser only), and the `/api/users` CRUD routes. Regular users can only access their own user record; superusers can manage other users. The password change request body is:

```json
{
  "old_password": "old-password",
  "password1": "new-password",
  "password2": "new-password"
}
```

After a successful change, the user's saved refresh tokens are revoked; access tokens that have already been issued remain usable until they expire.

For the update endpoints (`PUT/PATCH /api/users/<user-id>`), submitting `email`, `password`, `password1`, or `password2` returns 400. Changing the email address is not supported through this endpoint; password changes go only through the two dedicated endpoints: `change-password` for self-service (verifies the old password) and `reset-password` for superuser resets.

### User resource flow

```bash
# 1. Log in to get a token (account supports username or email)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"account":"user@example.com","password":"Passw0rd123"}'

# 2. Query your own profile
curl http://localhost:8000/api/users/self \
  -H "Authorization: Bearer <access-token>"

# 3. Update your own profile
curl -X PATCH http://localhost:8000/api/users/<user-id> \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"username":"new-name"}'

# 4. Change the password (log in again after success)
curl -X POST http://localhost:8000/api/users/change-password \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"old_password":"Passw0rd123","password1":"NewPassw0rd456","password2":"NewPassw0rd456"}'
```

## Security notes

- Production environments must use HTTPS and read `JWT_SECRET` from a secret management system.
- SRF enables refresh token persistence; logout revokes the current user's refresh token, but access tokens that have already been issued remain valid until they expire.
- GitHub OAuth is an optional authentication feature; see the [Social Login tutorial](social-login.md) for configuration and integration.
