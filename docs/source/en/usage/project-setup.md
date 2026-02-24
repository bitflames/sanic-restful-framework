# Project Setup

This chapter introduces how to properly set up and configure an SRF project, including project structure, configuration management, database setup, etc.

## Recommended Project Structure

Assuming an SRF project structure as follows:

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
├── schemas/                    # Pydantic Schemas
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

## Configuration Management

### Environment Variables

Create a `.env` file to store sensitive information:

```bash
# .env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite://db.sqlite3
REDIS_URL=redis://localhost:6379/0

# JWT Configuration
JWT_SECRET=your-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=86400

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-password

# GitHub OAuth
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

### Configuration File

Create `config.py` to manage configurations:

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
    
    # JWT Configuration
    JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 86400))
    
    # Email Configuration
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    
    # Pagination Configuration
    PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # CORS Configuration
    CORS_ORIGINS = ["http://localhost:3000", "http://localhost:8080"]
    
    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_PER_MINUTE = 60

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

# Choose configuration based on environment variable
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "test": TestConfig,
}

env = os.getenv("ENVIRONMENT", "development")
config = config_map[env]
```

### Application Configuration

Apply the configuration in `app.py`:

```python
from sanic import Sanic
from tortoise.contrib.sanic import register_tortoise
from srf.config import srfconfig
from config import config

app = Sanic("MyApp")

# Apply configuration to Sanic
app.config.update_config(config)

# Configure SRF
srfconfig.set_app(app)

# Configure database
register_tortoise(
    app,
    db_url=config.DATABASE_URL,
    modules={"models": ["models"]},
    generate_schemas=True,
)
```

## Database Setup

### Tortoise ORM Configuration

SRF uses Tortoise ORM as the default ORM framework.

#### Basic Configuration

```python
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
)
```

#### PostgreSQL Configuration

```python
register_tortoise(
    app,
    db_url="postgres://user:password@localhost:5432/dbname",
    modules={"models": ["models"]},
    generate_schemas=True,
)
```

#### MySQL Configuration

```python
register_tortoise(
    app,
    db_url="mysql://user:password@localhost:3306/dbname",
    modules={"models": ["models"]},
    generate_schemas=True,
)
```

#### Advanced Configuration

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
                }
            }
        },
        "apps": {
            "models": {
                "models": ["models", "aerich.models"],
                "default_connection": "default",
            }
        },
        "use_tz": False,
        "timezone": "Asia/Shanghai"
    },
    generate_schemas=True,
)
```

### Database Migrations

Use Aerich for database migrations:

#### Install Aerich

```bash
pip install aerich
```

#### Initialize Aerich

```bash
aerich init -t config.TORTOISE_ORM
```

#### Initialize Database

```bash
aerich init-db
```

#### Create Migration

```bash
aerich migrate --name "add_user_model"
```

#### Apply Migration

```bash
aerich upgrade
```

#### Rollback Migration

```bash
aerich downgrade
```

### Configuration File Example

Create `config.py` for Aerich:

```python
TORTOISE_ORM = {
    "connections": {
        "default": "sqlite://db.sqlite3"
    },
    "apps": {
        "models": {
            "models": ["models", "aerich.models"],
            "default_connection": "default",
        }
    },
}
```

## Authentication Setup

### JWT Configuration

```python
from srf.auth.viewset import setup_auth

# Configure JWT
setup_auth(
    app,
    secret=config.JWT_SECRET,
    expiration_delta=config.JWT_ACCESS_TOKEN_EXPIRES,
    url_prefix="/api/auth",
    class_views=[
        ("/register", register),
        ("/send-verification-email", verify_email),
    ],
    authenticate=authenticate,
    retrieve_user=retrieve_user,
    store_user=store_user,
)
```

### Social Login Configuration

Set up social login in the configuration file:

```python
class Config:
    SOCIAL_CONFIG = {
        "github": {
            "client_id": os.getenv("GITHUB_CLIENT_ID"),
            "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
            "redirect_uri": "http://localhost:8000/api/auth/social/callback",
        }
    }
```

### Public Endpoint Configuration

Configure endpoints that do not require authentication:

```python
class Config:
    NON_AUTH_ENDPOINTS = [
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/send-verification-email",
        "/api/products",  # Public product list
        "/health/",       # Health check
    ]
```

## Middleware Setup

### Authentication Middleware

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx

@app.middleware("request")
async def auth_middleware(request):
    """Authentication middleware"""
    await set_user_to_request_ctx(request)
```

### Rate Limiting Middleware

```python
from srf.middleware.throttlemiddleware import (
    MemoryStorage,
    IPRateLimit,
    UserRateLimit,
    throttle_rate
)

# Create storage
storage = MemoryStorage()

# Configure rate limiting rules
app.config.RequestLimiter = [
    IPRateLimit(100, 60, storage),      # IP: 100 requests per minute
    UserRateLimit(1000, 60, storage),   # User: 1000 requests per minute
]

@app.middleware("request")
async def throttle_middleware(request):
    """Rate limiting middleware"""
    if not await throttle_rate(request):
        from sanic.response import json
        return json({"error": "Too many requests, please try again later"}, status=429)
```

