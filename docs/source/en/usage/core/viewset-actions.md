# ViewSet Decorators

ViewSet decorators extend and customize ViewSet behavior. The most important one is the `@action` decorator.

## The @action decorator

The `@action` decorator adds custom actions to a ViewSet, beyond the standard CRUD operations.

### Basic usage

```python
from datetime import datetime
from sanic.response import json
from srf.route import SanicRouter
from srf.views import BaseViewSet
from srf.views.decorators import action
from models import Product
from schemas import ProductSchemaReader


class ProductViewSet(BaseViewSet):
    @action(methods=["get"], detail=False, url_path="featured")
    async def list_featured(self, request):
        """Get featured products (collection-level action)"""
        products = await Product.filter(is_featured=True)
        data = [ProductSchemaReader.model_validate(p).model_dump(mode="json") for p in products]
        return json({"results": data})

    @action(methods=["post"], detail=True, url_path="publish")
    async def publish(self, request, pk):
        """Publish a product (detail-level action)"""
        product = await self.get_object(pk)
        product.is_published = True
        product.published_at = datetime.now()
        await product.save()

        return json({"message": "Product published"})
```

After registering the ViewSet with the router, you can call these actions with `curl`. The following example assumes `app` is a Sanic application
that has already been created and configured with a database:

```python
router = SanicRouter(app, prefix="api")
router.register("products", ProductViewSet, name="products")
```

```bash
# Collection-level action: query featured products
curl http://localhost:8000/api/products/featured

# Detail-level action: publish the product with ID 42
curl -X POST http://localhost:8000/api/products/42/publish
```

### @action decorator parameters

```python
from collections.abc import Sequence
from srf.views.decorators import action

action(
    *,
    detail: bool = False,                 # True for detail-level; False for collection-level
    methods: Sequence[str] = ("GET",),    # Default HTTP methods
    url_path: str | None = None,          # Default: "/<method name>"
    url_name: str | None = None,          # Default: method name
    **kwargs,
)
```

**Parameter reference**:

| Parameter | Type | Default | Description |
| ------ | ------ | -------- | ------ |
| `methods` | Sequence[str] | `("GET",)` | List of HTTP methods, such as `["get"]`, `["post"]`, `["get", "post"]` (case-insensitive on registration) |
| `detail` | bool | `False` | `True` for a detail-level action (requires pk), `False` for a collection-level action |
| `url_path` | str \| None | `/<method name>` | Custom URL path segment |
| `url_name` | str \| None | Method name | Route name, used for URL reverse resolution |

### Collection-level vs detail-level actions

#### Collection-level actions (`detail=False`)

No resource ID is needed; the action applies to the whole collection.

**Features**:

- No pk parameter
- URL format: `/api/products/action-name`
- Suitable for batch operations, statistics, search, etc.

**Example**:

The following snippets are all methods of `ProductViewSet`; they continue to use the imports from the earlier example.

```python
from tortoise.functions import Count, Avg, Sum


@action(methods=["get"], detail=False, url_path="statistics")
async def get_statistics(self, request):
    """Get product statistics"""    
    
    stats = await Product.all().annotate(
        total=Count("id"),
        avg_price=Avg("price"),
        total_value=Sum("price")
    ).values("total", "avg_price", "total_value")
    
    return json(stats[0] if stats else {})


@action(methods=["post"], detail=False, url_path="bulk-update")
async def bulk_update(self, request):
    """Bulk update products"""
    ids = request.json.get("ids", [])
    updates = request.json.get("updates", {})

    if not ids:
        return json({"error": "Please provide a list of product IDs"}, status=400)

    await Product.filter(id__in=ids).update(**updates)

    return json({"message": f"Successfully updated {len(ids)} products"})


@action(methods=["get"], detail=False, url_path="search")
async def advanced_search(self, request):
    """Advanced search"""
    keyword = request.args.get("q", "")
    category = request.args.get("category")

    queryset = Product.all()

    if keyword:
        queryset = queryset.filter(name__icontains=keyword)

    if category:
        queryset = queryset.filter(category_id=category)

    products = await queryset
    data = [ProductSchemaReader.model_validate(p).model_dump(mode="json") for p in products]

    return json({"results": data})
```

**Generated routes**:

- `GET /api/products/statistics`
- `POST /api/products/bulk-update`
- `GET /api/products/search`

Corresponding `curl` examples:

```bash
curl "http://localhost:8000/api/products/statistics"
curl "http://localhost:8000/api/products/search?q=keyboard&category=2"
curl -X POST http://localhost:8000/api/products/bulk-update \
  -H "Content-Type: application/json" \
  -d '{"ids":[1,2],"updates":{"is_active":false}}'
```

#### Detail-level actions (`detail=True`)

A resource ID is required; the action applies to a single resource.

**Features**:

- Requires a pk parameter
- URL format: `/api/products/<pk>/action-name`
- Suitable for state changes, related operations, etc.

**Example**:

