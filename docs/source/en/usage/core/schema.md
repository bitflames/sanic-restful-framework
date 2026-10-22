# Data Validation

SRF uses [Pydantic](https://docs.pydantic.dev/latest/) for data validation and serialization, providing powerful type safety and data validation capabilities. For detailed usage of [Pydantic](https://docs.pydantic.dev/latest/), please refer to the official documentation!

## Basic usage

### Defining a schema

```python
from pydantic import BaseModel, Field
from typing import Optional


class ProductSchema(BaseModel):
    name: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)
    description: Optional[str] = None
```

### Using it in a ViewSet

```python
from srf.views import BaseViewSet
from models import Product
from schemas import ProductSchema


class ProductViewSet(BaseViewSet):
    schema = ProductSchema

    @property
    def queryset(self):
        return Product.all()
```

## Field validation

### Numeric validation

```python
from pydantic import BaseModel, Field


class ProductSchema(BaseModel):
    price: float = Field(..., gt=0)           # Greater than 0
    stock: int = Field(..., ge=0)             # Greater than or equal to 0
    discount: float = Field(..., lt=100)      # Less than 100
    rating: int = Field(..., le=5)            # Less than or equal to 5
    quantity: int = Field(..., ge=1, le=1000) # Range: 1-1000
```

### String validation

```python
from pydantic import BaseModel, Field, EmailStr


class ProductSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    sku: str = Field(..., pattern=r"^[A-Z]{3}-\d{6}$")
    email: EmailStr  # Email validation
```

### Lists and sets

```python
from typing import List, Set
from pydantic import BaseModel, Field


class ProductSchema(BaseModel):
    tags: List[str] = Field(default_factory=list)
    images: List[str] = Field(..., min_length=1, max_length=10)
    categories: Set[int] = Field(default_factory=set)
```

## Custom validators

```python
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ProductSchema(BaseModel):
    name: str
    price: float
    discount_price: Optional[float] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        if not value.strip():
            raise ValueError("Product name cannot be empty")
        return value.strip()

    @field_validator("discount_price")
    @classmethod
    def validate_discount(cls, value, info):
        if value is not None and "price" in info.data:
            if value >= info.data["price"]:
                raise ValueError("The discount price must be less than the original price")
        return value
```

## Separating read and write schemas

### Writer schema (write)

Used for create and update operations:

```python
from pydantic import BaseModel, Field


class ProductSchemaWriter(BaseModel):
    name: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)
    category_id: int
```

### Reader schema (read)

Used for serializing returned data:

```python
from pydantic import BaseModel, ConfigDict, computed_field
from datetime import datetime


class ProductSchemaReader(BaseModel):
    id: int
    name: str
    price: float
    stock: int
    category_id: int
    created_at: datetime

    @computed_field
    @property
    def is_in_stock(self) -> bool:
        return self.stock > 0

    @computed_field
    @property
    def url(self) -> str:
        return f"/api/products/{self.id}"

    model_config = ConfigDict(from_attributes=True)
```

### Using it in a ViewSet

`BaseViewSet.as_view()` sets `self.request` and `self.action` before calling the action method,
so `get_schema()` does not need to accept a `request` parameter. Sanic's `request.is_safe` is a property
that indicates whether the current HTTP method is a safe method; it is suitable for choosing a schema based on read/write requests:

```python
from srf.views import BaseViewSet
from schemas import ProductSchemaReader, ProductSchemaWriter


class ProductViewSet(BaseViewSet):
    def get_schema(self):
        return ProductSchemaReader if self.request.is_safe else ProductSchemaWriter
```

To choose based on the ViewSet action name — for example, when a custom action needs its own schema — check
`self.action`:

```python
from srf.views import BaseViewSet
from schemas import ProductSchemaReader, ProductSchemaWriter


class ProductViewSet(BaseViewSet):
    def get_schema(self):
        if self.action in ("list", "retrieve"):
            return ProductSchemaReader
        return ProductSchemaWriter
```

You can also simply fix the schema class attribute as needed:

```python
from srf.views import BaseViewSet
from srf.permission import SafeMethodOnly
from schemas import ProductSchemaReader


class ProductViewSet(BaseViewSet):
    permission_classes = [
        SafeMethodOnly,
    ]
    schema = ProductSchemaReader
```

`is_safe` classifies by HTTP method; `self.action` classifies by the ViewSet method bound to the route. Which one to use
depends on the API design. The built-in `create` / `update` use the same schema returned by `get_schema()` to validate input and serialize the response.

!!! warning "strict=True and partial updates"
    The built-in `create` / `update` use `schema.model_validate(request.json, strict=True)`:

    - Strings in the request body are not automatically converted to types such as `datetime` / `date` / `Decimal`;
      if the write schema contains such fields, clients must send values that pass strict validation (usually you should use
      `str` or `float` fields instead, or override `create` / `update`).
    - `update` validates the request body against the full schema, and `PUT` and `PATCH` behave the same; there is currently no
      true partial update. The request body must satisfy the schema's required fields.

## Data types

### Basic types

```python
from pydantic import BaseModel
from typing import Optional


class ExampleSchema(BaseModel):
    name: str           # String
    age: int            # Integer
    price: float        # Float
    is_active: bool     # Boolean
    description: Optional[str] = None  # Optional
```

### Dates and times

```python
from datetime import date, datetime, time


class EventSchema(BaseModel):
    event_date: date         # Date
    created_at: datetime     # Datetime
    start_time: time         # Time
```

### Advanced types

```python
from pydantic import EmailStr, HttpUrl
from decimal import Decimal


class AdvancedSchema(BaseModel):
    email: EmailStr       # Email
    website: HttpUrl      # URL
    price: Decimal        # Precise decimal number
```

### Enum types

```python
from enum import Enum
from pydantic import BaseModel
from srf.views import BaseViewSet
from models import Product


class ProductStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ProductSchema(BaseModel):
    name: str
    status: ProductStatus = ProductStatus.DRAFT
```

## Validation error responses

When Pydantic validation fails in `create` / `update`, `as_view()` converts it into
`PydanticValidationException` (422). The response body returned by Sanic looks like:

```json
{
  "description": "Unprocessable Entity",
  "status": 422,
  "message": "1 validation error for ProductSchemaWriter\nprice\n  Input should be greater than 0 ..."
}
```

`message` is `str(ValidationError)`, not a structured list of fields. If you need per-field errors,
register a global exception handler or override `create` / `update` and call `error.errors()` yourself.

## Complete example

```python
from pydantic import BaseModel, Field, field_validator, computed_field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum
from srf.views import BaseViewSet
from models import Product


class ProductStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class ProductSchemaWriter(BaseModel):
    """Write schema"""

    name: str = Field(..., min_length=1, max_length=200)
    sku: str = Field(..., pattern=r"^[A-Z]{3}-\d{6}$")
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)
    category_id: int
    tags: List[str] = Field(default_factory=list)
    status: ProductStatus = ProductStatus.DRAFT

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        if not value.strip():
            raise ValueError("Product name cannot be empty")
        return value.strip()


class ProductSchemaReader(BaseModel):
    """Read schema"""

    id: int
    name: str
    sku: str
    price: float
    stock: int
    category_id: int
    tags: List[str]
    status: ProductStatus
    created_at: datetime

    @computed_field
    @property
    def is_in_stock(self) -> bool:
        return self.stock > 0

    model_config = ConfigDict(from_attributes=True)


# Using it in a ViewSet
class ProductViewSet(BaseViewSet):
    @property
    def queryset(self):
        return Product.all()

    def get_schema(self):
        # Choose the read/write schema by HTTP method here; see above for the complete selection approach.
        return ProductSchemaReader if self.request.is_safe else ProductSchemaWriter
```

## Best practices

1. **Use type annotations**: provide complete type information
2. **Separate read and write schemas**: define different schemas for different operations
3. **Add validation rules**: use Field and validators to ensure data validity
4. **Use enums**: use enum types for fixed options
5. **Computed fields**: use `@computed_field` to add derived fields
6. **Friendly errors**: return clear error messages in validators

## Next steps

- Study [Views](viewsets.md) to learn how to use schemas in ViewSets
- Read [Authentication](authentication.md) to learn about user data validation
- See [Filtering](filtering.md) to learn about query parameter validation
