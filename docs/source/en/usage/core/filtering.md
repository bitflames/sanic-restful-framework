# Filtering

SRF provides a powerful and flexible filtering system that supports search, complex queries, and sorting.

## Filter Overview

The filtering system allows clients to filter and sort data through query parameters, offering several built-in filters:

- **SearchFilter**: Full-text search
- **JsonLogicFilter**: Complex JSON Logic queries
- **QueryParamFilter**: Exact filtering based on query parameters
- **OrderingFactory**: Sorting functionality

## BaseFilter

All filters inherit from the `BaseFilter` abstract base class:

```python
from srf.filters.filter import BaseFilter

class BaseFilter:
    """Base filter class"""
    
    async def filter_queryset(self, request, queryset):
        """Filter the query set
        
        Args:
            request: Request object
            queryset: Tortoise ORM query set
        
        Returns:
            Filtered query set
        """
        raise NotImplementedError
```

## SearchFilter - Full-text Search

`SearchFilter` provides full-text search functionality, searching for keywords in specified fields.

### Basic Usage

```python
from srf.views import BaseViewSet

class ProductViewSet(BaseViewSet):
    # Define searchable fields
    search_fields = ["name", "description", "sku"]
    
    @property
    def queryset(self):
        return Product.all()
```

### Request Examples

```bash
# Search for products with "phone" in name, description, or SKU
GET /api/products?search=phone

# Search for multiple keywords (AND relationship)
GET /api/products?search=apple phone
```

### Search Logic

- **Multiple Keywords**: Separated by spaces, relationship is AND
- **Multiple Fields**: Match in any field, relationship is OR
- **Case-insensitive**: Automatically converted to lowercase for search

Example: `search=apple phone`

```python
# Translated into query:
Q(name__icontains="apple") | Q(description__icontains="apple") | Q(sku__icontains="apple")
AND
Q(name__icontains="phone") | Q(description__icontains="phone") | Q(sku__icontains="phone")
```

### Customizing Search Fields

```python
class ProductViewSet(BaseViewSet):
    search_fields = [
        "name",           # Product name
        "description",    # Description
        "sku",           # SKU
        "brand__name",   # Brand name (related field)
    ]
```

## QueryParamFilter - Exact Filtering

`QueryParamFilter` performs exact match filtering based on query parameters.

### Basic Usage

```python
class ProductViewSet(BaseViewSet):
    # Define filter field mappings
    filter_fields = {
        "category": "category_id",      # Category ID
        "brand": "brand_id",             # Brand ID
        "is_active": "is_active",        # Whether active
        "min_price": "price__gte",       # Minimum price (greater than or equal to)
        "max_price": "price__lte",       # Maximum price (less than or equal to)
    }
```

### Request Examples

```bash
# Filter by category
GET /api/products?category=1

# Price range filter
GET /api/products?min_price=100&max_price=500

# Combined multiple conditions
GET /api/products?category=1&brand=2&min_price=100&is_active=true
```

### Supported Lookup Types

| Parameter Suffix | Tortoise Lookup | Description | Example |
|------------------|------------------|-------------|---------|
| None | `=` | Exact match | `category=1` |
| `__gte` | `>=` | Greater than or equal to | `min_price__gte=100` |
| `__lte` | `<=` | Less than or equal to | `max_price__lte=500` |
| `__gt` | `>` | Greater than | `stock__gt=0` |
| `__lt` | `<` | Less than | `price__lt=1000` |
| `__in` | `IN` | Contains | `id__in=1,2,3` |
| `__contains` | `LIKE %x%` | Contains | `name__contains=phone` |
| `__icontains` | `ILIKE %x%` | Case-insensitive contains | `name__icontains=Phone` |
| `__startswith` | `LIKE x%` | Starts with | `sku__startswith=PRD` |

### Example