### CORS Middleware

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

## Route Setup

### Basic Route Registration

Create `routes.py`:

```python
from srf.route import SanicRouter
from viewsets.product import ProductViewSet
from viewsets.order import OrderViewSet
from viewsets.category import CategoryViewSet

def register_routes(app):
    """Register all routes"""
    router = SanicRouter(prefix="api")
    
    # Register ViewSets
    router.register("products", ProductViewSet, name="products")
    router.register("orders", OrderViewSet, name="orders")
    router.register("categories", CategoryViewSet, name="categories")
    
    # Add routes to application
    app.blueprint(router.get_blueprint())
```

Call in `app.py`:

```python
from routes import register_routes

app = Sanic("MyApp")
# ... other configurations ...

# Register routes
register_routes(app)
```

### Multi-Version API

```python
from srf.route import SanicRouter

def register_routes(app):
    # v1 API
    router_v1 = SanicRouter(prefix="api/v1")
    router_v1.register("products", ProductViewSetV1)
    app.blueprint(router_v1.get_blueprint())
    
    # v2 API
    router_v2 = SanicRouter(prefix="api/v2")
    router_v2.register("products", ProductViewSetV2)
    app.blueprint(router_v2.get_blueprint())
```

## Health Check Setup

```python
from srf.health.route import bp as health_bp

# Register health check routes
app.blueprint(health_bp)

# Configure health check service
@app.before_server_start
async def setup_health_checks(app, loop):
    """Set up health check dependencies"""
    import aioredis
    
    # Redis client
    app.ctx.redis = await aioredis.create_redis_pool(config.REDIS_URL)
    
    # PostgreSQL connection pool
    # app.ctx.pg = await asyncpg.create_pool(config.DATABASE_URL)
```

## Logging Setup

```python
import logging
from sanic.log import logger

# Configure logging
logging.basicConfig(
    level=logging.INFO if not config.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Use in code
logger.info("Application started")
logger.error("An error occurred", exc_info=True)
```

## Exception Handling

```python
from sanic.exceptions import NotFound, InvalidUsage
from srf.views.http_status import HTTPStatus
from sanic.response import json

@app.exception(NotFound)
async def handle_not_found(request, exception):
    """Handle 404 errors"""
    return json(
        {"error": "Resource not found", "message": str(exception)},
        status=HTTPStatus.HTTP_404_NOT_FOUND
    )

@app.exception(InvalidUsage)
async def handle_invalid_usage(request, exception):
    """Handle 400 errors"""
    return json(
        {"error": "Invalid request", "message": str(exception)},
        status=HTTPStatus.HTTP_400_BAD_REQUEST
    )

@app.exception(Exception)
async def handle_exception(request, exception):
    """Handle uncaught exceptions"""
    logger.error(f"Unhandled exception: {exception}", exc_info=True)
    return json(
        {"error": "Internal server error"},
        status=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR
    )
```

## Full Application Example

`app.py`:

```python
from sanic import Sanic
from sanic_cors import CORS
from tortoise.contrib.sanic import register_tortoise
from srf.config import srfconfig
from srf.middleware.authmiddleware import set_user_to_request_ctx
from srf.health.route import bp as health_bp
from config import config
from routes import register_routes
import logging

# Create application
app = Sanic("MyApp")

# Apply configuration
app.config.update_config(config)
srfconfig.set_app(app)

# Configure CORS
CORS(app, origins=config.CORS_ORIGINS)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Register database
register_tortoise(
    app,
    db_url=config.DATABASE_URL,
    modules={"models": ["models"]},
    generate_schemas=True,
)

# Register middleware
@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)

# Register routes
register_routes(app)
app.blueprint(health_bp)

# Exception handling
@app.exception(Exception)
async def handle_exception(request, exception):
    from sanic.response import json
    logging.error(f"Error: {exception}", exc_info=True)
    return json({"error": str(exception)}, status=500)

if __name__ == "__main__":
    app.run(
        host=config.get("HOST", "0.0.0.0"),
        port=config.get("PORT", 8000),
        debug=config.DEBUG,
        auto_reload=config.DEBUG,
    )
```

## Production Deployment

### Using Gunicorn

```bash
pip install gunicorn
```

```bash
gunicorn app:app \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class sanic.worker.GunicornWorker
```

### Using Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

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

Run:

```bash
docker-compose up -d
```

## Best Practices

1. **Use environment variables**: Never hardcode sensitive information in code
2. **Separate configurations**: Create different configurations for different environments
3. **Use migrations**: Manage database changes through migrations
4. **Logging**: Log important operations and errors
5. **Exception handling**: Handle exceptions globally and return friendly error messages
6. **Health checks**: Provide health check endpoints for monitoring systems
7. **Rate limiting**: Prevent API abuse
8. **CORS configuration**: Correctly configure cross-origin access

## Next Steps

- Learn [Core Concepts](core/viewsets.md) to understand SRF's features
- View [Configuration Options](../config.md) to see all configuration options
- Read [API Reference](../api-reference.md) for detailed API documentation