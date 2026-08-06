# Configuration

SRF uses `srf.config.settings` (a `LazySettings`) to read configuration. The lookup order is:

1. `app.config` bound most recently through `settings.set_app(app)`
2. Uppercase default values in the `srf.config.settings` module

## Initialization

`SECRET_KEY` / `JWT_SECRET` are **no longer** required when importing SRF. When enabling JWT authentication, set it in Sanic configuration and pass it to `setup_auth(..., secret=...)`:

```python
from sanic import Sanic
from srf.config import settings

app = Sanic("MyApp")
app.config.JWT_SECRET = "Read from a secure environment variable"
app.config.NON_AUTH_ENDPOINTS = ("login", "health")
settings.set_app(app)
```

`LazySettings` is a process-level singleton. When multiple apps share a process, the latter `set_app()` will affect all code reading configuration through `settings`.

## Default Configuration

### Core & JWT

| Name | Default Value | Current Usage |
|---|---|---|
| `JWT_SECRET` | None (must be set by app) | JWT signing, authentication middleware, OAuth state fallback key |
| `JWT_ACCESS_TOKEN_EXPIRES` | `timedelta(hours=24)` | Only defined; `setup_auth()` currently does not automatically read |

To control the expiration settings of `sanic-jwt`, directly pass the parameters supported by the library to `setup_auth()`, do not assume `JWT_ACCESS_TOKEN_EXPIRES` will take effect automatically.

### Authentication Exemptions

`NON_AUTH_ENDPOINTS` is a set of **last segments** of URLs:

```python
NON_AUTH_ENDPOINTS = (
    "register",
    "login",
    "send-verification-email",
    "health",
    ...
)
```

It does not support full paths or prefix rules. For example, `"products"` will match both `/api/products` and `/admin/products`.

### Filters

```python
from srf.filters.filter import (
    JsonLogicFilter,
    OrderingFactory,
    QueryParamFilter,
    SearchFilter,
)

DEFAULT_FILTERS = [
    SearchFilter,
    JsonLogicFilter,
    QueryParamFilter,
    OrderingFactory,
]
```

Each `GenericAPIView` / `BaseViewSet` instance initializes with `settings.DEFAULT_FILTERS` if no `filter_class` is declared on the class.

### Pagination

`PAGINATION_CLASS = PageNumberPagination` is defined, but the built-in `list()` currently does not read it, instead directly using `PageNumberPagination`. There is currently no global `PAGE_SIZE` or `MAX_PAGE_SIZE` configuration; the default values are in the pagination class.

### Rate Limiting

```python
REQUEST_LIMITERS = []  # No rate limiting by default; list of limiter instances set by app
```

`throttle_rate()` reads `app.config.REQUEST_LIMITERS` (treated as `[]` if missing).

### Health Check

`HEALTH_CHECK_LIST` defaults to an empty list. The health check route actually reads `app.config.HEALTH_CHECK_LIST`:

```python
from srf.health.checks import RedisCheck

app.config.HEALTH_CHECK_LIST = [RedisCheck]
app.ctx.redis = redis_client
```

### JSON Encoding

`DATETIME_FORMAT` defaults to `"%Y-%m-%d %H:%M:%S"`.
`JSON_ENCODER` points to `custom_dumps()`, which can serialize `datetime` and exception objects.
Whether to use this encoder depends on how the app integrates with Sanic configuration; SRF will not automatically install it.

### Email

`srf.tools.email.send_email()` directly reads `srf.config.settings.EmailConfig`:

| Attribute | Environment Variable |
|---|---|
| `from_email` | `FROM_EMAIL` |
| `smtp_server` | `SMTP_SERVER` |
| `smtp_port` | `SMTP_PORT` |
| `password` | `PASSWORD` |

These values are read when the module is imported; subsequent modifications to `app.config` will not change the email configuration.
Port judgment uses `int(smtp_port) == 465` to choose SSL.

### GitHub OAuth

```python
SOCIAL_CONFIG = {
    "github": {
        "CLIENT_ID": ...,
        "CLIENT_SECRET": ...,
        "REDIRECT_URI": ...,
        ...
    }
}

```

The default values come from corresponding uppercase environment variables. You can override them entirely via `app.config.SOCIAL_CONFIG` before binding the app.

## Full Example

```python
import os

from sanic import Sanic
from srf.config import srfconfig

app = Sanic("MyApp")
app.config.update(
    {
        "JWT_SECRET": os.environ["SECRET_KEY"],
        "NON_AUTH_ENDPOINTS": ("login", "register", "health"),
        "HEALTH_CHECK_LIST": [],
    }
)
settings.set_app(app)
```

## Best Practices

1. **Separate sensitive information**: Use environment variables for keys and passwords
2. **Multi-environment configuration**: Create different configurations for development, testing, and production environments
3. **Use .env files**: Convenient for local development
4. **Do not commit .env**: Add `.env` to `.gitignore`
5. **Provide default values**: Provide default values using the second parameter of `os.getenv()`
6. **Validate configuration**: Verify required configuration items (e.g., `JWT_SECRET`) when the application starts
7. **Document configuration**: Explain all configuration items in README

## Next Steps

- Read [Authentication](usage/core/authentication.md) configuration for JWT.
- Read [Project Setup](usage/project-setup.md) to view the complete application structure.