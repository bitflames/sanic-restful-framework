# Project Setup

This chapter explains how to properly set up and configure an SRF project, including project structure, configuration management, database setup, and more.

## Recommended project structure

Assume an SRF project is structured as follows:

```
myproject/
├── app.py                      # Application entry point
├── config.py                   # Configuration file
├── requirements.txt            # Dependency list
├── .env                        # Environment variables
├── models/                     # Data models
│   ├── __init__.py
│   ├── product.py
│   ├── order.py
│   └── category.py
├── schemas/                    # Pydantic schemas
│   ├── __init__.py
│   ├── product.py
│   ├── order.py
│   └── category.py
├── viewsets/                   # ViewSets
│   ├── __init__.py
│   ├── product.py
│   ├── order.py
│   └── category.py
├── routes.py                   # Route configuration
├── permissions.py              # Custom permission classes
├── filters.py                  # Custom filters
├── middleware.py               # Custom middleware
├── utils/                      # Utility functions
│   ├── __init__.py
│   ├── helpers.py
│   └── validators.py
└── tests/                      # Tests
    ├── __init__.py
    ├── test_products.py
    └── test_orders.py
```

## Configuration management

### Environment variables

Create a `.env` file to store sensitive information:

```bash
# .env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite://db.sqlite3
REDIS_URL=redis://localhost:6379/0

# JWT configuration
JWT_SECRET=your-jwt-secret
# Access/refresh token lifetimes are defined as timedelta in srf.config.settings and are not read from environment variables

# Email configuration (the names actually read by srf.tools.email)
FROM_EMAIL=your-email@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
PASSWORD=your-password

```

### Configuration file

Create `config.py` to manage configuration:

```python
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://db.sqlite3")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # JWT configuration
    JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
    # JWT_ACCESS_TOKEN_EXPIRES is defined as a timedelta in srf.config.settings;
    # register_jwt_urls converts it to seconds and passes it to sanic-jwt

    # Email: send_email reads settings.EMAIL_CONFIG; app.config.EMAIL_CONFIG can override it.
    # Defaults come from the FROM_EMAIL/SMTP_SERVER/SMTP_PORT/PASSWORD environment variables.

    # Social login (uppercase key names, consistent with SOCIAL_CONFIG)
    SOCIAL_CONFIG = {
        "github": {...}
    }

    # CORS configuration
    CORS_ORIGINS = ["http://localhost:3000", "http://localhost:8080"]

class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    DATABASE_URL = "sqlite://db_dev.sqlite3"

class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    DATABASE_URL = os.getenv("DATABASE_URL")

class TestConfig(Config):
    """Test environment configuration"""
    TESTING = True
    DATABASE_URL = "sqlite://:memory:"

# Select configuration based on the environment variable
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "test": TestConfig,
}

env = os.getenv("ENVIRONMENT", "development")
config = config_map[env]
```

`python-dotenv` is not a dependency of SRF; install it separately if you want to load configuration from a `.env` file:

```bash
pip install python-dotenv
```

### Applying configuration

Apply the configuration in `app.py`:

```python
from sanic import Sanic
from tortoise.contrib.sanic import register_tortoise
from srf.config import settings
from config import config

app = Sanic("MyApp")

# Apply configuration to Sanic
app.config.update_config(config)

# Configure SRF
settings.set_app(app)

# Configure the database
register_tortoise(
    app,
    db_url=config.DATABASE_URL,
    modules={"models": ["models"]},
    generate_schemas=True,
)
```

## Database setup

### Tortoise ORM configuration

SRF uses Tortoise ORM 1.1.8 or later as the default ORM framework.

#### Basic configuration

```python
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
)
```

#### PostgreSQL configuration

The PostgreSQL driver must be installed separately: `pip install asyncpg`.

```python
register_tortoise(
    app,
    db_url="postgres://user:password@localhost:5432/dbname",
    modules={"models": ["models"]},
    generate_schemas=True,
)
```

#### MySQL configuration

The MySQL driver must be installed separately: `pip install asyncmy`.

```python
register_tortoise(
    app,
    db_url="mysql://user:password@localhost:3306/dbname",
    modules={"models": ["models"]},
    generate_schemas=True,
)
```

#### Advanced configuration

