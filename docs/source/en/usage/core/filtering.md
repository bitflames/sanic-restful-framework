# Filtering

SRF provides a powerful and flexible filtering system, supporting search, complex queries, and sorting functions.

## Overview of Filters

The filtering system allows clients to filter and sort data through query parameters, offering various built-in filters:

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

    def filter_queryset(self, request, queryset):
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
# Search for products with "手机" in name, description, or SKU
GET /api/products?search=手机

# Search for multiple keywords (AND relationship)
GET /api/products?search=苹果 手机
```

### Search Logic

- **Multiple Keywords**: Separated by spaces, relationship is AND
- **Multiple Fields**: Match in any field, relationship is OR
- **Case-insensitive**: Automatically converted to lowercase for search

Example: `search=苹果 手机`

```python
# Converted to query:
Q(name__icontains="苹果") | Q(description__icontains="苹果") | Q(sku__icontains="苹果")
AND
Q(name__icontains="手机") | Q(description__icontains="手机") | Q(sku__icontains="手机")
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

`QueryParamFilter` performs exact matching filtering based on query parameters.

### Basic Usage

```python
class ProductViewSet(BaseViewSet):
    # Define filter field mapping
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

# Price range filtering
GET /api/products?min_price=100&max_price=500

# Combined conditions
GET /api/products?category=1&brand=2&min_price=100&is_active=true
```

### Mapping between `filter_fields` and Query Parameters

The query parameter name must **exactly match** the **key** in `filter_fields`. The lookup suffix is written in the **value** of the mapping, not in the query parameter name.

| Lookup written in VALUE | Tortoise | Description | `filter_fields` Example | Request |
|-------------------------|----------|-------------|--------------------------|---------|
| (none)                  | `=`      | Exact match | `"category": "category_id"` | `?category=1` |
| `__gte`                 | `>=`     | Greater than or equal to | `"min_price": "price__gte"` | `?min_price=100` |
| `__lte`                 | `<=`     | Less than or equal to | `"max_price": "price__lte"` | `?max_price=500` |
| `__gt`                  | `>`      | Greater than | `"min_stock": "stock__gt"` | `?min_stock=0` |
| `__lt`                  | `<`      | Less than | `"max_price_lt": "price__lt"` | `?max_price_lt=1000` |
| `__icontains`           | `ILIKE %x%` | Case-insensitive contains | `"name_contains": "name__icontains"` | `?name_contains=Phone` |
| `__startswith`          | `LIKE x%` | Starts with | `"sku_starts": "sku__startswith"` | `?sku_starts=PRD` |

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

        # Repeated same parameter names are automatically appended with __in
        "ids": "id",
        "categories": "category_id",
    }
```

Request:

```bash
# Multiple IDs (repeated key → id__in)
GET /api/products?ids=1&ids=2&ids=3&ids=4&ids=5

# Multiple categories
GET /api/products?categories=1&categories=2&categories=3

# Name contains
GET /api/products?name_contains=手机

# SKU starts with
GET /api/products?sku_starts=PRD

# Price range (key matches filter_fields; lookup in value)
GET /api/products?min_price=100&max_price=500
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

Use the `filter` parameter to pass a JSON Logic expression. The standard form for comparison operations is  
`{"<op>": [{"var": "<field>"}, <value>]}` (field names are remapped via `filter_fields`).

```bash
# Price greater than 100
GET /api/products?filter={">": [{"var": "price"}, 100]}

# Price between 100 and 500
GET /api/products?filter={"and": [{">=": [{"var": "price"}, 100]}, {"<=": [{"var": "price"}, 500]}]}

# Category is 1 and has stock
GET /api/products?filter={"and": [{"==": [{"var": "category"}, 1]}, {">": [{"var": "stock"}, 0]}]}
```

### Supported Operators

#### Comparison Operators

```bash
# Equal
{"==": [{"var": "price"}, 100]}

# Not equal
{"!=": [{"var": "status"}, "draft"]}

# Greater than
{">": [{"var": "price"}, 100]}

# Greater than or equal
{">=": [{"var": "price"}, 100]}

# Less than
{"<": [{"var": "price"}, 500]}

# Less than or equal
{"<=": [{"var": "price"}, 500]}
```

#### IN Operator

```bash
# In a list
{"in": [{"var": "category"}, [1, 2, 3]]}

# Not in a list
{"not in": [{"var": "status"}, ["draft", "archived"]]}
```

#### LIKE Operator

```bash
# Fuzzy match
{"like": [{"var": "name"}, "手机"]}
```

#### Logical Operators

```bash
# AND (all conditions are satisfied)
{"and": [
  {">=": [{"var": "price"}, 100]},
  {"<=": [{"var": "price"}, 500]},
  {"==": [{"var": "is_active"}, true]}
]}

# OR (any condition is satisfied)
{"or": [
  {"==": [{"var": "category"}, 1]},
  {"==": [{"var": "category"}, 2]}
]}

# NOT (condition is not met)
{"not": {"==": [{"var": "status"}, "archived"]}}
```

### Complex Query Examples

#### Example 1: Price range and category

```json
{
  "and": [
    {"in": [{"var": "category"}, [1, 2]]},
    {">=": [{"var": "price"}, 100]},
    {"<=": [{"var": "price"}, 500]},
    {">": [{"var": "stock"}, 0]}
  ]
}
```

#### Example 2: Multiple OR conditions

