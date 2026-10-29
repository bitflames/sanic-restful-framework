# Configuration

SRF reads configuration through `srf.config.settings` (`LazySettings`). The lookup order is:

1. The `app.config` most recently bound via `settings.set_app(app)`
2. The uppercase defaults defined in the `srf.config.settings` module

## Initialization

Set this up in your Sanic configuration:

```python
from sanic import Sanic
from srf.config import settings

app = Sanic("MyApp")
settings.set_app(app)
```

`LazySettings` is a process-level singleton. When multiple applications share a single process, a later
`set_app()` call affects all code that reads configuration through `settings`.

## Default configuration

The following options are defined in `srf/config/settings.py`; the source code is authoritative.

### Pagination / Filtering / Permissions

Defaults used when a ViewSet does not declare the corresponding class attributes.

| Option                       | Default                                                  | Description                |
| ---------------------------- | -------------------------------------------------------- | -------------------------- |
| `PAGINATION_CLASS`           | `PageNumberPagination`                                   | Default pagination class   |
| `DEFAULT_FILTERS`            | `[SearchFilter, QueryParamFilter, OrderingFactory, ...]` | Default filter chain       |
| `DEFAULT_PERMISSION_CLASSES` | `(AllowAny,)`                                            | Default permission classes |

### Serialization and caching

| Option            | Default               | Description                                                                                                 |
| ----------------- | --------------------- | ----------------------------------------------------------------------------------------------------------- |
| `BASE_DIR`        | `os.getcwd()`         | Project root directory (process working directory)                                                          |
| `CACHE_ROOT`      | `BASE_DIR/.diskcache` | Cache directory                                                                                             |
| `DATETIME_FORMAT` | `"%Y-%m-%d %H:%M:%S"` | Datetime string template                                                                                    |
| `JSON_ENCODER`    | `custom_dumps`        | JSON serialization function (handles `datetime` / `Exception`); must be wired into Sanic by the application |

### Health checks and rate limiting

The health check route actually reads `app.config.HEALTH_CHECK_LIST`:

```python
from srf.health.checks import RedisCheck

app.config.HEALTH_CHECK_LIST = [RedisCheck]
app.ctx.redis = redis_client
```

| Option                  | Default      | Description                                                                                                               |
| ----------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------- |
| `HEALTH_CHECK_LIST`     | `[]`         | List of health check classes                                                                                              |
| `REQUEST_LIMITERS`      | `[]`         | List of rate limiters; `throttle_rate()` reads `app.config.REQUEST_LIMITERS`, falling back to `settings.REQUEST_LIMITERS` |
| `THROTTLE_REDIS_PREFIX` | `"throttle"` | Redis key prefix for rate limiting (`RedisStorage`)                                                                       |

### Email

`srf.tools.email.send_email()` reads `settings.EMAIL_CONFIG`. `LazySettings` prefers
`app.config.EMAIL_CONFIG`, so the application can override it at startup; when it is not
overridden, `srf.config.settings.EMAIL_CONFIG` is used and its attributes are read from
environment variables at module import time.

| Attribute                  | Environment variable | Description                         |
| -------------------------- | -------------------- | ----------------------------------- |
| `EMAIL_CONFIG.from_email`  | `FROM_EMAIL`         | Sender address                      |
| `EMAIL_CONFIG.smtp_server` | `SMTP_SERVER`        | SMTP server                         |
| `EMAIL_CONFIG.smtp_port`   | `SMTP_PORT`          | SMTP port                           |
| `EMAIL_CONFIG.password`    | `PASSWORD`           | Email password / authorization code |

### Social login

See [Social Login](usage/core/social-login.md) for a GitHub OAuth tutorial.

| Option                            | Default                         | Description                                                           |
| --------------------------------- | ------------------------------- | --------------------------------------------------------------------- |
| `SOCIAL_CONFIG`                   | GitHub OAuth configuration dict | Fields are read from environment variables such as `GITHUB_CLIENT_ID` |
| `SOCIAL_LOGIN_COOKIE_KEY`         | `"oauth_state"`                 | Cookie name for the OAuth state                                       |
| `SOCIAL_LOGIN_COOKIE_KEY_MAX_AGE` | `600`                           | State cookie lifetime (seconds)                                       |

### Registration verification codes and passwords

| Option                                 | Default                                    | Description                               |
| -------------------------------------- | ------------------------------------------ | ----------------------------------------- |
| `MIN_PASSWORD_LENGTH`                  | `8`                                        | Minimum password length                   |
| `USER_REGISTER_EMAIL_VERIFY_CODE_TTL`  | `60`                                       | Verification code lifetime (seconds)      |
| `USER_REGISTER_EMAIL_CODE`             | `"USER_REGISTER:EMAIL_CODE:{email}"`       | Redis key template for verification codes |
| `USER_REGISTER_EMAIL_CODE_TIMES`       | `"USER_REGISTER:EMAIL_CODE_TIMES:{email}"` | Redis key template for failure counts     |
| `USER_REGISTER_EMAIL_CODE_TIMES_LIMIT` | `10`                                       | Maximum number of verification failures   |

### JWT

`JWT_SECRET` (signing key) and `SECRET_KEY` (refresh token digest key) have no defaults and must be
set explicitly in `app.config`. `register_jwt_urls()` converts `JWT_ACCESS_TOKEN_EXPIRES` to seconds
and passes it to `sanic-jwt`.

| Option                      | Default               | Description            |
| --------------------------- | --------------------- | ---------------------- |
| `JWT_ACCESS_TOKEN_EXPIRES`  | `timedelta(hours=24)` | Access token lifetime  |
| `JWT_REFRESH_TOKEN_EXPIRES` | `timedelta(days=30)`  | Refresh token lifetime |

## Best practices

1. **Separate sensitive information**: use environment variables for secrets and passwords
2. **Multi-environment configuration**: create different configurations for development, testing, and production
3. **Use a .env file**: convenient for local development
4. **Do not commit .env**: add `.env` to `.gitignore`
5. **Provide defaults**: use the second argument of `os.getenv()` for default values
6. **Validate configuration**: validate required options (such as `JWT_SECRET`) at application startup
7. **Document configuration**: describe all options in the README

## Next steps

- Read [Authentication](usage/core/authentication.md) to configure JWT.
- Read [Project Setup](usage/project-setup.md) for a complete application structure.
