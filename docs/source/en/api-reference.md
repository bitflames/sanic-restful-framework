# API Reference

This document provides detailed reference for SRF core APIs.

## Views

### BaseViewSet

Base class for all ViewSets.

```python
from srf.views import BaseViewSet
from pydantic import BaseModel

class BaseViewSet(HTTPMethodView, ModelMixin):
    """Base class for ViewSet"""

    # Configuration attributes
    schema: BaseModel = None
    permission_classes = ()          # List of permission classes
    search_fields = []               # Search fields
    filter_fields = {}               # Filter field mappings
    ordering_fields = {}             # Ordering field mappings
    filter_class = []                # List of filter classes

    # Core attributes
    @property
    def queryset(self):
        """Return query set (must be implemented)"""
        raise NotImplementedError

    # Core methods
    def get_schema(self, request, is_safe=False):
        """Return Schema (optional) """
        raise NotImplementedError

    async def check_permissions(self, request):
        """Check view-level permissions (optional)"""
        pass

    async def check_object_permissions(self, request, obj):
        """Check object-level permissions (optional)"""
        pass

    async def get_object(self, request, id: int):
        """Get object and check permissions (optional)"""
        pass
```

### Mixins

#### CreateModelMixin

```python
class CreateModelMixin:
    """Create mixin"""

    async def create(self, request):
        """Handle POST requests"""
        pass

    async def perform_create(self, request, schema):
        """Perform creation (can be overridden)"""
        pass
```

#### RetrieveModelMixin

```python
class RetrieveModelMixin:
    """Retrieve mixin"""

    async def retrieve(self, request, pk):
        """Handle GET /resource/<pk> requests"""
        pass
```

#### UpdateModelMixin

```python
class UpdateModelMixin:
    """Update mixin"""

    async def update(self, request, pk):
        """Handle PUT/PATCH requests"""
        pass

    async def perform_update(self, request, obj, schema):
        """Perform update (can be overridden)"""
        pass
```

#### DestroyModelMixin

```python
class DestroyModelMixin:
    """Destroy mixin"""

    async def destroy(self, request, pk):
        """Handle DELETE requests"""
        pass

    async def perform_destroy(self, request, obj):
        """Perform deletion (can be overridden)"""
        pass
```

#### ListModelMixin

```python
class ListModelMixin:
    """List mixin"""

    async def list(self, request):
        """Handle GET /resource requests"""
        pass
```

### Decorators

#### @action

```python
from srf.views.decorators import action

@action(
    methods: list = ["get"],     # List of HTTP methods
    detail: bool = False,        # Whether it's a detail-level action
    url_path: str = None,        # URL path
    url_name: str = None         # Route name
)
```

**Example**:

```python
@action(methods=["get"], detail=False)
async def featured(self, request):
    """Collection-level action"""
    pass

@action(methods=["post"], detail=True)
async def publish(self, request, pk):
    """Detail-level action"""
    pass
```

## Routing

### SanicRouter

```python
from srf.route import SanicRouter

class SanicRouter:
    """Route manager"""

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
            name: Route name prefix
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
    """Base permission class"""

    def has_permission(self, request, view) -> bool:
        """View-level permission check"""
        return True

    def has_object_permission(self, request, view, obj) -> bool:
        """Object-level permission check"""
        return True
```

### Built-in Permission Classes

```python
from srf.permission.permission import (
    IsAuthenticated,      # Requires login
    IsRoleAdminUser,      # Requires admin role
    IsSafeMethodOnly      # Allows only safe methods
)
```

## Pagination

### PaginationHandler

```python
from srf.paginator import PaginationHandler

class PaginationHandler:
    """Pagination handler"""

    page_size = 10                      # Default number per page
    max_page_size = 100                 # Maximum number per page
    page_query_param = 'page'           # Page number parameter name
    page_size_query_param = 'page_size' # Number per page parameter name

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

    async def filter_queryset(self, request, queryset):
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
async def authenticate(request):
    """Validate user credentials and return JWT payload"""
    pass

async def retrieve_user(request, payload, *args, **kwargs):
    """Retrieve user object from JWT payload"""
    pass

async def store_user(request, user_id):
    """Store user in request context"""
    pass
```

### setup_auth

```python
from srf.auth.viewset import setup_auth

setup_auth(
    app,                                # Sanic application
    secret: str,                        # JWT secret
    expiration_delta: int,              # Expiration time (seconds)
    url_prefix: str = "/auth",          # URL prefix
    authenticate: callable,             # Authentication function
    retrieve_user: callable,            # Retrieve user function
    store_user: callable                # Store user function
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

app.config.RequestLimiter = [
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
from srf.health.base import BaseHealthCheck, HealthCheckRegistry

class BaseHealthCheck:
    """Base health check class"""

    name: str = None

    def __init__(self, app):
        self.app = app

    async def check(self) -> bool:
        """Perform check"""
        raise NotImplementedError

    async def run(self):
        """Run check and return result"""
        pass

# Register custom check
HealthCheckRegistry.register(CustomHealthCheck)
```

### Built-in Health Checks

```python
from srf.health.checks import (
    RedisCheck,       # Redis check
    PostgresCheck,    # PostgreSQL check
    MongoCheck,       # MongoDB check
    SQLiteCheck       # SQLite check
)
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
from srf.views.http_status import HTTPStatus

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

# Helper functions
HTTPStatus.is_informational(code)  # 1xx
HTTPStatus.is_success(code)        # 2xx
HTTPStatus.is_redirect(code)       # 3xx
HTTPStatus.is_client_error(code)   # 4xx
HTTPStatus.is_server_error(code)   # 5xx
```

## Configuration

### SrfConfig

```python
from srf.config import srfconfig

# Set application configuration
srfconfig.set_app(app)

# Access any configuration of the application
srfconfig.SECRET_KEY
srfconfig.JWT_SECRET
srfconfig.JWT_ACCESS_TOKEN_EXPIRES
srfconfig.NON_AUTH_ENDPOINTS
srfconfig.DEFAULT_FILTERS
```

## Utility Functions

### Email Sending

```python
from srf.tools.email import send_email

await send_email(
    to: str,              # Recipient
    subject: str,         # Subject
    content: str,         # Content
    is_html: bool = False # Whether it's HTML
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
        return ProductSchemaReader if is_safe else ProductSchemaWriter

    async def list(self, request: Request) -> json:
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
from typing import Optional

from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.views.http_status import HTTPStatus
from srf.route import SanicRouter
from srf.permission.permission import IsAuthenticated
from srf.config import srfconfig

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
        return ProductSchemaReader if is_safe else ProductSchemaWriter

    @action(methods=["get"], detail=False)
    async def featured(self, request):
        products = await Product.filter(stock__gt=0).limit(10)
        schema = self.get_schema(request, is_safe=True)
        data = [schema.model_validate(p).model_dump() for p in products]
        return json({"results": data}, status=HTTPStatus.HTTP_200_OK)

# Application
app = Sanic("MyApp")
srfconfig.set_app(app)

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
- Browse [Configuration Options](config.md) to learn about configuration settings