```python
class ProductViewSet(BaseViewSet):
    filter_fields = {
        # Exact match
        "category": "category_id",
        "status": "status",
        
        # Range query
        "min_price": "price__gte",
        "max_price": "price__lte",
        "min_stock": "stock__gt",
        
        # Contains query
        "name_contains": "name__icontains",
        "sku_starts": "sku__startswith",
        
        # IN query
        "ids": "id__in",
        "categories": "category_id__in",
    }
```

Request:

```bash
# Multiple IDs
GET /api/products?ids=1,2,3,4,5

# Multiple categories
GET /api/products?categories=1,2,3

# Name contains
GET /api/products?name_contains=phone

# SKU starts with
GET /api/products?sku_starts=PRD
```

## JsonLogicFilter - Complex Queries

`JsonLogicFilter` supports complex queries using JSON Logic expressions.

### Basic Usage

```python
class ProductViewSet(BaseViewSet):
    filter_fields = {
        "category": "category_id",
        "price": "price",
        "stock": "stock",
        "is_active": "is_active",
    }
```

### Request Examples

Use the `filter` parameter to pass a JSON Logic expression:

```bash
# Price greater than 100
GET /api/products?filter={"price": {">": 100}}

# Price between 100 and 500
GET /api/products?filter={"and": [{"price": {">=": 100}}, {"price": {"<=": 500}}]}

# Category 1 and has stock
GET /api/products?filter={"and": [{"category": 1}, {"stock": {">": 0}}]}
```

### Supported Operators

#### Comparison Operators

```bash
# Equal
{"price": 100}
{"price": {"==": 100}}

# Not equal
{"status": {"!=": "draft"}}

# Greater than
{"price": {">": 100}}

# Greater than or equal to
{"price": {">=": 100}}

# Less than
{"price": {"<": 500}}

# Less than or equal to
{"price": {"<=": 500}}
```

#### IN Operator

```bash
# In list
{"category": {"in": [1, 2, 3]}}

# Not in list
{"status": {"not in": ["draft", "archived"]}}
```

#### LIKE Operator

```bash
# Fuzzy match
{"name": {"like": "%phone%"}}
```

#### Logical Operators

```bash
# AND (all conditions satisfied)
{"and": [
  {"price": {">=": 100}},
  {"price": {"<=": 500}},
  {"is_active": true}
]}

# OR (any condition satisfied)
{"or": [
  {"category": 1},
  {"category": 2}
]}

# NOT (condition not satisfied)
{"not": {"status": "archived"}}
```

### Complex Query Examples

#### Example 1: Price range and category

```json
{
  "and": [
    {"category": {"in": [1, 2]}},
    {"price": {">=": 100}},
    {"price": {"<=": 500}},
    {"stock": {">": 0}}
  ]
}
```

#### Example 2: Multiple OR conditions

```json
{
  "or": [
    {"category": 1},
    {
      "and": [
        {"category": 2},
        {"price": {"<": 200}}
      ]
    }
  ]
}
```

#### Example 3: NOT condition

```json
{
  "and": [
    {"is_active": true},
    {"not": {"status": {"in": ["draft", "archived"]}}}
  ]
}
```

### Python Client Example

```python
import json
import requests

# Build filter conditions
filter_logic = {
    "and": [
        {"category": {"in": [1, 2, 3]}},
        {"price": {">=": 100}},
        {"price": {"<=": 500}},
        {"is_active": True}
    ]
}

# Send request
response = requests.get(
    "http://localhost:8000/api/products",
    params={"filter": json.dumps(filter_logic)}
)

products = response.json()
```

## OrderingFactory - Sorting

`OrderingFactory` provides sorting functionality.

### Basic Usage

```python
class ProductViewSet(BaseViewSet):
    ordering_fields = {
        "price": "price",
        "name": "name",
        "created": "created_at",
        "stock": "stock",
    }
```

### Request Examples