```python
from tortoise.contrib.sanic import register_tortoise

register_tortoise(
    app,
    config={
        "connections": {
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": "localhost",
                    "port": 5432,
                    "user": "postgres",
                    "password": "password",
                    "database": "mydb",
                    "minsize": 1,
                    "maxsize": 5,
                },
            }
        },
        "apps": {
            "models": {
                "models": ["models"],
                "default_connection": "default",
            }
        },
        "use_tz": False,
        "timezone": "Asia/Shanghai",
    },
    generate_schemas=True,
)
```

### Database migrations

Tortoise ORM 1.1.8 and later include a migration CLI. First define a complete
`TORTOISE_ORM` configuration in `config.py`:

```python
TORTOISE_ORM = {
    "connections": {"default": "sqlite://db.sqlite3"},
    "apps": {
        "models": {
            "models": ["models"],
            "default_connection": "default",
        }
    },
}
```

Use the Tortoise CLI in the project root to initialize the migration directory and manage migrations:

```bash
# Initialize the migration directory for the models app
tortoise -c config.TORTOISE_ORM init models

# Generate a migration after model changes
tortoise -c config.TORTOISE_ORM makemigrations models --name add_products

# Apply migrations
tortoise -c config.TORTOISE_ORM migrate

# Roll back the most recent migration
tortoise -c config.TORTOISE_ORM downgrade
```

`config.TORTOISE_ORM` after `-c` is the dotted path to the Python module and configuration variable;
the model module names and migration app names in the configuration should match the project structure. Small examples in
development can use `generate_schemas=True` to create tables automatically; production environments should manage schema changes through migrations.

## Authentication setup

### JWT and route registration (recommended)

Prefer `register_all_auth_urls`: it initializes JWT (login /me /verify /refresh) and registers
registration, logout, email verification, and social login routes in one call:

```python
from srf.auth.route import register_all_auth_urls

register_all_auth_urls(app, prefix="/api/auth")
```

If you only need a subset, call `register_jwt_urls` (JWT endpoints only; requires a Sanic app
instance), `register_auth_urls` (register/verify_email/logout), or `register_social_auth_urls`
(GitHub OAuth) separately. To customize `sanic-jwt` parameters, call `sanic_jwt.Initialize` directly.

## Middleware setup

### Authentication middleware

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx

app.middleware("request")(set_user_to_request_ctx)
```

By default (`strict=False`) a request with no token falls back to `AnonymousUser`; pass
`strict=True` for mandatory authentication, or filter public endpoints with a whitelist first.
See [Authentication Middleware](advanced/middleware/auth-middleware.md) for details.

### Rate limiting middleware

```python
from srf.middleware.throttlemiddleware import (
    MemoryStorage,
    IPRateLimit,
    UserRateLimit,
    throttle_rate,
)

# Create storage
storage = MemoryStorage()

# Configure rate limiting rules
app.config.REQUEST_LIMITERS = [
    IPRateLimit(100, 60, storage),      # IP: 100 requests/minute
    UserRateLimit(1000, 60, storage),   # User: 1000 requests/minute
]


@app.middleware("request")
async def throttle_middleware(request):
    """Rate limiting middleware"""
    if not await throttle_rate(request):
        from sanic.response import json

        return json({"error": "Too many requests, please try again later"}, status=429)
```

### CORS middleware

`sanic-cors` is an optional dependency and is not installed with SRF. Install it first if you need this integration:

```bash
pip install sanic-cors
```

```python
from sanic_cors import CORS

# Configure CORS
CORS(
    app,
    origins=config.CORS_ORIGINS,
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Range", "X-Content-Range"],
    supports_credentials=True,
)
```

## Routing setup

### Basic route registration

Create `routes.py`:

```python
from srf.route import SanicRouter
from viewsets.product import ProductViewSet
from viewsets.order import OrderViewSet
from viewsets.category import CategoryViewSet


def register_routes(app):
    """Register all routes"""
    router = SanicRouter(app, prefix="api")

    # Register ViewSets
    router.register("products", ProductViewSet, name="products")
    router.register("orders", OrderViewSet, name="orders")
    router.register("categories", CategoryViewSet, name="categories")

```

Call it in `app.py`:

```python
from routes import register_routes

app = Sanic("MyApp")
# ... other configuration ...

# Register routes
register_routes(app)
```

### Multiple API versions

```python
from srf.route import SanicRouter


def register_routes(app):
    # v1 API
    router_v1 = SanicRouter(app, prefix="api/v1")
    router_v1.register("products", ProductViewSetV1)

    # v2 API
    router_v2 = SanicRouter(app, prefix="api/v2")
    router_v2.register("products", ProductViewSetV2)
