# Configuration

SRF provides a flexible configuration system that allows you to customize the framework's behavior.

## Configuration System

SRF uses the `SrfConfig` singleton class to manage configurations, with the following priority order:

1. **Application Configuration** (`app.config`): Highest priority
2. **Module Configuration** (`srf.config.settings`): Default configuration

### Setting Configuration

```python
from sanic import Sanic
from srf.config import srfconfig

app = Sanic("MyApp")

# Method 1: Set directly in app.config
app.config.SECRET_KEY = "your-secret-key"
app.config.JWT_SECRET = "your-jwt-secret"

# Method 2: Use a configuration class
class Config:
    SECRET_KEY = "your-secret-key"
    JWT_SECRET = "your-jwt-secret"

app.config.update_config(Config)

# After updating the app using any method, apply the configuration to SRF
srfconfig.set_app(app)
```

## Core Configuration

### SECRET_KEY

**Type**: `str`  
**Required**: Yes  
**Description**: Application key used for encryption and signing

```python
SECRET_KEY = "your-secret-key-keep-it-secret"
```

**Recommended Practices**:
- Read from environment variables
- Use a sufficiently long and random string
- Do not commit to version control

```python
import os
SECRET_KEY = os.getenv("SECRET_KEY")
```

## JWT Configuration

### JWT_SECRET

**Type**: `str`  
**Default Value**: `SECRET_KEY`  
**Description**: JWT Token signing key

```python
JWT_SECRET = "your-jwt-secret"
```

### JWT_ACCESS_TOKEN_EXPIRES

**Type**: `int`  
**Default Value**: `86400` (24 hours)  
**Unit**: seconds  
**Description**: Access Token expiration time

```python
JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
```

## Authentication Configuration

### NON_AUTH_ENDPOINTS

**Type**: `list[str]`  
**Default Value**: `[]`  
**Description**: List of endpoints that do not require authentication

```python
NON_AUTH_ENDPOINTS = [
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/send-verification-email",
    "/api/products",  # Public product list
    "/health/",
]
```

**Matching Rules**:
- Exact match: `/api/auth/login`
- Prefix match: `/api/public/` matches all paths starting with this prefix

## Date and Time Configuration

### DATETIME_FORMAT

**Type**: `str`  
**Default Value**: `"%Y-%m-%d %H:%M:%S"`  
**Description**: Date and time format string

```python
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
```

**Examples**:
- `"%Y-%m-%d"`: `2026-02-07`
- `"%Y-%m-%d %H:%M:%S"`: `2026-02-07 10:30:45`
- `"%Y/%m/%d %H:%M"`: `2026/02/07 10:30`

## Filter Configuration

### DEFAULT_FILTERS

**Type**: `list`  
**Default Value**: `[SearchFilter, JsonLogicFilter, QueryParamFilter, OrderingFactory]`  
**Description**: List of default filter classes to use

```python
from srf.filters.filter import (
    SearchFilter,
    JsonLogicFilter,
    QueryParamFilter,
    OrderingFactory
)

DEFAULT_FILTERS = [
    SearchFilter,
    JsonLogicFilter,
    QueryParamFilter,
    OrderingFactory,
]
```

**Customization**:

```python
from filters import CustomFilter

DEFAULT_FILTERS = [
    SearchFilter,
    QueryParamFilter,
    CustomFilter,  # Add custom filter
]
```

## Social Login Configuration

### SOCIAL_CONFIG

**Type**: `dict`  
**Description**: Social login configuration

```python
SOCIAL_CONFIG = {
    "github": {
        "client_id": "your-github-client-id",
        "client_secret": "your-github-client-secret",
        "redirect_uri": "http://localhost:8000/api/auth/social/callback",
    }
}
```

**Reading from Environment Variables**:

```python
import os

SOCIAL_CONFIG = {
    "github": {
        "client_id": os.getenv("GITHUB_CLIENT_ID"),
        "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/api/auth/social/callback"),
    }
}
```

## Email Configuration

### EmailConfig

**Type**: `class`  
**Description**: Email sending configuration

```python
class EmailConfig:
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USER = "your-email@gmail.com"
    SMTP_PASSWORD = "your-password"
    SMTP_FROM = "your-email@gmail.com"
    SMTP_USE_TLS = True
```

**Reading from Environment Variables**:

```python
import os

class EmailConfig:
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_FROM = os.getenv("SMTP_FROM", os.getenv("SMTP_USER"))
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
```

## Cache Configuration

### CACHES

**Type**: `dict`  
**Description**: Cache configuration

```python
CACHES = {
    "default": {
        "backend": "redis",
        "location": "redis://localhost:6379/0",
    }
}
```

