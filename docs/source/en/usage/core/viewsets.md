# Views (ViewSet)

ViewSet is one of the core concepts of SRF, providing an elegant way to organize and manage RESTful API endpoints.

## What is a ViewSet?

A ViewSet is a class-based view that organizes related API operations. A ViewSet typically corresponds to a resource type (such as products, orders, etc.) and provides CRUD (Create, Read, Update, Delete) operations for that resource.

### Basic Concepts

- **Resource-oriented**: Each ViewSet corresponds to a resource type
- **Automatic routing**: Automatically generates RESTful routes
- **Mixin pattern**: Combines functionality through Mixin
- **Flexible extension**: Supports custom operations

## BaseViewSet

`BaseViewSet` is the base class for all ViewSets, inheriting all CRUD Mixins.

### Basic Usage

```python
from srf.views import BaseViewSet
from models import Product
from schemas import ProductSchemaReader, ProductSchemaWriter

class ProductViewSet(BaseViewSet):
    """Product ViewSet"""
    
    @property
    def queryset(self):
        """Returns the query set"""
        return Product.all()
    
    def get_schema(self, request, *args, is_safe=False, **kwargs):
        """Returns Schema
        
        Args:
            request: Request object
            is_safe: See the actual parameter passing explanation of the Mixin; default False
        """
        # Note: When calling list/retrieve internally, is_safe defaults to False
        if request.method in ("GET", "HEAD", "OPTIONS") or is_safe:
            return ProductSchemaReader
        return ProductSchemaWriter
```

### Required Properties and Methods

#### 1. `queryset` / `get_queryset`

Provide a Tortoise ORM query set. Prefer overriding `get_queryset()` for per-request scoping; you may also set a class attribute or `@property` named `queryset`, which the default `get_queryset()` reads (and clones with `.all()` when it is a `QuerySet`).

`list()` uses `filter_queryset(self.get_queryset())`. `get_object()` and `perform_create()` also go through `get_queryset()`.

```python
# Class attribute
queryset = Product.all()

# Or a property (still consumed by get_queryset)
@property
def queryset(self):
    """Return only published products"""
    return Product.filter(is_published=True)

# Or override get_queryset for request-aware scoping
def get_queryset(self):
    return Product.filter(owner_id=self.request.ctx.user.id).prefetch_related(
        "category", "tags"
    )
```

#### 2. `get_schema` Method

Returns the Pydantic Schema used for data validation and serialization.

```python
def get_schema(self, request, *args, is_safe=False, **kwargs):
    """
    Different schemas may be used in the same request, such as controlling different fields for input or output. Use unsafe schema for input.
    
    is_safe=True: Read operation (GET), use Reader Schema
    is_safe=False: Write operation (POST/PUT/PATCH), use Writer Schema
    """
    is_read = request.method.upper() in ("GET", "HEAD", "OPTIONS")
    return ProductSchemaReader if is_read or is_safe else ProductSchemaWriter
```

**Why separate read and write schemas?**

- **Security**: Exclude read-only fields (like id, created_at) when writing
- **Flexibility**: Include computed fields and related data when reading
- **Validation**: Have stricter validation rules when writing

Example:

```python
from pydantic import BaseModel, Field
from typing import Optional

class ProductSchemaWriter(BaseModel):
    """Write Schema - For creating and updating"""
    name: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = None
    category_id: int

class ProductSchemaReader(BaseModel):
    """Read Schema - For serialization"""
    id: int
    name: str
    price: float
    description: Optional[str]
    category_id: int
    category_name: str  # Additional related field
    created_at: str
    
    class Config:
        from_attributes = True
```

## CRUD Operations

BaseViewSet provides standard CRUD operations through Mixin.

### ListModelMixin - List Operations

**Route**: `GET /api/products`

**Functionality**:
- Get a list of resources
- Support pagination
- Support filtering and searching
- Support sorting

**Response Format**:

```json
{
  "count": 100,
  "next": true,
  "previous": false,
  "results": [
    {
      "id": 1,
      "name": "Product 1",
      "price": 99.99
    }
  ]
}
```

**Customizing the list method**:

```python
class ProductViewSet(BaseViewSet):
    async def list(self, request):
        """Custom list logic"""
        # Get the query set
        queryset = self.queryset
        
        # Apply filters
        if "category" in request.args:
            category_id = request.args.get("category")
            queryset = queryset.filter(category_id=category_id)
        
        # Apply filter classes
        for filter_class in self.filter_class:
            queryset = filter_class(self).filter_queryset(request, queryset)
        
        # Pagination
        from srf.paginator import PageNumberPagination
        paginator = PageNumberPagination.from_queryset(queryset, request)
        schema = self.get_schema(request, is_safe=True)
        result = await paginator.to_dict(schema)
        
        from sanic.response import json
        return json(result)
```

### CreateModelMixin - Create Operation

**Route**: `POST /api/products`

**Functionality**: Create a new resource

**Request Body**:

```json
{
  "name": "New Product",
  "price": 99.99,
  "description": "Product description",
  "category_id": 1
}
```

