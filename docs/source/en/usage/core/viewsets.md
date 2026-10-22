# Views (ViewSet)

ViewSet is one of the core concepts of SRF. It provides an elegant way to organize and manage RESTful API endpoints.

## What is a ViewSet?

A ViewSet is a class-based view that groups related API operations together. A ViewSet usually corresponds to one resource type (such as products or orders) and provides CRUD (Create, Read, Update, Delete) operations for that resource.

### Basic concepts

- **Resource-oriented**: Each ViewSet corresponds to one resource type
- **Automatic routing**: RESTful routes are generated automatically
- **Mixin pattern**: Functionality is composed through mixins
- **Flexible extension**: Custom actions are supported

## BaseViewSet

`BaseViewSet` is the base class for all ViewSets and inherits all CRUD mixins.
Code blocks below that do not repeat imports are method snippets to add to an existing ViewSet and continue to use
the `BaseViewSet`, `Product`, and schema imports from the basic usage section.

### Basic usage

```python
from srf.views import BaseViewSet
from models import Product
from schemas import ProductSchemaReader, ProductSchemaWriter


class ProductViewSet(BaseViewSet):
    """Product ViewSet"""

    @property
    def queryset(self):
        """Return the queryset"""
        return Product.all()

    def get_schema(self):
        """Choose the read/write schema by HTTP method; self.request is set by as_view."""
        return ProductSchemaReader if self.request.is_safe else ProductSchemaWriter
```

### Required attributes and methods

#### 1. `queryset` / `get_queryset`

Provides the Tortoise ORM queryset. To limit the data scope per request, prefer overriding `get_queryset()`; you can also set a class attribute or `@property` named `queryset`, which the default `get_queryset()` reads (cloning it with `.all()` if it is a `QuerySet`).

`list()` uses `filter_queryset(self.get_queryset())`. `get_object()` and `perform_create()` also go through `get_queryset()`.

```python
# Class attribute
queryset = Product.all()


# Or a property (still read by get_queryset)
@property
def queryset(self):
    """Return only published products"""
    return Product.filter(is_published=True)


# Or override get_queryset to limit the scope per request
def get_queryset(self):
    return Product.filter(owner_id=self.request.ctx.user.id).prefetch_related("category", "tags")
```

#### 2. The `get_schema` method

Returns the Pydantic schema used for validation and serialization.

To always use one schema, just set the `schema` class attribute. To choose based on the request or action, override
`get_schema()`; see [Schema selection](schema.md) for how to choose and how the built-in `create` / `update`
use the returned schema.

**Why separate read and write schemas?**

- **Security**: exclude read-only fields on write (such as id, created_at)
- **Flexibility**: include computed fields and related data on read
- **Validation**: use stricter validation rules on write

Example:

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class ProductSchemaWriter(BaseModel):
    """Write schema - used for create and update"""

    name: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = None
    category_id: int


class ProductSchemaReader(BaseModel):
    """Read schema - used for serialization"""

    id: int
    name: str
    price: float
    description: Optional[str]
    category_id: int
    category_name: str  # Additional related field
    created_at: str

    model_config = ConfigDict(from_attributes=True)
```

## CRUD operations

BaseViewSet provides standard CRUD operations through mixins.

### ListModelMixin - list operation

**Route**: `GET /api/products`

**Features**:

- Get a resource list
- Supports pagination
- Supports sorting

**Response format**:

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

**Custom list method**:

```python
from sanic.response import json
from srf.paginator import PageNumberPagination


class ProductViewSet(BaseViewSet):
    async def list(self, request):
        """Custom list logic"""
        # Get the queryset
        queryset = self.queryset

        # Apply filtering
        if "category" in request.args:
            category_id = request.args.get("category")
            queryset = queryset.filter(category_id=category_id)

        # Apply filter classes
        for filter_class in self.filter_class:
            queryset = filter_class(self).filter_queryset(request, queryset)

        paginator = PageNumberPagination.from_queryset(queryset, request)
        schema = self.get_schema()
        result = await paginator.to_dict(schema)

        return json(result)
```

### CreateModelMixin - create operation

**Route**: `POST /api/products`

**Feature**: Create a new resource

**Request body**:

```json
{
  "name": "New product",
  "price": 99.99,
  "description": "Product description",
  "category_id": 1
}
```

**Response**:

```json
{
  "id": 1,
  "name": "New product",
  "price": 99.99,
  "description": "Product description",
  "category_id": 1,
  "created_at": "2026-02-07 10:00:00"
}
```

**Custom create logic**:

```python
class ProductViewSet(BaseViewSet):
    async def perform_create(self, sch_model):
        """Custom create logic

        Args:
            sch_model: The validated Pydantic schema instance

        Use self.request when the request is needed (as_view assigns it).
        """
        data = sch_model.model_dump(exclude_unset=True)
        data["created_by"] = self.request.ctx.user.id

        obj = await Product.create(**data)
        await self.send_notification(obj)
        return obj

    async def send_notification(self, product):
        """Send a notification"""
        # Implement notification logic
        pass
```

### RetrieveModelMixin - retrieve operation

**Route**: `GET /api/products/<pk>`

**Feature**: Get a single resource

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

**Custom retrieve logic**:

```python
class ProductViewSet(BaseViewSet):
    async def retrieve(self, request, pk):
        """Custom retrieve logic"""
        # Get the object
        obj = await self.get_object(pk)

        # Log the access
        await self.log_view(obj, request.ctx.user)

        # Serialize
        schema = self.get_schema()
        data = schema.model_validate(obj).model_dump()

        from sanic.response import json

        return json(data)

    async def log_view(self, product, user):
        """Log a view"""
        # Implement view logging logic
        pass