**Redis Configuration**:

```python
CACHES = {
    "default": {
        "backend": "redis",
        "location": "redis://localhost:6379/0",
        "options": {
            "maxsize": 10,
            "minsize": 1,
        }
    }
}
```

## Full Configuration Example

### config.py

```python
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    # Core configuration
    SECRET_KEY = os.getenv("SECRET_KEY")
    DEBUG = False
    
    # JWT configuration
    JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 86400))  # Access token expiration time (seconds)
    
    # Database configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://db.sqlite3")
    
    # Redis configuration
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Authentication configuration
    NON_AUTH_ENDPOINTS = [
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/send-verification-email",
        "/api/auth/social/",
        "/api/public/",
        "/health/",
    ]
    
    # Datetime format
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # Filter configuration
    from srf.filters.filter import (
        SearchFilter,
        JsonLogicFilter,
        QueryParamFilter,
        OrderingFactory
    )
    DEFAULT_FILTERS = [
        SearchFilter,
        JsonLogicFilter,
        QueryParamFilter,
        OrderingFactory,
    ]
    
    # Social login configuration
    SOCIAL_CONFIG = {
        "github": {
            "client_id": os.getenv("GITHUB_CLIENT_ID"),
            "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
            "redirect_uri": os.getenv(
                "GITHUB_REDIRECT_URI",
                "http://localhost:8000/api/auth/social/callback"
            ),
        }
    }
    
    # Email configuration
    class EmailConfig:
        SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
        SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
        SMTP_USER = os.getenv("SMTP_USER")
        SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
        SMTP_FROM = os.getenv("SMTP_FROM", os.getenv("SMTP_USER"))
        SMTP_USE_TLS = True
    
    # Cache configuration
    CACHES = {
        "default": {
            "backend": "redis",
            "location": REDIS_URL,
        }
    }
    
    # Pagination configuration
    PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # CORS configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    
    # Rate limiting configuration
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

# Choose configuration based on environment
env = os.getenv("ENVIRONMENT", "development")
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "test": TestConfig,
}
config = config_map[env]
```

### .env

```bash
# Core configuration
SECRET_KEY=your-secret-key-keep-it-secret
ENVIRONMENT=development

# JWT configuration
JWT_SECRET=your-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=86400

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# GitHub OAuth
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_REDIRECT_URI=http://localhost:8000/api/auth/social/callback

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

### app.py

```python
from sanic import Sanic
from srf.config import srfconfig
from config import config

app = Sanic("MyApp")

# Apply configuration
app.config.update_config(config)
srfconfig.set_app(app)

# Access configuration
print(f"Environment: {config.__name__}")
print(f"Debug: {app.config.DEBUG}")
print(f"Database: {app.config.DATABASE_URL}")
```

## Accessing Configuration

### Accessing in Code

```python
from srf.config import srfconfig

# Access configuration values
secret_key = srfconfig.SECRET_KEY
jwt_secret = srfconfig.JWT_SECRET
non_auth_endpoints = srfconfig.NON_AUTH_ENDPOINTS
```

### Accessing in ViewSet

```python
from srf.views import BaseViewSet
from srf.config import srfconfig

class ProductViewSet(BaseViewSet):
    def __init__(self):
        super().__init__()
        # Access configuration
        self.page_size = getattr(srfconfig, 'PAGE_SIZE', 20)
```

## Environment Variables

It is recommended to use environment variables to manage sensitive configurations:

### Using python-dotenv

```bash
pip install python-dotenv
```

```python
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Read environment variables
SECRET_KEY = os.getenv("SECRET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://db.sqlite3")
```

### Docker Environment Variables

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
```

## Best Practices

1. **Separate sensitive information**: Use environment variables to store keys and passwords.
2. **Multiple environment configurations**: Create different configurations for development, testing, and production environments.
3. **Use .env files**: Makes local development easier.
4. **Do not commit .env**: Add `.env` to `.gitignore`.
5. **Provide default values**: Use the second parameter of `os.getenv()` to provide default values.
6. **Validate configurations**: Validate required configuration items when the application starts.
7. **Document configurations**: Explain all configuration items in the README.

## Configuration Validation

```python
class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.SECRET_KEY:
            raise ValueError("SECRET_KEY is required")
        
        if len(cls.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")

# Validate configuration on application startup
@app.before_server_start
async def validate_config(app, loop):
    Config.validate()
```

## Next Steps

- View [Project Setup](usage/project-setup.md) for complete project configuration
- Read [Authentication](usage/core/authentication.md) for authentication configuration
- Browse [API Reference](api-reference.md) for configuration API