```bash
# Sort by price ascending
GET /api/products?sort=price

# Sort by price descending (add minus sign)
GET /api/products?sort=-price

# Multi-field sorting
GET /api/products?sort=-price,name

# First sort by category descending, then by price ascending
GET /api/products?sort=-category,price
```

### Sorting Rules

- **Ascending**: Field name
- **Descending**: Add `-` before the field name
- **Multi-field**: Separate with commas

## Using Filters Together

All filters can be used together:

```python
class ProductViewSet(BaseViewSet):
    # Define search fields
    search_fields = ["name", "description"]
    
    # Define filter fields
    filter_fields = {
        "category": "category_id",
        "min_price": "price__gte",
        "max_price": "price__lte",
        "is_active": "is_active",
    }
    
    # Define sort fields
    ordering_fields = {
        "price": "price",
        "name": "name",
        "created": "created_at",
    }
```

### Combined Query Example

```bash
# Search + Filter + Sort + Pagination
GET /api/products?search=phone&category=1&min_price=1000&max_price=5000&sort=-price&page=1&page_size=20
```

Execution order:

1. Apply search (SearchFilter)
2. Apply exact filter (QueryParamFilter)
3. Apply JSON filter (JsonLogicFilter)
4. Apply sorting (OrderingFactory)
5. Apply pagination (PaginationHandler)

## Custom Filters

### Creating a Custom Filter

```python
from srf.filters.filter import BaseFilter
from tortoise.expressions import Q

class PriceRangeFilter(BaseFilter):
    """Price range filter"""
    
    async def filter_queryset(self, request, queryset):
        """Filter by price range"""
        price_range = request.args.get('price_range')
        
        if not price_range:
            return queryset
        
        # Parse price range: "100-500"
        try:
            min_price, max_price = map(float, price_range.split('-'))
            queryset = queryset.filter(
                Q(price__gte=min_price) & Q(price__lte=max_price)
            )
        except ValueError:
            pass
        
        return queryset
```

### Using the Custom Filter

```python
from filters import PriceRangeFilter

class ProductViewSet(BaseViewSet):
    filter_class = [
        PriceRangeFilter,
        SearchFilter,
        QueryParamFilter,
        OrderingFactory,
    ]
```

Request:

```bash
GET /api/products?price_range=100-500
```

## Complete Example

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.filters.filter import SearchFilter, JsonLogicFilter, QueryParamFilter, OrderingFactory
from sanic.response import json
from models import Product
from schemas import ProductSchemaReader, ProductSchemaWriter

class ProductViewSet(BaseViewSet):
    """Product ViewSet - Complete filtering example"""
    
    # Search fields
    search_fields = [
        "name",
        "description",
        "sku",
        "brand__name",       # Related field
        "category__name",    # Related field
    ]
    
    # Filter fields
    filter_fields = {
        # Exact match
        "category": "category_id",
        "brand": "brand_id",
        "status": "status",
        "is_active": "is_active",
        
        # Range query
        "min_price": "price__gte",
        "max_price": "price__lte",
        "min_stock": "stock__gte",
        
        # Fuzzy query
        "name_contains": "name__icontains",
        
        # IN query
        "ids": "id__in",
        "categories": "category_id__in",
    }
    
    # Sort fields
    ordering_fields = {
        "price": "price",
        "name": "name",
        "stock": "stock",
        "created": "created_at",
        "updated": "updated_at",
    }
    
    # Specify the filter classes to use
    filter_class = [
        SearchFilter,
        JsonLogicFilter,
        QueryParamFilter,
        OrderingFactory,
    ]
    
    @property
    def queryset(self):
        return Product.all().prefetch_related("category", "brand")
    
    def get_schema(self, request, is_safe=False):
        return ProductSchemaReader if is_safe else ProductSchemaWriter
    
    @action(methods=["get"], detail=False, url_path="popular")
    async def popular(self, request):
        """Popular products (custom filter)"""
        # Get query set
        queryset = Product.filter(is_active=True, stock__gt=0)
        
        # Apply search and sorting
        for filter_class in [SearchFilter, OrderingFactory]:
            queryset = await filter_class().filter_queryset(request, queryset)
        
        # Limit the number
        queryset = queryset.limit(10)
        
        # Serialize
        products = await queryset
        schema = self.get_schema(request, is_safe=True)
        results = [schema.model_validate(p).model_dump() for p in products]
        
        return json({"results": results})
