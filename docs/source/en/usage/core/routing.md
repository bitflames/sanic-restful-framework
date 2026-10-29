# Routing

SRF's routing system automatically generates RESTful routes for ViewSets through the `SanicRouter` class.

## SanicRouter basics

`SanicRouter` is SRF's core routing class. It is responsible for:

- Registering ViewSets as routes
- Automatically generating standard RESTful endpoints
- Discovering and registering custom actions decorated with `@action`
- Managing URL prefixes and naming

### Basic usage

```python
from sanic import Sanic
from srf.route import SanicRouter
from viewsets import ProductViewSet

app = Sanic("ShopApp")
router = SanicRouter(app, prefix="api")

# Register the ViewSet
router.register("products", ProductViewSet, name="products")
```

## Initialization parameters

### `SanicRouter(instance, prefix="")`

```python
router = SanicRouter(app, prefix="api")
```

**Parameter reference**:

- `instance`: Required. A Sanic `Sanic` or `Blueprint` instance. When a Sanic instance is passed, routes are registered directly on the application; when a Blueprint is passed, routes are registered on that Blueprint.
- `prefix`: URL prefix added in front of all routes

## Registering ViewSets

### register(path, view_cls, name=None)

```python
router.register(
    path="products",           # URL path
    view_cls=ProductViewSet,   # ViewSet class
    name="products"            # Optional: route name
)
```

**Parameter reference**:

- `path`: URL path of the resource (without the prefix)
- `view_cls`: ViewSet class
- `name`: Route name prefix used to generate route names

## Automatically generated routes

When a ViewSet is registered, `SanicRouter` automatically generates the following routes:

### Standard CRUD routes

Assume the registration code is:

```python
router = SanicRouter(app, prefix="api")
router.register("products", ProductViewSet, name="products")
```

Generated routes:

| HTTP method | URL path             | Operation        | ViewSet method | Route name        |
| ----------- | -------------------- | ---------------- | -------------- | ----------------- |
| GET         | `/api/products`      | List             | `list()`       | `products-list`   |
| HEAD        | `/api/products`      | List (no body)   | `list()`       | `products-list`   |
| POST        | `/api/products`      | Create           | `create()`     | `products-list`   |
| GET         | `/api/products/<pk>` | Detail           | `retrieve()`   | `products-detail` |
| HEAD        | `/api/products/<pk>` | Detail (no body) | `retrieve()`   | `products-detail` |
| PUT         | `/api/products/<pk>` | Full update      | `update()`     | `products-detail` |
| PATCH       | `/api/products/<pk>` | Partial update   | `update()`     | `products-detail` |
| DELETE      | `/api/products/<pk>` | Delete           | `destroy()`    | `products-detail` |

### Custom action routes

For methods decorated with `@action`:

**Collection-level actions** (`detail=False`):

```python
@action(methods=["get"], detail=False, url_path="featured")
async def list_featured(self, request):
    pass
```

Generated route:

- URL: `/api/products/featured`
- Method: GET
- Route name: `products-list_featured` (the default `url_name` is the method name)

**Detail-level actions** (`detail=True`):

```python
@action(methods=["post"], detail=True, url_path="publish")
async def publish(self, request, pk):
    pass
```

Generated route:

- URL: `/api/products/<pk>/publish`
- Method: POST
- Route name: `products-publish` (the default `url_name` is the method name)

## URL prefixes

URL prefixes add a common prefix to all routes.

### A single prefix

```python
router = SanicRouter(app, prefix="api")
router.register("products", ProductViewSet)
# Generated: /api/products, /api/products/<pk>
```

### Versioned APIs

```python
# v1 API
router_v1 = SanicRouter(app, prefix="api/v1")
router_v1.register("products", ProductViewSetV1)
# Generated: /api/v1/products

# v2 API
router_v2 = SanicRouter(app, prefix="api/v2")
router_v2.register("products", ProductViewSetV2)
# Generated: /api/v2/products
```

### Nested resources

`SanicRouter.register()` appends collection and detail paths after the resource name. For nested routes, put the parent resource ID in the prefix and register the child resource name as `path`. The child resource ViewSet must limit its data by the parent resource ID in `get_queryset()`:

```python
review_router = SanicRouter(app, prefix="api/products/<product_id:int>")
review_router.register("reviews", ReviewViewSet)
# Collection: /api/products/<product_id:int>/reviews
# Detail: /api/products/<product_id:int>/reviews/<pk>
```

## Registering multiple ViewSets

### Registering in the same router

```python
router = SanicRouter(app, prefix="api")

# Register multiple ViewSets
router.register("products", ProductViewSet)
router.register("categories", CategoryViewSet)
router.register("orders", OrderViewSet)
router.register("reviews", ReviewViewSet)

```

### Using multiple routers

```python
# Public API routes
public_router = SanicRouter(app, prefix="api/public")
public_router.register("products", ProductViewSet)
public_router.register("categories", CategoryViewSet)

# Admin API routes
admin_router = SanicRouter(app, prefix="api/admin")
admin_router.register("users", UserViewSet)
admin_router.register("orders", OrderViewSet)
```