**Response**:

```json
{
  "id": 1,
  "name": "New Product",
  "price": 99.99,
  "description": "Product description",
  "category_id": 1,
  "created_at": "2026-02-07 10:00:00"
}
```

**Customizing the create logic**:

```python
class ProductViewSet(BaseViewSet):
    async def perform_create(self, sch_model):
        """Custom create logic

        Args:
            sch_model: Validated Pydantic Schema instance

        Use self.request when you need request (as_view will assign it).
        """
        data = sch_model.model_dump(exclude_unset=True)
        data["created_by"] = self.request.ctx.user.id

        obj = await Product.create(**data)
        await self.send_notification(obj)
        return obj

    async def send_notification(self, product):
        """Send notification"""
        # Implement notification logic
        pass
```

### RetrieveModelMixin - Detail Operation

**Route**: `GET /api/products/<pk>`

**Functionality**: Retrieve a single resource

**Response**:

```json
{
  "id": 1,
  "name": "Product 1",
  "price": 99.99,
  "description": "Product description",
  "category_id": 1,
  "category_name": "Electronics",
  "created_at": "2026-02-07 10:00:00"
}
```

**Customizing the retrieval logic**:

```python
class ProductViewSet(BaseViewSet):
    async def retrieve(self, request, pk):
        """Custom retrieval logic"""
        # Get the object
        obj = await self.get_object(request, pk)
        
        # Record access
        await self.log_view(obj, request.ctx.user)
        
        # Serialization
        schema = self.get_schema(request, is_safe=True)
        data = schema.model_validate(obj).model_dump()
        
        from sanic.response import json
        return json(data)
    
    async def log_view(self, product, user):
        """Log view"""
        # Implement view logging logic
        pass
```

### UpdateModelMixin - Update Operation

**Route**: `PUT /api/products/<pk>` or `PATCH /api/products/<pk>`

**Functionality**: Update a resource

**Request Body**:

```json
{
  "name": "Updated product name",
  "price": 109.99
}
```

**Response**:

```json
{
  "id": 1,
  "name": "Updated product name",
  "price": 109.99,
  "updated_at": "2026-02-07 11:00:00"
}
```

**Customizing the update logic**:

```python
class ProductViewSet(BaseViewSet):
    async def perform_update(self, sch_model, orm_model):
        """Custom update logic
        
        Args:
            sch_model: Validated Pydantic Schema instance
            orm_model: ORM model instance to update
        
        Returns:
            Updated model instance
        """
        # Record changes
        old_price = orm_model.price
        
        # Update the object
        update_data = sch_model.model_dump(exclude_unset=True, exclude_none=True, exclude=["id"])
        for field, value in update_data.items():
            if hasattr(orm_model, field):
                setattr(orm_model, field, value)
        await orm_model.save()
        
        # If the price has changed, send a notification
        if old_price != orm_model.price:
            await self.notify_price_change(orm_model, old_price)
        
        return orm_model
    
    async def notify_price_change(self, product, old_price):
        """Notify about price change"""
        # Implement notification logic
        pass
```

### DestroyModelMixin - Delete Operation

**Route**: `DELETE /api/products/<pk>`

**Functionality**: Delete a resource

**Response**: HTTP 204 No Content

**Customizing the delete logic**:

```python
class ProductViewSet(BaseViewSet):
    async def perform_destroy(self, orm_model):
        """Custom delete logic
        
        Args:
            orm_model: ORM model instance to delete
        """
        # Soft delete
        orm_model.is_deleted = True
        await orm_model.save()
        
        # Or hard delete
        # await orm_model.delete()
        
        # Clean up related data
        await self.cleanup_related(orm_model)
    
    async def cleanup_related(self, product):
        """Clean up related data"""
        # Delete related images, comments, etc.
        pass
```

## Custom Actions - @action Decorator

The `@action` decorator is used to add custom actions to a ViewSet.

### Basic Usage

```python
from srf.views.decorators import action
from sanic.response import json

class ProductViewSet(BaseViewSet):
    @action(methods=["get"], detail=False, url_path="featured")
    async def list_featured(self, request):
        """Get featured products (collection-level action)"""
        products = await Product.filter(is_featured=True)
        schema = self.get_schema(request, is_safe=True)
        data = [schema.model_validate(p).model_dump() for p in products]
        return json({"results": data})
    
    @action(methods=["post"], detail=True, url_path="publish")
    async def publish(self, request, pk):
        """Publish product (detail-level action)"""
        product = await self.get_object(request, pk)
        product.is_published = True
        product.published_at = datetime.now()
        await product.save()
        
        return json({"message": "Product has been published"})
```

### Decorator Parameters

| Parameter | Type | Description | Default Value |
|---------|------|-------------|---------------|
| `methods` | list | List of HTTP methods | `["get"]` |
| `detail` | bool or None | Whether it is a detail-level action | `None` (treated as collection-level) |
| `url_path` | str | URL path | Method name |
| `url_name` | str | Route name | Method name |

