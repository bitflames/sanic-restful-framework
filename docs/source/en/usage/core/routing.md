# Routing

The SRF routing system automatically generates RESTful routes for ViewSets through the `SanicRouter` class.

## SanicRouter Basics

`SanicRouter` is the core routing class of SRF, responsible for:

- Registering ViewSets as routes
- Automatically generating standard RESTful endpoints
- Discovering and registering custom operations decorated with `@action`
- Managing URL prefixes and naming

### Basic Usage

```python
from srf.route import SanicRouter
from viewsets import ProductViewSet

# Create a router
router = SanicRouter(prefix="api")

# Register a ViewSet
router.register("products", ProductViewSet, name="products")

# Get the Blueprint and add it to the application
app.blueprint(router.get_blueprint())
```

## Initialization Parameters

### SanicRouter(bp=None, prefix="")

```python
router = SanicRouter(
    bp=None,          # Optional: existing Blueprint object
    prefix="api"      # Optional: URL prefix
)
```

**Parameter Description**:

- `bp`: Optional Sanic Blueprint object. If not provided, it will be created automatically.
- `prefix`: URL prefix that will be added to all routes.

## Registering ViewSets

### register(path, view_cls, name=None)

```python
router.register(
    path="products",           # URL path
    view_cls=ProductViewSet,   # ViewSet class
    name="products"            # Optional: route name prefix
)
```

**Parameter Description**:

- `path`: The URL path for the resource (without the prefix)
- `view_cls`: The ViewSet class
- `name`: A prefix for the route name used to generate route names

## Auto-generated Routes

When a ViewSet is registered, `SanicRouter` automatically generates the following routes:

### Standard CRUD Routes

Assuming the registration code is:

```python
router = SanicRouter(prefix="api")
router.register("products", ProductViewSet, name="products")
```

Generated routes:

| HTTP Method | URL Path | Action | ViewSet Method | Route Name |
|-------------|----------|--------|----------------|------------|
| GET | `/api/products` | List | `list()` | `products-list` |
| POST | `/api/products` | Create | `create()` | `products-list` |
| GET | `/api/products/<pk:int>` | Detail | `retrieve()` | `products-detail` |
| PUT | `/api/products/<pk:int>` | Full Update | `update()` | `products-detail` |
| PATCH | `/api/products/<pk:int>` | Partial Update | `update()` | `products-detail` |
| DELETE | `/api/products/<pk:int>` | Delete | `destroy()` | `products-detail` |

### Custom Action Routes

For methods decorated with `@action`:

**Collection-level action** (`detail=False`):

```python
@action(methods=["get"], detail=False, url_path="featured")
async def list_featured(self, request):
    pass
```

Generated route:

- URL: `/api/products/featured`
- Method: GET
- Route name: `products-list_featured`

**Detail-level action** (`detail=True`):

```python
@action(methods=["post"], detail=True, url_path="publish")
async def publish(self, request, pk):
    pass
```

Generated route:

- URL: `/api/products/<pk:int>/publish`
- Method: POST
- Route name: `products-publish`

## URL Prefixes

URL prefixes are used to add a common prefix to all routes.

### Single Prefix

```python
router = SanicRouter(prefix="api")
router.register("products", ProductViewSet)
# Generated: /api/products, /api/products/<pk>
```

### Versioned API

```python
# v1 API
router_v1 = SanicRouter(prefix="api/v1")
router_v1.register("products", ProductViewSetV1)
# Generated: /api/v1/products

# v2 API
router_v2 = SanicRouter(prefix="api/v2")
router_v2.register("products", ProductViewSetV2)
# Generated: /api/v2/products

# Register to application
app.blueprint(router_v1.get_blueprint())
app.blueprint(router_v2.get_blueprint())
```

### Nested Resources

```python
# Product routes
product_router = SanicRouter(prefix="api/products")
product_router.register("", ProductViewSet)
# Generated: /api/products, /api/products/<pk>

# Review routes (nested under products)
review_router = SanicRouter(prefix="api/products/<product_id:int>/reviews")
review_router.register("", ReviewViewSet)
# Generated: /api/products/<product_id>/reviews
```

## Multiple ViewSets Registration

### Registering in the Same Router

```python
router = SanicRouter(prefix="api")

# Register multiple ViewSets
router.register("products", ProductViewSet)
router.register("categories", CategoryViewSet)
router.register("orders", OrderViewSet)
router.register("reviews", ReviewViewSet)

# Add to application at once
app.blueprint(router.get_blueprint())
```

### Using Multiple Routers

```python
# Public API routes
public_router = SanicRouter(prefix="api/public")
public_router.register("products", ProductViewSet)
public_router.register("categories", CategoryViewSet)

# Admin API routes
admin_router = SanicRouter(prefix="api/admin")
admin_router.register("users", UserViewSet)
admin_router.register("orders", OrderViewSet)

# Register to application
app.blueprint(public_router.get_blueprint())
app.blueprint(admin_router.get_blueprint())
```

## Custom Blueprint

You can pass your own Blueprint object:

```python
from sanic import Blueprint
from srf.route import SanicRouter

# Create a custom Blueprint
my_blueprint = Blueprint("my_api", url_prefix="/api")

# Use the custom Blueprint
router = SanicRouter(bp=my_blueprint, prefix="")
router.register("products", ProductViewSet)

# Register to application
app.blueprint(router.get_blueprint())
```

## Reverse URL Resolution

Use route names to generate URLs:

