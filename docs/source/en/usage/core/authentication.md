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

Using `register_auth_urls()` is recommended. It calls `setup_auth()` and registers the authentication, registration,
logout, and email verification routes:

```python
from srf.auth.route import register_auth_urls

register_auth_urls(app, prefix="/api/auth")
```

`register_auth_urls()` reads and validates `JWT_SECRET` and `SECRET_KEY` from `app.config`.

Do not call `setup_auth()` and then `register_auth_urls()`, otherwise `sanic-jwt` will be initialized
twice.

If you need to pass other `sanic-jwt` initialization arguments to `setup_auth()`, initialize it directly:

```python
from srf.auth.viewset import setup_auth

jwt = setup_auth(
    app,
    url_prefix="/api/auth",
    # Remaining keyword arguments are passed to sanic_jwt.Initialize
)
```

`setup_auth()` already uses SRF's own `authenticate` and `retrieve_user`; do not pass these two names as keyword arguments, or a duplicate argument error will occur.
`setup_auth()` does not read JWT secrets from keyword arguments; if a valid `app.config.JWT_SECRET` or `app.config.SECRET_KEY` is missing, it raises `ServerError` during initialization.

## Login

The default login endpoint is `POST /api/auth`. The request fields are `account` and `password`; `account` can be an email address or a username:

```bash
# Email login
curl -X POST http://localhost:8000/api/auth \
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
queries `srf.auth.models.User`, checks whether the user is enabled and verifies the password, then puts `user_id`,
`username`, and role names into the JWT payload.

## Password and token algorithms

SRF stores passwords as **bcrypt(SHA-256(password))**: the password is first encoded as UTF-8 and
hashed with SHA-256, then bcrypt generates the password hash using a random salt. Login performs the same
preprocessing and then verifies with `bcrypt.checkpw()`.

## Authentication middleware

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx


@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)
```

When a token is included, the request header format is:

```http
Authorization: Bearer <token>
```

The middleware decodes the token using HS256 and `app.config.JWT_SECRET`, looks up the user through
`retrieve_user()`, and sets `request.ctx.user`. Specific behavior:

- When there is no authentication information, or the token's signature/expiry validation fails, `extract_payload()` returns
  `None`, `request.ctx.user` is set to `None`, and the request continues as an anonymous request. Whether
  to reject it is then decided by permission classes (for example, `IsAuthenticated` returns 403).
- When the `Authorization` header format is invalid (for example, the `Bearer` prefix is missing), JWT is not initialized,
  or the user corresponding to the token does not exist, the middleware raises `Unauthorized` (401).

Therefore, if you need distinct 401 and 403 semantics, do not rely solely on the authentication middleware; handle it uniformly
in permission classes or a global exception handler.

## Getting the current user

```python
from sanic.response import json
from srf.views import BaseViewSet


class ProductViewSet(BaseViewSet):
    async def create(self, request):
        user = self.get_current_user(request)
        if user is None:
            return json({"error": "Not logged in"}, status=401)
        # ...
```

`get_current_user()` returns `request.ctx.user` first, and falls back to
`request.auth` when it does not exist.

## Registration and email verification codes

`register_auth_urls()` registers the following common SRF routes:

- `POST /api/auth/register`
- `POST /api/auth/verify_email`
- `POST /api/auth/logout`

Email verification code settings are defined in `srf.config.settings`:

| Option | Default | Purpose |
| --- | --- | --- |
| `USER_REGISTER_EMAIL_VERIFY_CODE_TTL` | `60` | Verification code lifetime in seconds |
| `USER_REGISTER_EMAIL_CODE` | `USER_REGISTER:EMAIL_CODE:{email}` | Key format for the verification code in Redis; `{email}` is replaced with the email address |
| `USER_REGISTER_EMAIL_CODE_TIMES` | `USER_REGISTER:EMAIL_CODE_TIMES:{email}` | Key format for the number of failed attempts in Redis |
| `USER_REGISTER_EMAIL_CODE_TIMES_LIMIT` | `10` | Maximum allowed failed verification attempts |

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

`register_auth_urls()` only registers authentication flow routes and does not automatically register the user management resource. When you need the user profile and password change APIs, explicitly import `UserViewSet` and register it with `SanicRouter`:

```python
from srf.auth.viewset import UserViewSet
from srf.route import SanicRouter

user_router = SanicRouter(app, prefix="api")
user_router.register("users", UserViewSet, name="users")
```

This resource provides `GET /api/users/self`, `POST /api/users/change-password`, and CRUD routes for `/api/users`. Regular users can only access their own user record; superusers can manage other users. The password change request body is:

```json
{"old_password": "old-password", "password1": "new-password", "password2": "new-password"}
```

After a successful change, the user's saved refresh tokens are revoked; access tokens that have already been issued remain usable until they expire.

### User resource flow

```bash
# 1. Log in to get a token (account supports username or email)
curl -X POST http://localhost:8000/api/auth \
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