```python
@action(methods=["post"], detail=True, url_path="activate")
async def activate(self, request, pk):
    """Activate a product"""
    product = await self.get_object(pk)

    if product.is_active:
        return json({"error": "The product is already active"}, status=400)

    product.is_active = True
    await product.save()

    return json({"message": "Product activated"})


@action(methods=["post"], detail=True, url_path="duplicate")
async def duplicate(self, request, pk):
    """Duplicate a product"""
    product = await self.get_object(pk)

    # Duplicate the product
    new_product = await Product.create(
        name=f"{product.name} (Copy)",
        price=product.price,
        description=product.description,
        category_id=product.category_id
    )

    data = ProductSchemaReader.model_validate(new_product).model_dump()

    return json(data, status=201)


@action(methods=["get"], detail=True, url_path="related")
async def get_related(self, request, pk):
    """Get related products"""
    product = await self.get_object(pk)

    # Other products in the same category
    related = await Product.filter(category_id=product.category_id).exclude(id=product.id).limit(5)

    data = [ProductSchemaReader.model_validate(p).model_dump(mode="json") for p in related]

    return json({"results": data})
```

**Generated routes**:

- `POST /api/products/<pk>/activate`
- `POST /api/products/<pk>/duplicate`
- `GET /api/products/<pk>/related`

Corresponding `curl` examples:

```bash
curl -X POST http://localhost:8000/api/products/42/activate
curl -X POST http://localhost:8000/api/products/42/duplicate
curl http://localhost:8000/api/products/42/related
```

### Multiple HTTP methods

An action can support multiple HTTP methods:

```python
from models import Comment


@action(methods=["get", "post"], detail=True, url_path="comments")
async def handle_comments(self, request, pk):
    """Handle comments (GET to fetch, POST to add)"""
    product = await self.get_object(pk)

    if request.method == "GET":
        # Get comments
        comments = await product.comments.all()
        return json({"results": [{"id": c.id, "content": c.content} for c in comments]})

    elif request.method == "POST":
        # Add a comment
        content = request.json.get("content")
        comment = await Comment.create(
            product=product,
            user=request.ctx.user,
            content=content
        )
        return json({"id": comment.id, "content": comment.content}, status=201)
```

The same URL can perform different operations depending on the HTTP method:

```bash
# Get comments for the product with ID 42
curl http://localhost:8000/api/products/42/comments

# Add a comment (request middleware must have set request.ctx.user)
curl -X POST http://localhost:8000/api/products/42/comments \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"content":"Very useful"}'
```

### Custom URL path

Use the `url_path` parameter to customize the URL:

```python
@action(methods=["post"], detail=True, url_path="change-status")
async def change_status(self, request, pk):
    """Change status"""
    product = await self.get_object(pk)
    new_status = request.json.get("status")
    
    product.status = new_status
    await product.save()
    
    return json({"message": "Status updated"})
```

URL: `POST /api/products/<pk>/change-status`

```bash
curl -X POST http://localhost:8000/api/products/42/change-status \
  -H "Content-Type: application/json" \
  -d '{"status":"archived"}'
```

When `url_path` is omitted, it defaults to `/<method name>` (underscores are not converted):

```python
@action(detail=True, methods=["post"])
async def change_status(self, request, pk):
    """Change status"""
    pass
```

URL: `POST /api/products/<pk>/change_status`

### Custom route name

Use the `url_name` parameter to customize the route name, which is used for URL reverse resolution:

```python
@action(detail=False, methods=["get"], url_path="featured", url_name="featured_list")
async def featured(self, request):
    """Featured list"""
    pass


# Reverse resolution; when registered directly on the Sanic application, the name is products-featured_list
url = request.app.url_for("products-featured_list")
```

### Permission control

You can perform permission checks inside an action:

```python
from srf.permission.permission import SuperuserOnly
from sanic.exceptions import Forbidden


@action(methods=["post"], detail=True, url_path="approve")
async def approve(self, request, pk):
    """Approve a product (admin only)"""
    # Check administrator permission
    if not SuperuserOnly.has_permission(request, self):
        raise Forbidden("Superuser permission required")

    product = await self.get_object(pk)
    product.is_approved = True
    await product.save()

    return json({"message": "Approved"})
```

### Complete example

Combine the action methods above with the regular ViewSet configuration; see
[ViewSet](viewsets.md) for complete CRUD and schema configuration.

## Best practices

1. **Semantic naming**: method names should clearly express the intent of the operation
2. **Appropriate grouping**: related operations should use consistent URL path prefixes
3. **Permission checks**: add permission validation for sensitive operations
4. **Error handling**: provide friendly error messages
5. **Docstrings**: add clear documentation for each action
6. **HTTP methods**: follow RESTful conventions (GET for queries, POST for creation/operations)
7. **Idempotency**: GET operations should be idempotent

## Common patterns

### State changes

```python
@action(methods=["post"], detail=True, url_path="archive")
async def archive(self, request, pk):
    """Archive"""
    obj = await self.get_object(pk)
    obj.status = "archived"
    await obj.save()
    return json({"message": "Archived"})
```

### Related resources

```python
@action(methods=["get"], detail=True, url_path="reviews")
async def get_reviews(self, request, pk):
    """Get reviews"""
    obj = await self.get_object(pk)
    reviews = await obj.reviews.all()
    return json({"results": [{"id": review.id} for review in reviews]})
```

### Batch operations

```python
@action(methods=["post"], detail=False, url_path="bulk-update")
async def bulk_update(self, request):
    """Bulk update"""
    ids = request.json.get("ids", [])
    updates = request.json.get("updates", {})
    await Product.filter(id__in=ids).update(**updates)
    return json({"message": "Updated successfully"})
```

## Next steps

- Read [Routing](routing.md) to learn about the routing system
- Study [Permissions](permissions.md) to add permission control
- See [ViewSet](viewsets.md) for ViewSet basics
