# API Reference

This document provides a detailed reference for the SRF core API.

## Views

### BaseViewSet

Base class for all ViewSets.

```python
from srf.views import BaseViewSet
from pydantic import BaseModel

class GenericAPIView(BaseViewSet):
    """Base class for ViewSet"""

    # Common configurations for subclasses
    schema: BaseModel = None         # pydantic model
    permission_classes = ()          # check_permissions treats as empty list when not declared
    search_fields = []               # search fields, read by SearchFilter
    filter_fields = {}               # field mapping for filtering, read by FilterClass
    ordering_fields = {}             # field mapping for ordering, read by OrderingFactory
    queryset = None                  # 设置 QuerySet / property，或重写 get_queryset()

    def get_schema(self, request, *args, is_safe=False, **kwargs):
        """Returns self.schema by default; can be customized based on request method"""
        return getattr(self, "schema", None)

    def get_queryset(self):
        """Return a per-request QuerySet from self.queryset (clones with .all() when needed)."""
        ...

    def filter_queryset(self, queryset):
        """Apply filter_class backends to queryset (used by list())."""
        ...

    async def check_permissions(self, request):
        """Call has_permission on each permissions (optional); raise Forbidden if denied"""
        ...

    async def check_object_permissions(self, request, obj):
        """Call has_object_permission on each entry; raise Forbidden if denied"""
        ...

    async def get_object(self, request, id: int):
        """Lookup via get_queryset(), then check_object_permissions()"""
        ...
```

### Mixins

#### CreateModelMixin

```python
class CreateModelMixin:
    """Create mixin"""

    async def create(self, request, *args, **kwargs):
        """Handle POST requests; call perform_create(sch_model)"""
        ...

    async def perform_create(self, sch_model):
        """Perform creation (can be overridden)"""
        ...
```

#### RetrieveModelMixin

```python
class RetrieveModelMixin:
    """Retrieve mixin"""

    async def retrieve(self, request, pk, *args, **kwargs):
        """Handle GET /resource/<pk> requests"""
        ...
```

#### UpdateModelMixin

```python
class UpdateModelMixin:
    """Update mixin"""

    async def update(self, request, pk, *args, **kwargs):
        """Handle PUT/PATCH requests"""
        ...

    async def perform_update(self, sch_model, orm_model):
        """Perform update (can be overridden)"""
        ...
```

#### DestroyModelMixin

```python
class DestroyModelMixin:
    """Destroy mixin"""

    async def destroy(self, request, pk, *args, **kwargs):
        """Handle DELETE requests; call perform_destroy(orm_model)"""
        ...

    async def perform_destroy(self, orm_model):
        """Perform deletion (can be overridden)"""
        ...
```

#### ListModelMixin

```python
class ListModelMixin:
    """List mixin"""

    async def list(self, request, *args, **kwargs):
        """Handle GET /resource requests"""
        ...
```

### Decorators

#### @action

```python
from srf.views.decorators import action

@action(
    *,
    detail: bool = False,                 # detail-level action (needs pk)
    methods: Sequence[str] = ("GET",),    # HTTP methods
    url_path: str | None = None,          # default: "/<method name>"
    url_name: str | None = None,          # route name (default: method name)
)
```

**Example**:

```python
@action(methods=["get"], detail=False, url_path="featured")
async def featured(self, request):
    """Collection-level action"""
    pass

@action(methods=["post"], detail=True, url_path="publish")
async def publish(self, request, pk):
    """Detail-level action"""
    pass
```

## Routing

### SanicRouter

```python
from srf.route import SanicRouter

class SanicRouter:
    """Router manager"""
    
    def __init__(self, bp: Blueprint = None, prefix: str = ""):
        """Initialize the router
        
        Args:
            bp: Sanic Blueprint instance
            prefix: URL prefix
        """
        pass
    
    def register(self, path: str, view_cls, name: str = None):
        """Register ViewSet
        
        Args:
            path: URL path
            view_cls: ViewSet class
            name: route name prefix
        """
        pass
    
    def get_blueprint(self) -> Blueprint:
        """Get Blueprint"""
        pass
```

**Example**:

```python
router = SanicRouter(prefix="api")
router.register("products", ProductViewSet, name="products")
app.blueprint(router.get_blueprint())
```

## Permissions

### BasePermission

```python
from srf.permission.permission import BasePermission

class BasePermission:
    """Base class for permissions"""

    @staticmethod
    def has_permission(request, view=None) -> bool:
        """View-level permission check"""
        return True

    @staticmethod
    def has_object_permission(request, view=None, obj=None) -> bool:
        """Object-level permission check"""
        return True
```

### Built-in Permission Classes