### Collection-Level vs Detail-Level Actions

**Collection-Level Action** (`detail=False`):

- Does not require a pk parameter
- URL: `/api/products/featured`
- Example: Get a featured list, batch operations

```python
@action(detail=False, methods=["get"], url_path="featured")
async def featured(self, request):
    """Collection-level action"""
    # No need for pk
    pass
```

**Detail-Level Action** (`detail=True`):

- Requires a pk parameter
- URL: `/api/products/<pk>/publish`
- Example: Publish, activate, archive

```python
@action(detail=True, methods=["post"], url_path="publish")
async def publish(self, request, pk):
    """Detail-level action"""
    # Requires pk parameter
    product = await self.get_object(request, pk)
    pass
```

### Advanced Example

#### Refer to [View Decorators](viewset-actions.md) 

## ViewSet Configuration Options

### Permission Control

```python
from srf.permission.permission import IsAuthenticated, IsRoleAdminUser

class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsRoleAdminUser)
```

### Search Fields

```python
class ProductViewSet(BaseViewSet):
    search_fields = ["name", "description", "sku"]
```

### Filter Fields

```python
class ProductViewSet(BaseViewSet):
    filter_fields = {
        "category": "category_id",
        "min_price": "price__gte",
        "max_price": "price__lte",
        "is_published": "is_published",
    }
```

### Ordering Fields

```python
class ProductViewSet(BaseViewSet):
    ordering_fields = {
        "price": "price",
        "name": "name",
        "created": "created_at",
    }
```

### Filterer Classes

```python
from srf.filters.filter import SearchFilter, JsonLogicFilter, QueryParamFilter, OrderingFactory

class ProductViewSet(BaseViewSet):
    filter_class = [
            SearchFilter,
            JsonLogicFilter,
            QueryParamFilter,
            OrderingFactory,
        ]
```

## Complete Example

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.permission.permission import IsAuthenticated, IsRoleAdminUser
from sanic.response import json
from models import Product
from schemas import ProductSchemaReader, ProductSchemaWriter
from datetime import datetime

class ProductViewSet(BaseViewSet):
    """Product ViewSet - Complete Example"""
    
    # Permission configuration
    permission_classes = (IsAuthenticated,)
    
    # Search configuration
    search_fields = ["name", "description", "sku"]
    
    # Filter configuration
    filter_fields = {
        "category": "category_id",
        "min_price": "price__gte",
        "max_price": "price__lte",
    }
    
    # Ordering configuration
    ordering_fields = {
        "price": "price",
        "name": "name",
        "created": "created_at",
    }
    
    @property
    def queryset(self):
        """Returns the query set"""
        return Product.all().prefetch_related("category")
    
    def get_schema(self, request, *args, is_safe=False, **kwargs):
        """Returns Schema (list/retrieve defaults to is_safe=False, do not rely solely on is_safe)"""
        if request.method in ("GET", "HEAD", "OPTIONS") or is_safe:
            return ProductSchemaReader
        return ProductSchemaWriter
    
    # Custom create logic
    async def perform_create(self, sch_model):
        """Create product; use self.request when you need request"""
        data = sch_model.model_dump(exclude_unset=True)
        data["created_by"] = self.request.ctx.user.id
        return await Product.create(**data)
    
    # Custom update logic
    async def perform_update(self, sch_model, orm_model):
        """Update product"""
        update_data = sch_model.model_dump(exclude_unset=True, exclude_none=True, exclude=["id"])
        for field, value in update_data.items():
            if hasattr(orm_model, field):
                setattr(orm_model, field, value)
        orm_model.updated_by = self.request.ctx.user.id
        await orm_model.save()
        return orm_model
    
    # Collection-level custom action
    @action(methods=["get"], detail=False, url_path="featured")
    async def list_featured(self, request):
        """Get featured products"""
        products = await Product.filter(is_featured=True)
        schema = self.get_schema(request, is_safe=True)
        data = [schema.model_validate(p).model_dump() for p in products]
        return json({"results": data})
    
    # Detail-level custom action
    @action(methods=["post"], detail=True, url_path="publish")
    async def publish(self, request, pk):
        """Publish product"""
        product = await self.get_object(request, pk)
        
        if product.is_published:
            return json({"error": "Product already published"}, status=400)
        
        product.is_published = True
        product.published_at = datetime.now()
        await product.save()
        
        return json({"message": "Product has been published"})
```

## Best Practices

1. **Keep ViewSet simple**: Complex logic should be placed in the Service layer or Manager
2. **Use perform_* methods**: Override `perform_create`, `perform_update`, etc., to customize logic
3. **Use @action wisely**: Add custom endpoints for specific business operations
4. **Permission checks**: Always add permission checks for sensitive operations
5. **Exception handling**: Catch and handle possible exceptions
6. **Docstrings**: Add clear docstrings for methods

## Next Steps

- Learn [Routing](routing.md) to understand how to register ViewSet
- Read [Permissions](permissions.md) to understand the permission system
- View [Filtering](filtering.md) to understand data filtering