```

## Health check setup

```python
from srf.health.checks import RedisCheck
from srf.health.route import health_check

# Register the health check route
app.add_route(health_check, "/health", methods=["GET"])
app.config.HEALTH_CHECK_LIST = [RedisCheck]  # Subclasses of BaseHealthCheck can be implemented


# Configure the services used by health checks
@app.before_server_start
async def setup_health_checks(app):
    """Set up the services that health checks depend on"""
    from redis.asyncio import Redis

    # Redis client
    app.ctx.redis = Redis.from_url(config.REDIS_URL)

    # PostgreSQL connection pool
    # app.ctx.pg = await asyncpg.create_pool(config.DATABASE_URL)
```

## Logging setup

```python
import logging
from sanic.log import logger

# Configure logging
logging.basicConfig(
    level=logging.INFO if not config.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)

# Use it in code
logger.info("Application started")
logger.error("An error occurred", exc_info=True)
```

## Exception handling

```python
from sanic.exceptions import NotFound, InvalidUsage
from sanic.log import logger
from srf.views.http_status import HTTPStatus
from sanic.response import json


@app.exception(NotFound)
async def handle_not_found(request, exception):
    """Handle 404 errors"""
    return json({"error": "Resource not found", "message": str(exception)}, status=HTTPStatus.HTTP_404_NOT_FOUND)


@app.exception(InvalidUsage)
async def handle_invalid_usage(request, exception):
    """Handle 400 errors"""
    return json({"error": "Invalid request", "message": str(exception)}, status=HTTPStatus.HTTP_400_BAD_REQUEST)


@app.exception(Exception)
async def handle_exception(request, exception):
    """Handle uncaught exceptions"""
    logger.error(f"Unhandled exception: {exception}", exc_info=True)
    return json({"error": "Internal server error"}, status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR)
```

## Complete application example

`app.py`:

```python
from sanic import Sanic
from sanic_cors import CORS
from tortoise.contrib.sanic import register_tortoise
from srf.auth.route import register_all_auth_urls
from srf.config import settings
from srf.health.route import health_check
from srf.middleware.authmiddleware import set_user_to_request_ctx
from config import config
from routes import register_routes
import logging

# Create the application
app = Sanic("MyApp")

# Apply configuration
app.config.update_config(config)
settings.set_app(app)

# Configure CORS
CORS(app, origins=config.CORS_ORIGINS)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Register the database
register_tortoise(
    app,
    db_url=config.DATABASE_URL,
    modules={"models": ["models"]},
    generate_schemas=True,
)


# Register middleware (optional auth by default: no token -> AnonymousUser,
# strict=True for mandatory authentication)
app.middleware("request")(set_user_to_request_ctx)


# Register routes
register_routes(app)
register_all_auth_urls(app, prefix="/api/auth")
app.add_route(health_check, "/health", methods=["GET"])


# Exception handling
@app.exception(Exception)
async def handle_exception(request, exception):
    from sanic.response import json

    logging.error(f"Error: {exception}", exc_info=True)
    return json({"error": str(exception)}, status=500)


if __name__ == "__main__":
    app.run(
        host=getattr(config, "HOST", "0.0.0.0"),
        port=getattr(config, "PORT", 8000),
        debug=config.DEBUG,
        auto_reload=config.DEBUG,
    )
```

## Production deployment

### Using Sanic's built-in multiprocessing

Sanic 25 no longer provides `sanic.worker.GunicornWorker`; start multiple workers directly with the `sanic` command:

```bash
sanic app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]
```

Create a `docker-compose.yml`:

```yaml
version: "3.8"

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgres://user:pass@db:5432/mydb
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=mydb
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

Run it:

```bash
docker-compose up -d
```

## Best practices

1. **Use environment variables**: do not hard-code sensitive information in code
2. **Separate configuration**: create different configurations for different environments
3. **Use migrations**: manage database changes through migrations
4. **Logging**: log important operations and errors
5. **Exception handling**: handle exceptions globally and return friendly error messages
6. **Health checks**: provide a health check endpoint for monitoring systems
7. **Rate limiting**: protect the API from abuse
8. **CORS configuration**: configure cross-origin access correctly

## Next steps

- Study [Core Concepts](core/viewsets.md) to learn more about SRF's features
- See [Configuration](../config.md) for all configuration options
- Read the [API Reference](../api/views.md) for detailed API documentation