```python
from srf.permission.permission import (
    AllowAny,             # Always allow (default in DEFAULT_PERMISSION_CLASSES)
    IsAuthenticated,      # Requires login
    IsRoleAdminUser,      # Requires admin role
    IsSafeMethodOnly      # Allows only safe methods
)
```

## Pagination

### BasePagination

```python
from srf.paginator import BasePagination

class BasePagination:
    """DRF-style base. Subclass and implement methods that raise NotImplementedError."""

    @classmethod
    def from_queryset(cls, queryset, request):
        raise NotImplementedError

    async def paginate(self, sch_model=None):
        raise NotImplementedError

    async def to_dict(self, sch_model=None):
        """Default: await paginate() then model_dump."""
        ...

    def num_pages(self, total_count=None):
        raise NotImplementedError
```

### PageNumberPagination

```python
from srf.paginator import PageNumberPagination

class PageNumberPagination(BasePagination):
    """Paginator."""

    MAX_PAGE_SIZE: int = 100
    PAGE_QUERY_PARAM: str = 'page'
    PAGE_SIZE_QUERY_PARAM: str = 'page_size'
    # Default to 10 if page_size is missing or invalid (fallback from_queryset)

    @classmethod
    def from_queryset(cls, queryset, request):
        """Create paginator from query set"""
        pass

    async def paginate(self, sch_model):
        """Execute pagination"""
        pass

    async def to_dict(self, sch_model):
        """Return dictionary format"""
        pass
```

## Filtering

### BaseFilter

```python
from srf.filters.filter import BaseFilter

class BaseFilter:
    """Base filter class"""

    def __init__(self, view_class):
        self.view_class = view_class

    def filter_queryset(self, request, queryset):
        """Filter query set"""
        raise NotImplementedError
```

### Built-in Filters

```python
from srf.filters.filter import (
    SearchFilter,        # Search filter
    JsonLogicFilter,     # JSON Logic filter
    QueryParamFilter,    # Query parameter filter
    OrderingFactory      # Ordering filter
)
```

## Authentication

### JWT Functions

```python
from srf.auth.auth import authenticate, retrieve_user, store_user

async def authenticate(request, *args, **kwargs):
    """Validate user credentials, return JWT payload"""
    pass

async def retrieve_user(payload, *args, **kwargs):
    """Get user object from JWT payload"""
    pass

async def store_user(request, user_id, *args, **kwargs):
    """Store user in request context"""
    pass
```

### setup_auth

```python
from srf.auth.viewset import setup_auth

setup_auth(
    app,
    secret=app.config.JWT_SECRET,  # Required; missing will throw ServerError
    url_prefix="/api/auth",        # Default /api/auth
    login_path="login",            # Path passed to sanic-jwt for authentication
    # Other keyword arguments for sanic-jwt Initialize...
)
```

## Middleware

### Authentication Middleware

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx

@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)
```

### Rate Limiting Middleware

```python
from srf.middleware.throttlemiddleware import (
    MemoryStorage,
    IPRateLimit,
    UserRateLimit,
    PathRateLimit,
    HeaderRateLimit,
    throttle_rate
)

storage = MemoryStorage()

app.config.REQUEST_LIMITERS = [
    IPRateLimit(100, 60, storage),
    UserRateLimit(1000, 60, storage),
]


@app.middleware("request")
async def throttle_middleware(request):
    if not await throttle_rate(request):
        return json({"error": "Too many requests"}, status=429)
```

## Health Checks

### BaseHealthCheck

```python
from srf.health.base import BaseHealthCheck

class BaseHealthCheck:
    """Base health check class"""

    name: str = "base"
    timeout: int = 5  # seconds; built-in checks use asyncio.timeout(self.timeout)

    def __init__(self, app):
        self.app = app
        client = getattr(app.ctx, self.name, None)
        if client is None:
            raise ValueError(f"{self.name} not found in app.ctx")
        setattr(self, self.name, client)

    async def check(self):
        """Execute check; raises exception on failure"""
        raise NotImplementedError

    async def run(self):
        """Run check and return (name, status)"""
        ...
```

### Built-in Health Checks

```python
from srf.health.checks import (
    RedisCheck,       # Redis check (requires app.ctx.redis)
    SQLiteCheck,      # SQLite check (requires app.ctx.sqlite)
)

# Route reads app.config.HEALTH_CHECK_LIST
app.config.HEALTH_CHECK_LIST = [RedisCheck, SQLiteCheck]
```

## Exceptions

### Custom Exceptions

```python
from srf.exceptions import (
    TargetObjectAlreadyExist,  # Object already exists (409)
    ImproperlyConfigured       # Configuration error (500)
)
```

## HTTP Status Codes

### HTTPStatus

```python
from srf.views.http_status import (
    HTTPStatus,
    is_informational,
    is_success,
    is_redirect,
    is_client_error,
    is_server_error,
)

