# Filtering

SRF provides a flexible filtering system with search, query parameter filtering, and ordering capabilities.

## Filtering overview

The filtering system lets clients filter and sort data through query parameters and provides several built-in filters:

- **SearchFilter**: Performs keyword search on configured fields
- **QueryParamFilter**: Exact filtering based on query parameters
- **OrderingFactory**: Sorting functionality

`search_fields`, `filter_fields`, and `ordering_fields` all default to an empty list `[]`. All three accept either a list or a dictionary: field names in a list map to same-named ORM fields; a dictionary specifies ORM field names through its values, and the keys of `filter_fields` and `ordering_fields` are the request parameter names and available ordering names respectively. Use dictionaries when you need field aliases or ORM lookup expressions.

## BaseFilter

All filters inherit from the `BaseFilter` abstract base class:

```python
from srf.filters.filter import BaseFilter


class BaseFilter:
    """Filter base class"""

    # Subclasses must set this: the name of the ViewSet attribute holding the field allowlist
    cls_fields: str | None = None

    def filter_queryset(self, request, queryset):
        """Filter the queryset

        Args:
            request: The request object
            queryset: The Tortoise ORM queryset

        Returns:
            The filtered queryset
        """
        raise NotImplementedError
```

`BaseFilter.__init_subclass__()` checks `cls_fields`: if a subclass forgets to set it, a `TypeError` is raised at class definition time. If you do not use a field allowlist, set it to `"filter_fields"` (or any existing ViewSet attribute name). `filter_fields` is normalized into `{parameter name: ORM field name}` when the filter is instantiated.

## SearchFilter - full-text search

`SearchFilter` gets search fields from `search_fields` and reads the `search` parameter from the request. Field names in a list and dictionary values are both treated as ORM field names.

```python
class ProductViewSet(BaseViewSet):
    search_fields = ["name", "description", "sku"]
    # A dictionary is also supported, with ORM field names as values:
    # search_fields = {"product_name": "name", "product_description": "description"}
```

```bash
GET /api/products?search=phone
GET /api/products?search=wireless headphones
```

Multiple search fields are combined with OR; multiple keywords are combined with AND. In other words, the result must match every keyword, but each keyword may appear in any configured field.

## JsonLogicFilter - expression filtering

`?filter=` accepts a JSON Logic expression and can combine conditions within the `filter_fields` allowlist. Common operators include `==`, `!=`, `>`, `>=`, `<`, `<=`, `in`, `not in`, `like` (contains), and nested `and` / `or` / `not` are supported.

```bash
# Actual requests must URL-encode the JSON
GET /api/products?filter={"and":[{"==":[{"var":"is_active"},true]},{"like":[{"var":"name"},"phone"]}]}
```