```json
{
  "or": [
    {"==": [{"var": "category"}, 1]},
    {
      "and": [
        {"==": [{"var": "category"}, 2]},
        {"<": [{"var": "price"}, 200]}
      ]
    }
  ]
}
```

#### Example 3: NOT condition

```json
{
  "and": [
    {"==": [{"var": "is_active"}, true]},
    {"not": {"in": [{"var": "status"}, ["draft", "archived"]]}}
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
        {"in": [{"var": "category"}, [1, 2, 3]]},
        {">=": [{"var": "price"}, 100]},
        {"<=": [{"var": "price"}, 500]},
        {"==": [{"var": "is_active"}, True]},
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

# Sort by price descending (add a minus sign)
GET /api/products?sort=-price

# Multi-field sorting
GET /api/products?sort=-price,name

# First by category descending, then by price ascending
GET /api/products?sort=-category,price
```

### Sorting Rules

- **Ascending**: Field name
- **Descending**: Add `-` before the field name
- **Multi-field**: Separate with commas

## Using Filters Together

All filters can be used simultaneously:

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
GET /api/products?search=手机&category=1&min_price=1000&max_price=5000&sort=-price&page=1&page_size=20
```

Execution order:

1. Apply search (SearchFilter)
2. Apply JSON filter (JsonLogicFilter)
3. Apply exact filter (QueryParamFilter)
4. Apply sorting (OrderingFactory)
5. Apply pagination (PageNumberPagination)

## Custom Filters

### Creating a Custom Filter

```python
from srf.filters.filter import BaseFilter
from tortoise.expressions import Q

class PriceRangeFilter(BaseFilter):
    """Price range filter"""

    def filter_queryset(self, request, queryset):
        """Filter by price range (synchronous)"""
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

### Using a Custom Filter

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
    """Product ViewSet - Complete filter example"""
    
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

        # Repeated same parameter names will automatically be converted to __in
        "ids": "id",
        "categories": "category_id",
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
        is_read = request.method.upper() in ("GET", "HEAD", "OPTIONS")
        return ProductSchemaReader if is_read or is_safe else ProductSchemaWriter

    @action(methods=["get"], detail=False, url_path="popular")
    async def popular(self, request):
        """Popular products (custom filter)"""
        queryset = Product.filter(is_active=True, stock__gt=0)

        # filter_queryset is synchronous; use ViewSet instance
        for filter_cls in [SearchFilter, OrderingFactory]:
            queryset = filter_cls(self).filter_queryset(request, queryset)

        queryset = queryset.limit(10)

        products = await queryset
        schema = self.get_schema(request, is_safe=True)
        results = [schema.model_validate(p).model_dump() for p in products]

        return json({"results": results})
```

### Query Examples

```bash
# 1. Basic search
GET /api/products?search=手机

# 2. Search + Category filter
GET /api/products?search=手机&category=1

# 3. Price range + Sort
GET /api/products?min_price=1000&max_price=5000&sort=-price

# 4. Complex filter (JSON Logic)
GET /api/products?filter={"and":[{"in":[{"var":"category"},[1,2]]},{">=":[{"var":"price"},1000]}]}

# 5. Combined query
GET /api/products?search=苹果&category=1&min_price=3000&sort=-created&page=1&page_size=20

# 6. Multiple categories (repeated key)
GET /api/products?categories=1&categories=2&categories=3&sort=price

# 7. Name contains
GET /api/products?name_contains=iPhone&is_active=true

# 8. Multiple IDs (repeated key)
GET /api/products?ids=1&ids=2&ids=3&ids=4&ids=5
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

Optimize related field searches using `prefetch_related`:

```python
@property
def queryset(self):
    return Product.all().prefetch_related("category", "brand", "tags")
```

### 4. Limit Search Fields

Only enable search on necessary fields to avoid full table scans:

```python
# Not recommended: too many fields to search
search_fields = ["name", "description", "content", "notes", "metadata"]

# Recommended: only search key fields
search_fields = ["name", "sku"]
```

## Best Practices

1. **Choose filter fields wisely**: Only expose necessary filter fields
2. **Add database indexes**: Add indexes to filter and sort fields
3. **Limit search fields**: Avoid searching large text fields
4. **Validate input**: Validate the validity of filter parameters
5. **Use JSON Logic carefully**: Complex queries may affect performance
6. **Combine filters**: Fully utilize the combination of multiple filters
7. **Document filter parameters**: Document supported filter parameters in API documentation

## Frequently Asked Questions

### How to implement OR queries?

Use the JSON Logic Filter:

```bash
GET /api/products?filter={"or":[{"==":[{"var":"category"},1]},{"==":[{"var":"category"},2]}]}
```

### How to implement date range queries?

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

### How to implement fuzzy search?

Use `SearchFilter` or `QueryParamFilter`:

```python
# Method 1: SearchFilter
search_fields = ["name", "description"]

# Method 2: QueryParamFilter
filter_fields = {
    "name": "name__icontains",
}
```

### How to disable a specific filter?

```python
class ProductViewSet(BaseViewSet):
    # Use only part of the filters
    filter_class = [
            SearchFilter,
            QueryParamFilter,
            # Do not use JsonLogicFilter and OrderingFactory
        ]
```

## Next Steps

- Learn [Pagination](pagination.md) to understand how it combines with filtering
- Read [Views](viewsets.md) to learn about the full functionality of ViewSet
- View [API Reference](../../api-reference.md) for detailed API documentation