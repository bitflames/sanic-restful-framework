# Data Validation

SRF uses [Pydantic](https://docs.pydantic.dev/latest/) for data validation and serialization, providing strong type safety and data validation capabilities. For detailed usage of [Pydantic](https://docs.pydantic.dev/latest/), please refer to the official documentation!

## Basic Usage

### Define Schema

```python
from pydantic import BaseModel, Field
from typing import Optional

class ProductSchema(BaseModel):
    name: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)
    description: Optional[str] = None
```

### Use in ViewSet

```python
from srf.views import BaseViewSet
from pydantic import BaseModel

class ProductViewSet(BaseViewSet):
    schema: BaseModel = ProductSchema

    @property
    def queryset(self):
        return Product.all()
```

## Field Validation

### Numeric Validation

```python
class ProductSchema(BaseModel):
    price: float = Field(..., gt=0)           # greater than 0
    stock: int = Field(..., ge=0)             # greater than or equal to 0
    discount: float = Field(..., lt=100)      # less than 100
    rating: int = Field(..., le=5)            # less than or equal to 5
    quantity: int = Field(..., ge=1, le=1000) # range: 1-1000
```

### String Validation

```python
from pydantic import BaseModel, Field, EmailStr

class ProductSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    sku: str = Field(..., pattern=r'^[A-Z]{3}-\d{6}$')
    email: EmailStr  # email validation
```

### Lists and Sets

```python
from typing import List, Set

class ProductSchema(BaseModel):
    tags: List[str] = Field(default=[])
    images: List[str] = Field(..., min_length=1, max_length=10)
    categories: Set[int] = Field(default=set())
```

## Custom Validators

```python
from pydantic import BaseModel, field_validator

class ProductSchema(BaseModel):
    name: str
    price: float
    discount_price: Optional[float] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, value):
        if not value.strip():
            raise ValueError('Product name cannot be empty')
        return value.strip()
    
    @field_validator('discount_price')
    @classmethod
    def validate_discount(cls, value, info):
        if value is not None and 'price' in info.data:
            if value >= info.data['price']:
                raise ValueError('Discount price must be less than original price')
        return value
```

## Separating Read and Write Schemas

### Writer Schema (Writing)

Used for create and update operations:

```python
class ProductSchemaWriter(BaseModel):
    name: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)
    category_id: int
```

### Reader Schema (Reading)

Used for serializing returned data:

```python
from pydantic import computed_field
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
    
    class Config:
        from_attributes = True
```

### Use in ViewSet

```python
class ProductViewSet(BaseViewSet):
    def get_schema(self, request, is_safe=False):
        """
        is_safe=True: Read operation (GET)
        is_safe=False: Write operation (POST/PUT/PATCH)
        """
        return ProductSchemaReader if is_safe else ProductSchemaWriter
```

## Data Types

### Basic Types

```python
from pydantic import BaseModel
from typing import Optional

class ExampleSchema(BaseModel):
    name: str           # string
    age: int            # integer
    price: float        # float
    is_active: bool     # boolean
    description: Optional[str] = None  # optional
```

### Date and Time

```python
from datetime import date, datetime, time

class EventSchema(BaseModel):
    event_date: date         # date
    created_at: datetime     # date and time
    start_time: time         # time
```

### Advanced Types

```python
from pydantic import EmailStr, HttpUrl
from decimal import Decimal

class AdvancedSchema(BaseModel):
    email: EmailStr       # email
    website: HttpUrl      # URL
    price: Decimal        # precise decimal number
```

### Enumerated Types

```python
from enum import Enum

class ProductStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class ProductSchema(BaseModel):
    name: str
    status: ProductStatus = ProductStatus.DRAFT
```

## Validation Error Response

When data validation fails, return 422 error:

```json
{
  "errors": [
    {
      "type": "string_too_short",
      "loc": ["name"],
      "msg": "String should have at least 1 character"
    },
    {
      "type": "greater_than",
      "loc": ["price"],
      "msg": "Input should be greater than 0"
    }
  ]
}
```

## Complete Example

```python
from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ProductStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"

class ProductSchemaWriter(BaseModel):
    """Writer Schema"""
    name: str = Field(..., min_length=1, max_length=200)
    sku: str = Field(..., pattern=r'^[A-Z]{3}-\d{6}$')
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)
    category_id: int
    tags: List[str] = Field(default=[])
    status: ProductStatus = ProductStatus.DRAFT
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, value):
        if not value.strip():
            raise ValueError('Product name cannot be empty')
        return value.strip()

class ProductSchemaReader(BaseModel):
    """Reader Schema"""
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
    
    class Config:
        from_attributes = True

# Use in ViewSet
class ProductViewSet(BaseViewSet):
    @property
    def queryset(self):
        return Product.all()
    
    def get_schema(self, request, is_safe=False):
        return ProductSchemaReader if is_safe else ProductSchemaWriter
```

## Best Practices

1. **Use Type Annotations**: Provide complete type information
2. **Separate Read and Write Schemas**: Define different schemas for different operations
3. **Add Validation Rules**: Use Field and validator to ensure data validity
4. **Use Enums**: Use enum types for fixed options
5. **Computed Fields**: Use `@computed_field` to add derived fields
6. **Friendly Errors**: Return clear error messages in validators

## Next Steps

- Learn about [Views](viewsets.md) to understand how to use Schemas in ViewSets
- Read about [Authentication](authentication.md) to learn about user data validation
- View [Filtering](filtering.md) to learn about query parameter validation