Conditions on fields not present in `filter_fields` are ignored; if the JSON cannot be parsed, 400 is returned. See the [Filters API](../../api/filters.md#srf.filters.filter.JsonLogicFilter) for the complete operator table.

## QueryParamFilter - exact filtering

`QueryParamFilter` performs exact matching based on query parameters.

### Basic usage

```python
class ProductViewSet(BaseViewSet):
    # Define the filter field mapping
    # A list is also supported, e.g. filter_fields = ["category_id", "is_active", ...]
    filter_fields = {
        "category": "category_id",       # Category ID
        "brand": "brand_id",             # Brand ID
        "is_active": "is_active",        # Whether active
        "min_price": "price__gte",       # Minimum price (greater than or equal)
        "max_price": "price__lte",       # Maximum price (less than or equal)
    }
```

### Request examples

```bash
# Filter by category
GET /api/products?category=1

# Price range filtering
GET /api/products?min_price=100&max_price=500

# Multiple conditions
GET /api/products?category=1&brand=2&min_price=100&is_active=true
```

### Mapping between `filter_fields` and query parameters

Query parameter names must **exactly equal** the **keys** of `filter_fields`. Lookup suffixes are written in the mapping's **values**, not in the query parameter names.

| Lookup written in VALUE | Tortoise | Meaning | `filter_fields` example | Request |
| --------------------- | ---------- | ------ | ---------------------- | ------ |
| (none) | `=` | Exact match | `"category": "category_id"` | `?category=1` |
| `__gte` | `>=` | Greater than or equal | `"min_price": "price__gte"` | `?min_price=100` |
| `__lte` | `<=` | Less than or equal | `"max_price": "price__lte"` | `?max_price=500` |
| `__gt` | `>` | Greater than | `"min_stock": "stock__gt"` | `?min_stock=0` |
| `__lt` | `<` | Less than | `"max_price_lt": "price__lt"` | `?max_price_lt=1000` |
| `__icontains` | `ILIKE %x%` | Case-insensitive contains | `"name_contains": "name__icontains"` | `?name_contains=Phone` |
| `__startswith` | `LIKE x%` | Starts with | `"sku_starts": "sku__startswith"` | `?sku_starts=PRD` |

### Example

```python
class ProductViewSet(BaseViewSet):
    filter_fields = {
        # Exact match
        "category": "category_id",
        "status": "status",
        # Range queries
        "min_price": "price__gte",
        "max_price": "price__lte",
        "min_stock": "stock__gt",
        # Contains queries
        "name_contains": "name__icontains",
        "sku_starts": "sku__startswith",
        # Repeated parameters with the same name automatically get __in appended by QueryParamFilter
        "ids": "id",
        "categories": "category_id",
    }
```

Requests:

```bash
# Multiple IDs (repeated key → id__in)
GET /api/products?ids=1&ids=2&ids=3&ids=4&ids=5

# Multiple categories
GET /api/products?categories=1&categories=2&categories=3

# Name contains
GET /api/products?name_contains=phone

# SKU starts with
GET /api/products?sku_starts=PRD

# Price range (keys match filter_fields; the lookup is in the value)
GET /api/products?min_price=100&max_price=500
```

## OrderingFactory - ordering

`OrderingFactory` provides sorting functionality.

### Basic usage

```python
class ProductViewSet(BaseViewSet):
    # A list maps field names to the same ORM field names
    # ordering_fields = ["price", "username", "created_at", "stock"]
    ordering_fields = {
        "price": "price",
        "name": "username",
        "created": "created_at",
        "stock": "stock",
    }
```

### Request examples

```bash
# Sort by price ascending
GET /api/products?ordering=price

# Sort by price descending (prefix with a minus sign)
GET /api/products?ordering=-price

# Sort by multiple fields
GET /api/products?ordering=-price,name

# Sort by category descending first, then by price ascending
GET /api/products?ordering=-category,price
```

### Ordering rules

- **Ascending**: the field name
- **Descending**: prefix the field name with `-`
- **Multiple fields**: separate with commas

## Combining filters

All filters can be used at the same time:

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
    
    # Define ordering fields
    ordering_fields = {
        "price": "price",
        "name": "name",
        "created": "created_at",
    }
```

### Combined query example

```bash
# Search + filter + order + paginate
GET /api/products?search=phone&category=1&min_price=1000&max_price=5000&ordering=-price&page=1&page_size=20
```

With the default `filter_class`, the execution order is:

1. Apply search filtering (SearchFilter)
2. Apply JSON Logic filtering (JsonLogicFilter)
3. Apply exact filtering (QueryParamFilter)
4. Apply ordering (OrderingFactory)
5. Apply pagination (PageNumberPagination)

If the ViewSet customizes `filter_class`, the order of your custom list is used entirely.

## Custom filters

### Creating a custom filter

```python
from srf.filters.filter import BaseFilter
from tortoise.expressions import Q


class PriceRangeFilter(BaseFilter):
    """Price range filter"""

    # BaseFilter requires subclasses to declare cls_fields; this example does not read the allowlist, so any existing attribute name works
    cls_fields = "filter_fields"

    def filter_queryset(self, request, queryset):
        """Filter by price range (synchronous)"""
        price_range = request.args.get("price_range")

        if not price_range:
            return queryset

        # Parse the price range: "100-500"
        try:
            min_price, max_price = map(float, price_range.split("-"))
            queryset = queryset.filter(Q(price__gte=min_price) & Q(price__lte=max_price))
        except ValueError:
            pass

        return queryset
```

### Using a custom filter

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

## Combining filters in a custom action

`filter_queryset()` runs automatically in `list()`; custom actions need to construct filters manually:

```python
from sanic.response import json


class ProductViewSet(BaseViewSet):
    @action(methods=["get"], detail=False, url_path="popular")
    async def popular(self, request):
        queryset = Product.filter(is_active=True, stock__gt=0)

        # filter_queryset is synchronous; construct it with the ViewSet instance
        for filter_cls in [SearchFilter, OrderingFactory]:
            queryset = filter_cls(self).filter_queryset(request, queryset)

        products = await queryset.limit(10)
        results = [ProductSchemaReader.model_validate(p).model_dump() for p in products]
        return json({"results": results})
```

## Performance optimization

### 1. Add database indexes

Add indexes for commonly used filtering and ordering fields:

```python
class Product(Model):
    category_id = fields.IntField(index=True)
    price = fields.DecimalField(max_digits=10, decimal_places=2, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    is_active = fields.BooleanField(default=True, index=True)
```

### 2. Limit search fields

Select only the necessary fields to avoid full table scans:

```python
# Not recommended: searching too many fields
search_fields = ["name", "description", "content", "notes", "metadata"]

# Recommended: search only key fields
search_fields = ["name", "sku"]
```

## Best practices

1. **Choose filter fields sensibly**: expose only the necessary filter fields
2. **Add database indexes**: add indexes for filtering and ordering fields
3. **Limit search fields**: avoid searching large text fields
4. **Validate input**: validate the validity of filter parameters
5. **Combine filters**: make full use of multiple filters together
6. **Document filter parameters**: describe the supported filter parameters in the API documentation

## FAQ

### How do I implement date range queries?

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

### How do I implement fuzzy search?

Use SearchFilter or QueryParamFilter:

```python
# Option 1: SearchFilter
search_fields = ["name", "description"]

# Option 2: QueryParamFilter
filter_fields = {
    "name": "name__icontains",
}
```

### How do I disable a filter?

```python
class ProductViewSet(BaseViewSet):
    # Use only some filters
    filter_class = [
        SearchFilter,
        QueryParamFilter,
        # Do not use OrderingFactory
    ]
```

## Next steps

- Study [Pagination](pagination.md) to learn how to combine it with filtering
- Read [Views](viewsets.md) for the complete functionality of ViewSets
- See the [Filters API](../../api/filters.md) for detailed API documentation
