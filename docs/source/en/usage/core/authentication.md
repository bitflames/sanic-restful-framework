# Authentication

SRF provides login and Token generation through `sanic-jwt`, and provides an independent request middleware to verify Bearer Token, load the user, and write it to `request.ctx.user`.

## Prerequisites

Before enabling JWT, set `JWT_SECRET` in Sanic configuration (no longer requiring the `SECRET_KEY` environment variable to be set before import):

```python
from sanic import Sanic
from srf.config import settings

app = Sanic("MyApp")
app.config.JWT_SECRET = "Read from a secure environment variable"
settings.set_app(app)
```

## Register Authentication Routes

It is recommended to use `register_auth_urls()`. It calls `setup_auth()` and registers routes for registration, logout, verification email, and GitHub login:

```python
from srf.auth.route import register_auth_urls

register_auth_urls(app, prefix="/api/auth")
```

`register_auth_urls()` internally uses `secret=app.config.JWT_SECRET`, so ensure it's set.

Do not call `setup_auth()` before `register_auth_urls()`, otherwise it will cause duplicate initialization of `sanic-jwt`.

If only the `sanic-jwt` login endpoint is needed, you can initialize directly:

```python
from srf.auth.viewset import setup_auth

jwt = setup_auth(
    app,
    secret=app.config.JWT_SECRET,
    url_prefix="/api/auth",
    login_path="login",
    # Other keyword arguments are passed to sanic_jwt.Initialize
)
app.config.update({"JWT": jwt})
```

`setup_auth()` has fixed usage of SRF's own `authenticate` and `retrieve_user`, do not pass these names as keyword arguments again, otherwise it will cause duplicate parameter errors. If `secret` is missing, it throws `ServerError("secret is required")`.

## Login

The default login endpoint is `POST /api/auth/login`. It supports email or username:

```bash
# Email login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

`authenticate()` uses `UserLoginSchema` (at least one of `email` or `username`), queries `srf.auth.models.User`, checks if the user is active and verifies the password, then puts `user_id`, `username`, and role name into the JWT payload.

## Authentication Middleware

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx


@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)
```

Protected requests must carry:

```http
Authorization: Bearer <token>
```

The middleware decodes the Token using HS256 and `app.config.JWT_SECRET`, queries the user via `retrieve_user()`, and sets `request.ctx.user`. It returns 401 if the Token is missing, malformed, expired, invalid, or the user does not exist.

## Public Endpoints

`NON_AUTH_ENDPOINTS` stores the last segment of the path, not the full URL:

```python
app.config.NON_AUTH_ENDPOINTS = (
    "login",
    "register",
    "send-verification-email",
    "health",
    ...
)
```

For example, `"products"` will exempt both `/api/products` and `/admin/products`. It does not support prefix matching, nor can it distinguish HTTP methods. For applications with high security requirements, it is recommended to modify the middleware to use explicit `(method, path)` rules.

## Get Current User

```python
class ProductViewSet(BaseViewSet):
    async def create(self, request):
        user = self.get_current_user(request)
        if user is None:
            return json({"error": "Not logged in"}, status=401)
        # ...
```

`get_current_user()` first returns `request.ctx.user`, and if it does not exist, tries `request.auth`.

## Registration and Email Verification

`register_auth_urls()` registers the following endpoints:

- `POST /api/auth/register`
- `POST /api/auth/send-verification-email`
- `POST /api/auth/logout`
- `GET /api/auth/social/github/login`
- `GET /api/auth/social/callback`
- `GET /api/auth/social/github/login_by_code`

Registration and verification email rely on:

- `request.app.ctx.redis`
- `settings.EMAIL_CODE_REDIS` (or `app.config.EMAIL_CODE_REDIS`), default is `"EMAIL_CODE"`; Redis key format is `EMAIL_CODE_{email}`
- Environment variables `FROM_EMAIL`, `SMTP_SERVER`, `SMTP_PORT`, `PASSWORD`

The underlying function signature for sending emails is:

```python
from srf.tools.email import send_email

ok = await send_email(
    to_email="user@example.com",
    subject="Verification Code",
    content="Your verification code is: 12345",
)
```

Currently, `send_email()` internally uses synchronous `smtplib`, although the function is declared as asynchronous, the sending process will block the event loop; in production environments, it should be executed in a thread executor or asynchronous task queue.

## Security Considerations

- HTTPS must be used in production environments, and `JWT_SECRET` must be read from a key management system.
- The default code does not have token refresh or real logout/revocation mechanisms.
- GitHub OAuth uses random `state` and HMAC-signed cookies with timestamps to prevent tampering, and constant-time comparison is also performed during callback.