## Custom Blueprints

When you need to organize routes by module or add Blueprint middleware to routes, you can pass your own Blueprint object.
`SanicRouter` registers routes directly on that Blueprint; after registration, mount the Blueprint on the Sanic application
with `app.blueprint(bp)`. The URL prefix is set uniformly through `SanicRouter`'s `prefix`:

```python
from sanic import Blueprint
from srf.route import SanicRouter

# Create a custom Blueprint
my_blueprint = Blueprint("my_api")

# Use the custom Blueprint
router = SanicRouter(my_blueprint, prefix="api")
router.register("products", ProductViewSet)

# After the Blueprint has completed route registration, mount it on the Sanic application
app.blueprint(my_blueprint)
```

## URL reverse resolution

Generate URLs using route names:

```python
from sanic import Sanic

app = Sanic("MyApp")

# ... register routes ...

# Reverse resolve a URL
url = app.url_for("products-list")
# Result: /api/products

url = app.url_for("products-detail", pk=1)
# Result: /api/products/1

url = app.url_for("products-list_featured")
# Result: /api/products/featured

url = app.url_for("products-publish", pk=1)
# Result: /api/products/1/publish
```

Using it in a ViewSet:

```python
class ProductViewSet(BaseViewSet):
    async def create(self, request):
        # ... create the product ...

        # Generate the detail URL
        detail_url = request.app.url_for("products-detail", pk=product.id)

        return json({"id": product.id, "url": detail_url}, status=201)
```

## Route middleware

Add middleware for specific routes:

```python
from sanic import Blueprint
from srf.route import SanicRouter

# Create a Blueprint
bp = Blueprint("api")


# Add middleware
@bp.middleware("request")
async def add_custom_header(request):
    request.ctx.custom_data = "value"


# Use the Blueprint
router = SanicRouter(bp, prefix="api")
router.register("products", ProductViewSet)

app.blueprint(bp)
```

## Complete examples

### Example 1: Basic route setup

```python
# app.py
from sanic import Sanic
from srf.route import SanicRouter
from viewsets import ProductViewSet, CategoryViewSet

app = Sanic("ShopApp")

# Create the router
router = SanicRouter(app, prefix="api")

# Register ViewSets
router.register("products", ProductViewSet, name="products")
router.register("categories", CategoryViewSet, name="categories")

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

### Example 2: Multi-version API

```python
# routes.py
from srf.route import SanicRouter
from viewsets.v1 import ProductViewSetV1
from viewsets.v2 import ProductViewSetV2


def register_routes(app):
    # v1 routes
    router_v1 = SanicRouter(app, prefix="api/v1")
    router_v1.register("products", ProductViewSetV1)

    router_v2 = SanicRouter(app, prefix="api/v2")
    router_v2.register("products", ProductViewSetV2)
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

## Route debugging

### Viewing all routes

```python
@app.before_server_start
async def print_routes(app, loop):
    """Print all registered routes"""
    for route in app.router.routes:
        print(f"{route.methods} {route.path} -> {route.name}")
```

### Using Sanic's route list

```python
from sanic import Sanic

app = Sanic("MyApp")
# ... register routes ...

# Print routes
for route in app.router.routes:
    methods = ", ".join(route.methods)
    print(f"[{methods}] {route.path}")
```

Example output:

```
[GET, HEAD, POST] /api/products
[GET, HEAD, PUT, PATCH, DELETE] /api/products/<pk>
[GET] /api/products/featured
[POST] /api/products/<pk>/publish
```

## Best practices

1. **Use meaningful path names**: paths should clearly indicate the resource type
2. **Keep URL structure consistent**: use a consistent naming convention
3. **Version APIs**: use URL prefixes to distinguish versions
4. **Modular organization**: organize related routes together
5. **Use route names**: leverage route names for URL reverse resolution
6. **Document routes**: add docstrings to each ViewSet

## FAQ

### How do I disable certain HTTP methods?

Override the corresponding method and return a 405 error:

```python
class ProductViewSet(BaseViewSet):
    async def destroy(self, request, pk):
        """Disable the delete operation"""
        from sanic.response import json

        return json({"error": "Delete operations are not supported"}, status=405)
```

### How do I customize URL parameter types?

Use Sanic's path parameter syntax:

```python
# The pk parameter generated by SanicRouter does not specify a type; SRF normalizes the primary key when get_object(pk) is called
# /api/products/<pk>

# Other types can be used in custom actions
@action(methods=["get"], detail=True, url_path="by-slug/<slug:str>")
async def get_by_slug(self, request, pk, slug):
    pass
```

### How do I handle nested resources?

Use multiple routers with different URL prefixes:

```python
# Product routes
router.register("products", ProductViewSet)

# Reviews under products (product_id must be handled in the ViewSet)
review_router = SanicRouter(app, prefix="api/products/<product_id:int>")
review_router.register("reviews", ReviewViewSet)
```

## Next steps

- Study [Views](viewsets.md) to learn how to create ViewSets
- Read [Authentication](authentication.md) to learn how to protect routes
- See [Permissions](permissions.md) to learn about access control