```

### Query Examples

```bash
# 1. Basic search
GET /api/products?search=phone

# 2. Search + Category filter
GET /api/products?search=phone&category=1

# 3. Price range + Sort
GET /api/products?min_price=1000&max_price=5000&sort=-price

# 4. Complex filter (JSON Logic)
GET /api/products?filter={"and":[{"category":{"in":[1,2]}},{"price":{">=":1000}}]}

# 5. Combined query
GET /api/products?search=apple&category=1&min_price=3000&sort=-created&page=1&page_size=20

# 6. Multiple categories
GET /api/products?categories=1,2,3&sort=price

# 7. Name contains
GET /api/products?name_contains=iPhone&is_active=true

# 8. Multiple IDs
GET /api/products?ids=1,2,3,4,5
```

## Performance Optimization

### 1. Add Database Indexes

Add indexes to commonly filtered and sorted fields:

```python
class Product(Model):
    category_id = fields.IntField(index=True)
    price = fields.DecimalField(max_digits=10, decimal_places=2, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    is_active = fields.BooleanField(default=True, index=True)
```

### 2. Use Covering Indexes

Create composite indexes for common query combinations:

```python
class Meta:
    indexes = [
        ("category_id", "is_active"),
        ("price", "created_at"),
    ]
```

### 3. Optimize Related Queries

Use `prefetch_related` to optimize related field searches:

```python
@property
def queryset(self):
    return Product.all().prefetch_related("category", "brand", "tags")
```

### 4. Limit Search Fields

Only enable search on necessary fields to avoid full table scans:

```python
# Not recommended: search too many fields
search_fields = ["name", "description", "content", "notes", "metadata"]

# Recommended: search only key fields
search_fields = ["name", "sku"]
```

## Best Practices

1. **Choose Filter Fields Wisely**: Expose only necessary filter fields
2. **Add Database Indexes**: Add indexes to filter and sort fields
3. **Limit Search Fields**: Avoid searching on large text fields
4. **Validate Input**: Validate the validity of filter parameters
5. **Use JSON Logic Carefully**: Complex queries may affect performance
6. **Combine Filters**: Make full use of multiple filters
7. **Document Filter Parameters**: Document supported filter parameters in API documentation

## Common Issues

### How to Implement OR Query?

Use the JSON Logic Filter:

```bash
GET /api/products?filter={"or":[{"category":1},{"category":2}]}
```

### How to Implement Date Range Query?

```python
class ProductViewSet(BaseViewSet):
    filter_fields = {
        "start_date": "created_at__gte",
        "end_date": "created_at__lte",
    }
```

```bash
GET /api/products?start_date=2026-01-01&end_date=2026-01-31
```

### How to Implement Fuzzy Search?

Use SearchFilter or QueryParamFilter:

```python
# Method 1: SearchFilter
search_fields = ["name", "description"]

# Method 2: QueryParamFilter
filter_fields = {
    "name": "name__icontains",
}
```

### How to Disable a Specific Filter?

```python
class ProductViewSet(BaseViewSet):
    # Use only some filters
    filter_class = [
        SearchFilter,
        QueryParamFilter,
        # Do not use JsonLogicFilter and OrderingFactory
    ]
```

## Next Steps

- Learn [Pagination](pagination.md) to understand how to combine with filtering
- Read [Views](viewsets.md) to learn about the full functionality of ViewSet
- View [API Reference](../../api-reference.md) for detailed API documentation