```python
from sanic import Sanic

app = Sanic("MyApp")

# ... register routes ...

# Reverse URL resolution
url = app.url_for("products-list")
# Result: /api/products

url = app.url_for("products-detail", pk=1)
# Result: /api/products/1

url = app.url_for("products-list_featured")
# Result: /api/products/featured

url = app.url_for("products-publish", pk=1)
# Result: /api/products/1/publish
```

In ViewSet:

```python
class ProductViewSet(BaseViewSet):
    async def create(self, request):
        # ... create product ...
        
        # Generate detail URL
        detail_url = request.app.url_for("products-detail", pk=product.id)
        
        return json({
            "id": product.id,
            "url": detail_url
        }, status=201)
```

## Route Middleware

Add middleware for specific routes:

```python
from sanic import Blueprint
from srf.route import SanicRouter

# Create Blueprint
bp = Blueprint("api", url_prefix="/api")

# Add middleware
@bp.middleware("request")
async def add_custom_header(request):
    request.ctx.custom_data = "value"

# Use Blueprint
router = SanicRouter(bp=bp, prefix="")
router.register("products", ProductViewSet)

app.blueprint(router.get_blueprint())
```

## Complete Example

### Example 1: Basic Routing Setup

```python
# app.py
from sanic import Sanic
from srf.route import SanicRouter
from viewsets import ProductViewSet, CategoryViewSet

app = Sanic("ShopApp")

# Create router
router = SanicRouter(prefix="api")

# Register ViewSets
router.register("products", ProductViewSet, name="products")
router.register("categories", CategoryViewSet, name="categories")

# Add to application
app.blueprint(router.get_blueprint())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

Generated routes:

```
GET    /api/products              -> list
POST   /api/products              -> create
GET    /api/products/<pk>         -> retrieve
PUT    /api/products/<pk>         -> update
PATCH  /api/products/<pk>         -> update
DELETE /api/products/<pk>         -> destroy

GET    /api/categories            -> list
POST   /api/categories            -> create
GET    /api/categories/<pk>       -> retrieve
PUT    /api/categories/<pk>       -> update
PATCH  /api/categories/<pk>       -> update
DELETE /api/categories/<pk>       -> destroy
```

### Example 2: Multi-Version API

```python
# routes.py
from srf.route import SanicRouter
from viewsets.v1 import ProductViewSetV1
from viewsets.v2 import ProductViewSetV2

def register_routes(app):
    # v1 routes
    router_v1 = SanicRouter(prefix="api/v1")
    router_v1.register("products", ProductViewSetV1)
    app.blueprint(router_v1.get_blueprint())
    
    # v2 routes
    router_v2 = SanicRouter(prefix="api/v2")
    router_v2.register("products", ProductViewSetV2)
    app.blueprint(router_v2.get_blueprint())
```

Generated routes:

```
# v1 API
GET    /api/v1/products           -> ProductViewSetV1.list
POST   /api/v1/products           -> ProductViewSetV1.create
GET    /api/v1/products/<pk>      -> ProductViewSetV1.retrieve

# v2 API
GET    /api/v2/products           -> ProductViewSetV2.list
POST   /api/v2/products           -> ProductViewSetV2.create
GET    /api/v2/products/<pk>      -> ProductViewSetV2.retrieve
```

## Route Debugging

### View All Routes

```python
@app.before_server_start
async def print_routes(app, loop):
    """Print all registered routes"""
    for route in app.router.routes:
        print(f"{route.methods} {route.path} -> {route.name}")
```

### Use Sanic's Route List

```python
from sanic import Sanic

app = Sanic("MyApp")
# ... register routes ...

# Print routes
for route in app.router.routes:
    methods = ", ".join(route.methods)
    print(f"[{methods}] {route.path}")
```

Example Output:

```
[GET, POST] /api/products
[GET, PUT, PATCH, DELETE] /api/products/<pk:int>
[GET] /api/products/featured
[POST] /api/products/<pk:int>/publish
```

## Best Practices

1. **Use meaningful path names**: Paths should clearly indicate the type of resource
2. **Maintain consistent URL structure**: Use a uniform naming convention
3. **Version your API**: Use URL prefixes to distinguish between versions
4. **Organize modularly**: Group related routes together
5. **Use route names**: Utilize route names for URL reverse resolution
6. **Document routes**: Add docstrings for each ViewSet

## Frequently Asked Questions

### How to disable certain HTTP methods?

Override the corresponding method and return a 405 error:

```python
class ProductViewSet(BaseViewSet):
    async def destroy(self, request, pk):
        """Disable delete operation"""
        from sanic.response import json
        return json({"error": "Delete operation is not supported"}, status=405)
```

### How to customize URL parameter types?

Use Sanic's path parameter syntax:

```python
# Default uses int
# /api/products/<pk:int>

# You can use other types in custom actions
@action(methods=["get"], detail=True, url_path="by-slug/<slug:str>")
async def get_by_slug(self, request, pk, slug):
    pass
```

### How to handle nested resources?

Use multiple routers and different URL prefixes:

```python
# Product routes
router.register("products", ProductViewSet)

# Reviews under products (need to handle product_id in ViewSet)
review_router = SanicRouter(prefix="api/products/<product_id:int>")
review_router.register("reviews", ReviewViewSet)
```

## Next Steps

- Learn [Views](viewsets.md) to understand how to create ViewSets
- Read [Authentication](authentication.md) to learn how to protect routes
- View [Permissions](permissions.md) to understand access control