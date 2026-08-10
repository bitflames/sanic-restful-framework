# ViewSet Decorators

ViewSet decorators are used to extend and customize the behavior of ViewSets, with the most important being the `@action` decorator.

## @action Decorator

The `@action` decorator is used to add custom operations to a ViewSet beyond the standard CRUD operations.

### Basic Usage

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from sanic.response import json

class ProductViewSet(BaseViewSet):
    @action(methods=["get"], detail=False, url_path="featured")
    async def list_featured(self, request):
        """Get featured products (collection-level operation)"""
        products = await Product.filter(is_featured=True)
        schema = self.get_schema(request, is_safe=True)
        data = [schema.model_validate(p).model_dump() for p in products]
        return json({"results": data})
    
    @action(methods=["post"], detail=True, url_path="publish")
    async def publish(self, request, pk):
        """Publish product (detail-level operation)"""
        product = await self.get_object(request, pk)
        product.is_published = True
        product.published_at = datetime.now()
        await product.save()
        
        return json({"message": "Product has been published"})
```

### Decorator Parameters

```python
action(
    *,
    detail: bool = False,                 # True for detail-level; False for collection-level
    methods: Sequence[str] = ("GET",),    # Default HTTP methods
    url_path: str | None = None,          # Default: "/<method name>"
    url_name: str | None = None,          # Default: method name
    **kwargs,
)
```

**Parameter Description**:

| Parameter | Type | Default | Description |
|---------|------|---------|-------------|
| `methods` | Sequence[str] | `("GET",)` | HTTP methods, e.g. `["get"]`, `["post"]`, `["get", "post"]` (case-insensitive when registered) |
| `detail` | bool | `False` | `True` for detail-level operation (requires pk), `False` for collection-level |
| `url_path` | str \| None | `/<method name>` | Custom URL path segment |
| `url_name` | str \| None | Method name | Route name, used for URL reverse resolution |

### Collection-Level Operation vs Detail-Level Operation

#### Collection-Level Operation (`detail=False`)

Does not require a resource ID, operates on the entire collection.

**Characteristics**:
- No pk parameter required
- URL format: `/api/products/action-name`
- Suitable for batch operations, statistics, search, etc.

**Example**:

```python
@action(methods=["get"], detail=False, url_path="statistics")
async def get_statistics(self, request):
    """Get product statistics"""
    from tortoise.functions import Count, Avg, Sum
    
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
    schema = self.get_schema(request, is_safe=True)
    data = [schema.model_validate(p).model_dump() for p in products]
    
    return json({"results": data})
```

**Generated Routes**:
- `GET /api/products/statistics`
- `POST /api/products/bulk-update`
- `GET /api/products/search`

#### Detail-Level Operation (`detail=True`)

Requires a resource ID, operates on a single resource.

**Characteristics**:
- Requires pk parameter
- URL format: `/api/products/<pk>/action-name`
- Suitable for status changes, related operations, etc.

**Example**:

```python
@action(methods=["post"], detail=True, url_path="activate")
async def activate(self, request, pk):
    """Activate product"""
    product = await self.get_object(request, pk)
    
    if product.is_active:
        return json({"error": "Product is already active"}, status=400)
    
    product.is_active = True
    await product.save()
    
    return json({"message": "Product has been activated"})

@action(methods=["post"], detail=True, url_path="duplicate")
async def duplicate(self, request, pk):
    """Duplicate product"""
    product = await self.get_object(request, pk)
    
    # Duplicate product
    new_product = await Product.create(
        name=f"{product.name} (Copy)",
        price=product.price,
        description=product.description,
        category_id=product.category_id
    )
    
    schema = self.get_schema(request, is_safe=True)
    data = schema.model_validate(new_product).model_dump()
    
    return json(data, status=201)

@action(methods=["get"], detail=True, url_path="related")
async def get_related(self, request, pk):
    """Get related products"""
    product = await self.get_object(request, pk)
    
    # Other products in the same category
    related = await Product.filter(
        category_id=product.category_id
    ).exclude(id=product.id).limit(5)
    
    schema = self.get_schema(request, is_safe=True)
    data = [schema.model_validate(p).model_dump() for p in related]
    
    return json({"results": data})
```

**Generated Routes**:
- `POST /api/products/<pk>/activate`
- `POST /api/products/<pk>/duplicate`
- `GET /api/products/<pk>/related`

### Multiple HTTP Methods

An action can support multiple HTTP methods:

```python
@action(methods=["get", "post"], detail=True, url_path="comments")
async def handle_comments(self, request, pk):
    """Handle comments (GET to retrieve, POST to add)"""
    product = await self.get_object(request, pk)
    
    if request.method == "GET":
        # Get comments
        comments = await product.comments.all()
        return json({"results": [c.to_dict() for c in comments]})
    
    elif request.method == "POST":
        # Add comment
        content = request.json.get("content")
        comment = await Comment.create(
            product=product,
            user=request.ctx.user,
            content=content
        )
        return json(comment.to_dict(), status=201)
```

### Custom URL Path

Use the `url_path` parameter to customize the URL:

```python
@action(methods=["post"], detail=True, url_path="change-status")
async def change_status(self, request, pk):
    """Change status"""
    product = await self.get_object(request, pk)
    new_status = request.json.get("status")
    
    product.status = new_status
    await product.save()
    
    return json({"message": "Status has been updated"})
```

URL: `POST /api/products/<pk>/change-status`

If `url_path` is omitted, the default is `/<method name>` (underscores are kept):

```python
@action(detail=True, methods=["post"])
async def change_status(self, request, pk):
    """Change status"""
    pass
```

URL: `POST /api/products/<pk>/change_status`

### Custom Route Name

Use the `url_name` parameter to customize the route name for URL reverse resolution:

```python
@action(detail=False, methods=["get"], url_path="featured", url_name="featured_list")
async def featured(self, request):
    """Featured list"""
    pass

