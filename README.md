#  Sanic RESTful Framework (SRF)

A RESTful API framework based on [Sanic](https://sanic.dev/), providing a Django REST Framework-like development experience to help you quickly build high-performance Web APIs.

- **GitHub**: https://github.com/bitflames/sanic-restful-framework
- **PyPI**: https://pypi.org/project/sanic-restful-framework/
- **Documentation**: https://sanic-restful-framework.bitflames.com/

## Features

- 🚀 **Base ViewSets** - Complete CRUD operations (Create, Retrieve, Update, Destroy, List).
- 🔒 **Pydantic Integration** - Data validation and serialization using Pydantic.
- 🔍 **Powerful Filtering System** - Support for search, JSON logic filtering, query parameter filtering, and ordering.
- 📄 **Pagination** - Built-in pagination handler with customizable pagination parameters.
- 🛡️ **Authentication & Permissions** - JWT-based authentication system with permission control, and provides third-party authentication integration, such as GitHub login.
- ⚡ **Asynchronous ORM** - Built-in support for asynchronous database queries using Tortoise ORM, and more.
- 💓 **Health Checks** - Built-in health check routes supporting multiple service checks.
- 🎯 **Auto Route Registration** - Intelligent route registration with support for custom actions.
- 🔄 **Rate Limiting** - Built-in rate limiting middleware to control request rates.

## Requirements

- Python >= 3.11
- Sanic >= 25.0.0
- Tortoise ORM >= 1.1.8
- Pydantic >= 2.6.1

## Installation

### Install from Source

```bash
# Recommended installation method
pip install sanic-restful-framework

# Install production dependencies
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

## Quick Start

To get started with SRF, follow these steps:

1. **Define your models** using Tortoise ORM. Create your database models that inherit from `tortoise.models.Model` and define the necessary fields.

2. **Create Pydantic schemas** for data validation and serialization. Define separate schemas for reading (output) and writing (input) operations.

3. **Create a ViewSet** by inheriting from `BaseViewSet`. Configure the model, search fields, and filter fields. Implement the `queryset` property to return your model's queryset, and optionally override `get_schema()` to return different schemas based on the current action.

4. **Register routes** using `SanicRouter`. Create a router instance with an optional prefix, register your ViewSet with a path, and add the router's blueprint to your Sanic application.

5. **Run your application** using Sanic's built-in server or your preferred ASGI server.

## Core Features

### ViewSets

`BaseViewSet` provides standard CRUD operations:

- `list()` - GET /resource - Retrieve a list of resources
- `create()` - POST /resource - Create a new resource
- `retrieve()` - GET /resource/<id> - Retrieve a single resource
- `update()` - PUT/PATCH /resource/<id> - Update a resource
- `destroy()` - DELETE /resource/<id> - Delete a resource

```python
from srf.views import BaseViewSet
from tortoise.queryset import QuerySet
from .models import Project
from .schema import ProjectSchemaReader

class ProjectViewSet(BaseViewSet):
    def get_schema(self):
        return ProjectSchemaReader

    @property
    def queryset(self) -> QuerySet:
        return Project.all()
```

Congrats! At this point, you have completed a basic CRUD (Create, Read, Update, Delete) interface, just like in Django REST Framework.

### Custom Actions

Use the `@action` decorator to define custom actions:

```python
from srf.views import action
from sanic.response import JSONResponse

class ProjectViewSet(BaseViewSet):
    @action(detail=False, url_path="featured", methods=["get"])
    async def list_featured(self, request):
        projects = self.queryset.filter(is_featured=True)
        schema = self.get_schema()
        data = [schema.model_validate(p, from_attributes=True).model_dump(by_alias=True) for p in await projects]
        return JSONResponse(data)

    @action(detail=True, url_path="archive", methods=["post"])
    async def archive(self, request, pk):
        project = await self.get_object(pk)
        project.is_archived = True
        await project.save()
        return JSONResponse({"status": "archived"})
```

### Filters

The framework includes multiple built-in filters:

#### 1. Search Filter (SearchFilter)

```python
# GET /projects?search=api
# Searches for "api" in fields specified by search_fields
```

#### 2. JSON Logic Filter (JsonLogicFilter)

```python
# GET /projects?filter={"and":[{"==":[{"var":"is_active"},true]},{"like":[{"var":"name"},"api"]}]}
```

#### 3. Query Parameter Filter (QueryParamFilter)

```python
# GET /projects?name=myproject&is_active=true
```

#### 4. Ordering Filter (OrderingFactory)

```python
# GET /projects?ordering=name,-created_date
# Orders by name ascending, created_date descending
```

### Pagination

Pagination automatically reads `page` and `page_size` from query parameters:

```python
# GET /projects?page=1&page_size=20
```

Response format:

```json
{
  "count": 100,
  "next": true,
  "previous": false,
  "results": [...]
}
```

### Authentication & Permissions

#### Authentication Middleware

The framework provides JWT authentication middleware:

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx

app.middleware("request")(set_user_to_request_ctx)
```

#### Permission Classes

```python
from srf.permission.permission import IsAuthenticated, SafeMethodOnly, SuperuserOnly

class ProjectViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)  # Requires authentication
    # or
    permission_classes = (SuperuserOnly,)  # Requires a superuser
    # or read-only: allow GET/HEAD/OPTIONS only
    permission_classes = (SafeMethodOnly,)
```

### Health Checks

The framework provides a health check view that runs a configurable list of checks:

```python
from srf.health.checks import RedisCheck, SQLiteCheck
from srf.health.viewset import health_check

app.config.HEALTH_CHECK_LIST = [RedisCheck, SQLiteCheck]  # required
app.add_route(health_check, "/health", methods=["GET"])
```

Each check is a class that is instantiated with the Sanic `app` and exposes the required clients — e.g. the Redis check uses `app.ctx.redis` and the SQLite check uses `app.ctx.sqlite`. Attach those clients to `app.ctx` before startup. Access `GET /health` to check the status of the registered services.

## Configuration

SRF reads configuration from `srf.config.settings` via `settings` (uppercase keys such as `NON_AUTH_ENDPOINTS`, `DEFAULT_FILTERS`, `EMAIL_CODE_REDIS`). Override via Sanic `app.config` after `settings.set_app(app)` (or pass config when creating the app). `srfconfig` is a deprecated alias.

```python
from srf.config import settings
from srf.config.settings import DEFAULT_FILTERS

app.config.JWT_SECRET = "your-secret-key"  # required for JWT / register_auth_urls
app.config.NON_AUTH_ENDPOINTS = ("/api/auth/register", "/api/auth/login", "/api/auth/refresh")  # full request paths
app.config.DEFAULT_FILTERS = DEFAULT_FILTERS
app.config.EMAIL_CODE_REDIS = "EMAIL_CODE"
app.config.REQUEST_LIMITERS = []
settings.set_app(app)
```

For auth email verification and social login, ensure Redis is on `app.ctx.redis`. Email codes use `EMAIL_CODE_REDIS` (default `"EMAIL_CODE"`). Social one-time codes use `SOCIAL_LOGIN_REDIS_CODE_PREFIX` (default `"social-login"`).

## Dependencies

Main dependencies:

- `sanic>=25.0.0` - Async web framework
- `pydantic>=2.6.1` - Data validation
- `tortoise-orm>=1.1.8` - ORM
- `sanic-jwt>=1.8.0` - JWT authentication

See `pyproject.toml` for the complete dependency list.

## Development

### Install Development Dependencies

Development dependencies (pytest, black, isort, ruff, ...) are optional and are **not** installed by default:

```bash
# Production/runtime dependencies only (default)
uv sync

# Everything needed for local development
uv sync --extra dev
```

Or with pip:

```bash
pip install -e ".[dev]"
```

## License

MIT License

## Author

| Name   | Email                 |
| ------ | --------------------- |
| Chacer | 1364707405c@gmail.com |

## Contributing

Issues and Pull Requests are welcome!

## Want to join? Email us!