```

### UpdateModelMixin - update operation

**Route**: `PUT /api/products/<pk>` or `PATCH /api/products/<pk>`

**Feature**: Update a resource

**Request body**:

```json
{
  "name": "Updated product name",
  "price": 109.99,
  "description": "Product description",
  "category_id": 1
}
```

!!! warning "This is not a partial update currently"
    `update()` validates the full request body with the schema returned by `get_schema()` using `strict=True`,
    and `PUT` and `PATCH` map to the same method. The request body must satisfy the schema's required fields;
    `exclude_unset=True` in `perform_update()` only controls "which validated fields are written back to the database",
    and does not mean required fields can be omitted.

**Response**:

```json
{
  "id": 1,
  "name": "Updated product name",
  "price": 109.99,
  "updated_at": "2026-02-07 11:00:00"
}
```

**Custom update logic**:

```python
class ProductViewSet(BaseViewSet):
    async def perform_update(self, sch_model, orm_model):
        """Custom update logic
        
        Args:
            sch_model: The validated Pydantic schema instance
            orm_model: The ORM model instance to update
        
        Returns:
            The updated model instance
        """
        # Record the change
        old_price = orm_model.price
        
        # Update the object
        update_data = sch_model.model_dump(exclude_unset=True, exclude_none=True, exclude=["id"])
        for field, value in update_data.items():
            if hasattr(orm_model, field):
                setattr(orm_model, field, value)
        await orm_model.save()
        
        # If the price changed, send a notification
        if old_price != orm_model.price:
            await self.notify_price_change(orm_model, old_price)
        
        return orm_model
    
    async def notify_price_change(self, product, old_price):
        """Notify about a price change"""
        # Implement notification logic
        pass
```

### DestroyModelMixin - delete operation

**Route**: `DELETE /api/products/<pk>`

**Feature**: Delete a resource

**Response**: HTTP 204 No Content

**Custom delete logic**:

```python
class ProductViewSet(BaseViewSet):
    async def perform_destroy(self, orm_model):
        """Custom delete logic
        
        Args:
            orm_model: The ORM model instance to delete
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

## Custom actions - the @action decorator

`@action` is used to add endpoints beyond CRUD: `detail=False` registers
`/api/products/<url_path>`, while `detail=True` registers `/api/products/<pk>/<url_path>`.
See [ViewSet Decorators](viewset-actions.md) for complete details on parameters, examples, permission checks, and more.

## ViewSet configuration options

### Permission control

```python
from srf.permission.permission import IsAuthenticated, SuperuserOnly


class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, SuperuserOnly)
```

### Search fields

All three field configurations default to an empty list `[]` and also accept dictionaries. Field names in a list map directly to same-named ORM fields; dictionary values specify the ORM field name, while the keys of `filter_fields` and `ordering_fields` are used as query parameter names and ordering names respectively. See [Filtering](filtering.md) for details.

### Filter fields

```python
class ProductViewSet(BaseViewSet):
    filter_fields = {
        "category": "category_id",
        "min_price": "price__gte",
        "max_price": "price__lte",
        "is_published": "is_published",
    }
```

### Ordering fields

```python
class ProductViewSet(BaseViewSet):
    ordering_fields = {
        "price": "price",
        "name": "name",
        "created": "created_at",
    }
```

### Filter classes

```python
class ProductViewSet(BaseViewSet):
    filter_class = [
        SearchFilter,
        QueryParamFilter,
        OrderingFactory,
    ]
```

## Complete example

```python
from srf.views import BaseViewSet
from srf.permission.permission import IsAuthenticated
from models import Product
from schemas import ProductSchemaReader, ProductSchemaWriter


class ProductViewSet(BaseViewSet):
    """Product ViewSet - complete example"""

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
        """Return the queryset"""
        return Product.all().prefetch_related("category")

    def get_schema(self):
        """Choose the schema by HTTP method."""
        return ProductSchemaReader if self.request.is_safe else ProductSchemaWriter

    # Custom create logic
    async def perform_create(self, sch_model):
        """Create a product; use self.request when the request is needed"""
        data = sch_model.model_dump(exclude_unset=True)
        data["created_by"] = self.request.ctx.user.id
        return await Product.create(**data)

    # Custom update logic
    async def perform_update(self, sch_model, orm_model):
        """Update a product"""
        update_data = sch_model.model_dump(exclude_unset=True, exclude_none=True, exclude=["id"])
        for field, value in update_data.items():
            if hasattr(orm_model, field):
                setattr(orm_model, field, value)
        orm_model.updated_by = self.request.ctx.user.id
        await orm_model.save()
        return orm_model
```

## Best practices

1. **Keep ViewSets concise**: complex logic should live in a service layer or manager
2. **Use perform_* methods**: override `perform_create`, `perform_update`, and similar methods for custom logic
3. **Use @action sensibly**: add custom endpoints for specific business operations
4. **Permission checks**: always add permission checks for sensitive operations
5. **Exception handling**: catch and handle possible exceptions
6. **Docstrings**: add clear docstrings to methods

## Next steps

- See [Routing](routing.md) to learn how to register ViewSets
- Read [Permissions](permissions.md) to learn about the permission system
- See [Filtering](filtering.md) to learn about data filtering