# Reverse resolution; when default prefix="api", Blueprint name is "api"
url = request.app.url_for("api.featured_list")
```

### Permission Control

Permission checks can be performed within an action:

```python
from srf.permission.permission import IsRoleAdminUser
from sanic.exceptions import Forbidden

@action(methods=["post"], detail=True, url_path="approve")
async def approve(self, request, pk):
    """Approve product (only admins)"""
    # Check admin permission
    if not IsRoleAdminUser.has_permission(request, self):
        raise Forbidden("Admin permission required")
    
    product = await self.get_object(request, pk)
    product.is_approved = True
    await product.save()
    
    return json({"message": "Approved"})
```

### Complete Example

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.permission.permission import IsAuthenticated, IsRoleAdminUser
from sanic.response import json
from sanic.exceptions import Forbidden
from sanic.constants import SAFE_HTTP_METHODS
from datetime import datetime
from models import Product, Comment
from schemas import ProductSchemaReader, ProductSchemaWriter

class ProductViewSet(BaseViewSet):
    """Product ViewSet - Decorator Example"""
    
    permission_classes = (IsAuthenticated,)
    
    @property
    def queryset(self):
        return Product.all()
    
    def get_schema(self, request, is_safe=False):
        if request.method.upper() in SAFE_HTTP_METHODS or is_safe:
            return ProductSchemaReader
        return ProductSchemaWriter
    
    # Collection-level operations
    @action(methods=["get"], detail=False, url_path="featured")
    async def list_featured(self, request):
        """Get featured products"""
        products = await Product.filter(is_featured=True, is_active=True)
        schema = self.get_schema(request, is_safe=True)
        data = [schema.model_validate(p).model_dump() for p in products]
        return json({"results": data})
    
    @action(methods=["get"], detail=False, url_path="statistics")
    async def get_statistics(self, request):
        """Get statistics"""
        from tortoise.functions import Count, Avg
        
        stats = await Product.all().annotate(
            total=Count("id"),
            avg_price=Avg("price")
        ).values("total", "avg_price")
        
        return json(stats[0] if stats else {})
    
    @action(methods=["post"], detail=False, url_path="bulk-delete")
    async def bulk_delete(self, request):
        """Bulk delete (only admins)"""
        # Check admin permission
        user = self.get_current_user(request)
        if not user.role or user.role.name != 'admin':
            raise Forbidden("Admin permission required")
        
        ids = request.json.get("ids", [])
        count = await Product.filter(id__in=ids).delete()
        
        return json({"message": f"Successfully deleted {count} products"})
    
    # Detail-level operations
    @action(methods=["post"], detail=True, url_path="publish")
    async def publish(self, request, pk):
        """Publish product"""
        product = await self.get_object(request, pk)
        
        if product.is_published:
            return json({"error": "Product is already published"}, status=400)
        
        product.is_published = True
        product.published_at = datetime.now()
        await product.save()
        
        return json({"message": "Product has been published"})
    
    @action(methods=["post"], detail=True, url_path="duplicate")
    async def duplicate(self, request, pk):
        """Duplicate product"""
        product = await self.get_object(request, pk)
        
        new_product = await Product.create(
            name=f"{product.name} (Copy)",
            price=product.price,
            description=product.description,
            category_id=product.category_id
        )
        
        schema = self.get_schema(request, is_safe=True)
        data = schema.model_validate(new_product).model_dump()
        
        return json(data, status=201)
    
    @action(methods=["get", "post"], detail=True, url_path="comments")
    async def handle_comments(self, request, pk):
        """Handle comments"""
        product = await self.get_object(request, pk)
        
        if request.method == "GET":
            # Get comments
            comments = await product.comments.all()
            return json({"results": [c.to_dict() for c in comments]})
        
        elif request.method == "POST":
            # Add comment
            content = request.json.get("content")
            if not content:
                return json({"error": "Comment content cannot be empty"}, status=400)
            
            comment = await Comment.create(
                product=product,
                user=request.ctx.user,
                content=content
            )
            return json(comment.to_dict(), status=201)
```

## Best Practices

1. **Semantic Naming**: Method names should clearly express the intent of the operation.
2. **Appropriate Grouping**: Use consistent URL path prefixes for related operations.
3. **Permission Checks**: Add permission verification for sensitive operations.
4. **Error Handling**: Provide friendly error messages.
5. **Documentation Strings**: Add clear documentation for each action.
6. **HTTP Methods**: Follow RESTful conventions (GET for queries, POST for creation/operations).
7. **Idempotency**: GET operations should be idempotent.

## Common Patterns

### Status Change

```python
@action(methods=["post"], detail=True, url_path="archive")
async def archive(self, request, pk):
    """Archive"""
    obj = await self.get_object(request, pk)
    obj.status = "archived"
    await obj.save()
    return json({"message": "Archived"})
```

### Related Resources

```python
@action(methods=["get"], detail=True, url_path="reviews")
async def get_reviews(self, request, pk):
    """Get reviews"""
    obj = await self.get_object(request, pk)
    reviews = await obj.reviews.all()
    return json({"results": [r.to_dict() for r in reviews]})
```

### Batch Operations

```python
@action(methods=["post"], detail=False, url_path="bulk-update")
async def bulk_update(self, request):
    """Bulk update"""
    ids = request.json.get("ids", [])
    updates = request.json.get("updates", {})
    await Model.filter(id__in=ids).update(**updates)
    return json({"message": "Update successful"})
```

## Next Steps

- Read [Routing](routing.md) to understand the routing system
- Learn [Permissions](permissions.md) to add permission control
- View [ViewSet](viewsets.md) to understand the basics of ViewSet