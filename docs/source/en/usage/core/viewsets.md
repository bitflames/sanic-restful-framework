# ViewSet

ViewSet is one of the core concepts in SRF, providing an elegant way to organize and manage RESTful API endpoints.

## What is a ViewSet?

A ViewSet is a class-based view that groups related API operations. A ViewSet typically corresponds to a resource type (such as product, order, etc.), and provides CRUD (Create, Read, Update, Delete) operations for that resource.

### Basic Concepts

- **Resource-Oriented**: Each ViewSet corresponds to a resource type
- **Automatic Routing**: Automatically generates RESTful routes
- **Mixin Pattern**: Combines functionality using Mixin
- **Flexible Extension**: Supports custom operations

## BaseViewSet

`BaseViewSet` is the base class for all ViewSets, which inherits all CRUD Mixins.

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
    
    def get_schema(self, request, is_safe=False):
        """Returns Schema
        
        Args:
            request: Request object
            is_safe: True indicates a read operation, False indicates a write operation
        """
        return ProductSchemaReader if is_safe else ProductSchemaWriter
```

### Required Properties and Methods

#### 1. `queryset` Property

Defines the data query set, which must return a Tortoise ORM query object.

```python
@property
def queryset(self):
    """Returns all products"""
    return Product.all()

# Query set with filtering
@property
def queryset(self):
    """Returns only published products"""
    return Product.filter(is_published=True)

# Query set with preloading
@property
def queryset(self):
    """Preloads related objects"""
    return Product.all().prefetch_related("category", "tags")
```

#### 2. `get_schema` Method

Returns the Pydantic Schema used for data validation and serialization.

```python
def get_schema(self, request, is_safe=False):
    """
    Different schemas may be used in the same request, such as controlling different fields for input or output.
    Use the unsafe schema for input.
    """
    return ProductSchemaReader if is_safe else ProductSchemaWriter
```

**Why separate read and write Schemas?**

- **Security**: Exclude read-only fields (such as id, created_at) during writes
- **Flexibility**: Include computed fields and related data during reads
- **Validation**: Apply stricter validation rules during writes

Example:

```python
from pydantic import BaseModel, Field
from typing import Optional

class ProductSchemaWriter(BaseModel):
    """Write Schema - used for creating and updating"""
    name: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = None
    category_id: int

class ProductSchemaReader(BaseModel):
    """Read Schema - used for serialization"""
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
- Get resource list
- Support pagination
- Support filtering and search
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

**Customize list method**:

```python
class ProductViewSet(BaseViewSet):
    async def list(self, request):
        """Custom list logic"""
        # Get query set
        queryset = self.queryset
        
        # Apply filters
        if "category" in request.args:
            category_id = request.args.get("category")
            queryset = queryset.filter(category_id=category_id)
        
        # Apply filter classes
        for filter_class in self.filter_class:
            queryset = await filter_class().filter_queryset(request, queryset)
        
        # Pagination
        from srf.paginator import PaginationHandler
        paginator = PaginationHandler.from_queryset(queryset, request)
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
  "description": "Product Description",
  "category_id": 1
}
```

**Response**:

```json
{
  "id": 1,
  "name": "New Product",
  "price": 99.99,
  "description": "Product Description",
  "category_id": 1,
  "created_at": "2026-02-07 10:00:00"
}
```

**Custom create logic**:

```python
class ProductViewSet(BaseViewSet):
    async def perform_create(self, request, schema):
        """Custom create logic
        
        Args:
            request: Request object
            schema: Validated Pydantic Schema instance
        
        Returns:
            Created model instance
        """
        # Add extra fields
        data = schema.dict()
        data["created_by"] = request.ctx.user.id
        
        # Create object
        obj = await Product.create(**data)
        
        # Perform other actions (e.g., send notification)
        await self.send_notification(obj)
        
        return obj
    
    async def send_notification(self, product):
        """Send notification"""
        # Implement notification logic
        pass
```

### RetrieveModelMixin - Detail Operation

**Route**: `GET /api/products/<pk>`

**Functionality**: Get a single resource

**Response**:

```json
{
  "id": 1,
  "name": "Product 1",
  "price": 99.99,
  "description": "Product Description",
  "category_id": 1,
  "category_name": "Electronics",
  "created_at": "2026-02-07 10:00:00"
}
```