# Status code constants
HTTPStatus.HTTP_200_OK
HTTPStatus.HTTP_201_CREATED
HTTPStatus.HTTP_204_NO_CONTENT
HTTPStatus.HTTP_400_BAD_REQUEST
HTTPStatus.HTTP_401_UNAUTHORIZED
HTTPStatus.HTTP_403_FORBIDDEN
HTTPStatus.HTTP_404_NOT_FOUND
HTTPStatus.HTTP_422_UNPROCESSABLE_ENTITY
HTTPStatus.HTTP_429_TOO_MANY_REQUESTS
HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR

# Helper functions (module-level functions, not methods of HTTPStatus)
is_informational(code)  # 1xx
is_success(code)        # 2xx
is_redirect(code)       # 3xx
is_client_error(code)   # 4xx
is_server_error(code)   # 5xx
```

## Configuration

### LazySettings (`settings`)

```python
from srf.config import settings

# Bind Sanic app.config (optional; request path takes precedence)
settings.set_app(app)

# Common configurations (uppercase items come from srf.config.settings, can be overridden by app.config)
settings.JWT_ACCESS_TOKEN_EXPIRES
settings.NON_AUTH_ENDPOINTS
settings.DEFAULT_FILTERS
settings.DEFAULT_PERMISSION_CLASSES
settings.EMAIL_CODE_REDIS      # Default "EMAIL_CODE"
settings.REQUEST_LIMITERS      # Default []
settings.HEALTH_CHECK_LIST     # Default []
settings.SOCIAL_CONFIG

# JWT_SECRET must be set by application in app.config, no module-level default
app.config.JWT_SECRET = "..."

# srfconfig is a deprecated alias (issues DeprecationWarning on first use)
# from srf.config import srfconfig
```

## Utility Functions

### Email Sending

```python
from srf.tools.email import send_email

await send_email(
    to_email: str,        # Recipient
    subject: str = "",    # Subject
    content: str = "",    # Content
)
```

## Type Hints

```python
from sanic import Request
from tortoise.queryset import QuerySet
from pydantic import BaseModel
from typing import Type, List, Dict, Optional

class MyViewSet(BaseViewSet):
    @property
    def queryset(self) -> QuerySet:
        return Product.all()
    
    def get_schema(self, request: Request, is_safe: bool = False) -> Type[BaseModel]:
        is_read = request.method.upper() in ("GET", "HEAD", "OPTIONS")
        return ProductSchemaReader if is_read or is_safe else ProductSchemaWriter
    
    async def list(self, request: Request) -> JSONResponse:
        pass
```

## Full Example

```python
from sanic import Sanic
from sanic.response import json
from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.sanic import register_tortoise
from pydantic import BaseModel, Field
from sanic.constants import SAFE_HTTP_METHODS
from typing import Optional

from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.views.http_status import HTTPStatus
from srf.route import SanicRouter
from srf.permission.permission import IsAuthenticated
from srf.config import settings

# Model
class Product(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    stock = fields.IntField(default=0)

# Schema
class ProductSchemaWriter(BaseModel):
    name: str = Field(..., max_length=200)
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)

class ProductSchemaReader(BaseModel):
    id: int
    name: str
    price: float
    stock: int
    
    class Config:
        from_attributes = True

# ViewSet
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    search_fields = ["name"]
    filter_fields = {"min_price": "price__gte"}
    ordering_fields = {"price": "price"}
    
    @property
    def queryset(self):
        return Product.all()
    
    def get_schema(self, request, is_safe=False):
        if request.method.upper() in SAFE_HTTP_METHODS or is_safe:
            return ProductSchemaReader
        return ProductSchemaWriter
    
    @action(detail=False, methods=["get"], url_path="featured")
    async def featured(self, request):
        products = await Product.filter(stock__gt=0).limit(10)
        schema = self.get_schema(request, is_safe=True)
        data = [schema.model_validate(p).model_dump() for p in products]
        return json({"results": data}, status=HTTPStatus.HTTP_200_OK)

# Application
app = Sanic("MyApp")
app.config.JWT_SECRET = "change-me"
settings.set_app(app)

# Database
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["__main__"]},
    generate_schemas=True,
)

# Routing
router = SanicRouter(prefix="api")
router.register("products", ProductViewSet)
app.blueprint(router.get_blueprint())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

## Next Steps

- See [Getting Started](usage/getting-started.md) to create your first project
- Read [Core Concepts](usage/core/viewsets.md) to understand features in depth
- Browse [Configuration Options](config.md) to learn about configuration parameters