**Customize retrieval logic**:

```python
class ProductViewSet(BaseViewSet):
    async def retrieve(self, request, pk):
        """Custom retrieval logic"""
        # Get object
        obj = await self.get_object(request, pk)
        
        # Log access
        await self.log_view(obj, request.ctx.user)
        
        # Serialize
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
  "name": "Updated Product Name",
  "price": 109.99
}
```

**Response**:

```json
{
  "id": 1,
  "name": "Updated Product Name",
  "price": 109.99,
  "updated_at": "2026-02-07 11:00:00"
}
```

**Custom update logic**:

```python
class ProductViewSet(BaseViewSet):
    async def perform_update(self, request, obj, schema):
        """Custom update logic
        
        Args:
            request: Request object
            obj: Model instance to update
            schema: Validated Pydantic Schema instance
        
        Returns:
            Updated model instance
        """
        # Record changes
        old_price = obj.price
        
        # Update object
        update_data = schema.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(obj, field, value)
        await obj.save()
        
        # If price changed, send notification
        if old_price != obj.price:
            await self.notify_price_change(obj, old_price)
        
        return obj
    
    async def notify_price_change(self, product, old_price):
        """Notify about price change"""
        # Implement notification logic
        pass
```

### DestroyModelMixin - Delete Operation

**Route**: `DELETE /api/products/<pk>`

**Functionality**: Delete a resource

**Response**: HTTP 204 No Content

**Custom delete logic**:

```python
class ProductViewSet(BaseViewSet):
    async def perform_destroy(self, request, obj):
        """Custom delete logic
        
        Args:
            request: Request object
            obj: Model instance to delete
        """
        # Soft delete
        obj.is_deleted = True
        await obj.save()
        
        # Or hard delete
        # await obj.delete()
        
        # Clean up related data
        await self.cleanup_related(obj)
    
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
|----------|------|-------------|---------------|
| `methods` | list | HTTP method list | `["get"]` |
| `detail` | bool | Whether it's a detail-level action | `False` |
| `url_path` | str | URL path | Method name |
| `url_name` | str | Route name | Method name |

### Collection-Level vs Detail-Level Actions

**Collection-Level Actions** (`detail=False`):

- No pk parameter needed
- URL: `/api/products/featured`
- Example: Get featured list, batch operations

```python
@action(methods=["get"], detail=False)
async def featured(self, request):
    """Collection-level action"""
    # No pk needed
    pass
```

**Detail-Level Actions** (`detail=True`):

- Requires pk parameter
- URL: `/api/products/<pk>/publish`
- Example: Publish, activate, archive

```python
@action(methods=["post"], detail=True)
async def publish(self, request, pk):
    """Detail-level action"""
    # Requires pk parameter
    product = await self.get_object(request, pk)
    pass
```

### Advanced Example

#### See [View Action](viewset-actions.md)

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

### Filter Class

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
    
    def get_schema(self, request, is_safe=False):
        """Returns Schema"""
        return ProductSchemaReader if is_safe else ProductSchemaWriter
    
    # Custom create logic
    async def perform_create(self, request, schema):
        """Create product"""
        data = schema.dict()
        data["created_by"] = request.ctx.user.id
        return await Product.create(**data)
    
    # Custom update logic
    async def perform_update(self, request, obj, schema):
        """Update product"""
        update_data = schema.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(obj, field, value)
        obj.updated_by = request.ctx.user.id
        await obj.save()
        return obj
    
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
            return json({"error": "Product is already published"}, status=400)
        
        product.is_published = True
        product.published_at = datetime.now()
        await product.save()
        
        return json({"message": "Product has been published"})
```

## Best Practices

1. **Keep ViewSet Simple**: Complex logic should be placed in Service layer or Manager
2. **Use perform_* methods**: Override `perform_create`, `perform_update`, etc., to customize logic
3. **Use @action wisely**: Add custom endpoints for specific business operations
4. **Permission Check**: Always add permission checks for sensitive operations
5. **Exception Handling**: Capture and handle possible exceptions
6. **Docstrings**: Add clear docstrings for methods

## Next Steps

- Learn [Routing](routing.md) to understand how to register ViewSet
- Read [Permissions](permissions.md) to understand the permission system
- View [Filtering](filtering.md) to understand data filtering