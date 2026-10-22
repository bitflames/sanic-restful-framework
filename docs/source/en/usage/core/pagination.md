# Pagination

SRF provides page-number-based pagination for list queries over large datasets.

## Pagination overview

Pagination splits large datasets into multiple pages and returns only one page of data at a time, improving API performance and user experience.

### Main features

- **Page-number based**: uses a page number and page size for pagination
- **Automatic pagination**: applied automatically in the ViewSet's list operation
- **Configurable**: supports custom page sizes, maximum size limits, and other parameters
- **Unified response**: returns a standardized paginated response format

## PageNumberPagination

`PageNumberPagination` is SRF's pagination class. Custom pagination can inherit from `BasePagination`,
in which case you must implement `from_queryset()`, `paginate()`, and `num_pages()`; or inherit from
`PageNumberPagination` and override only the behavior you want to change. `to_dict()` already has a default implementation
on `BasePagination`.

### Basic usage

Pagination is applied automatically in `BaseViewSet`'s `list` method:

```python
from srf.views import BaseViewSet


class ProductViewSet(BaseViewSet):
    @property
    def queryset(self):
        return Product.all()

    def get_schema(self):
        return ProductSchemaReader if self.request.is_safe else ProductSchemaWriter

    # The list method applies pagination automatically
```

### Request examples

```bash
# Get page 1 with the default page size
GET /api/products?page=1

# Get page 2 with 20 items per page
GET /api/products?page=2&page_size=20

# The page parameter can be omitted on the first page
GET /api/products?page_size=10
```

### Response format

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
    },
    {
      "id": 2,
      "name": "Product 2",
      "price": 89.99
    }
  ]
}
```

**Field reference**:

- `count`: Total number of records
- `next`: Whether there is a next page (boolean)
- `previous`: Whether there is a previous page (boolean)
- `results`: The list of data on the current page

## Configuration options

### Default configuration

```python
class PageNumberPagination:
    MAX_PAGE_SIZE: int = 100           # Upper bound for the requested page_size
    PAGE_QUERY_PARAM: str = 'page'     # Page number query parameter name
    PAGE_SIZE_QUERY_PARAM: str = 'page_size'  # Page size query parameter name
```

There are **no** `page_size` / `max_page_size` class attributes. When `page_size` is missing or invalid, `from_queryset` falls back to `page=1` and `page_size=10`. The requested `page_size` is limited to at most `MAX_PAGE_SIZE`.

#### Creating a custom pagination class

```python
from srf.paginator import PageNumberPagination


class CustomPagination(PageNumberPagination):
    MAX_PAGE_SIZE = 50
    PAGE_QUERY_PARAM = "p"
    PAGE_SIZE_QUERY_PARAM = "size"


class ProductViewSet(BaseViewSet):
    pagination_class = CustomPagination
```

## Using pagination manually

Apply pagination manually in a custom action:

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.paginator import PageNumberPagination
from sanic.response import json


class ProductViewSet(BaseViewSet):
    @action(methods=["get"], detail=False, url_path="featured")
    async def list_featured(self, request):
        """Get featured products (with pagination)"""
        # Get the queryset
        queryset = Product.filter(is_featured=True)

        # Create the paginator
        paginator = PageNumberPagination.from_queryset(queryset, request)

        # Get the schema
        schema = self.get_schema()

        # Paginate and serialize
        result = await paginator.to_dict(schema)

        return json(result)
```

## Pagination method details

### from_queryset(queryset, request)

Creates a paginator instance from a queryset and a request:

```python
from srf.paginator import PageNumberPagination

# Create the paginator
paginator = PageNumberPagination.from_queryset(queryset=Product.all(), request=request)
```

### paginate(sch_model)

Performs pagination and returns a `PaginationResult` object:

```python
from schemas import ProductSchemaReader

paginator = PageNumberPagination.from_queryset(queryset, request)
result = await paginator.paginate(sch_model=ProductSchemaReader)

# result is a PaginationResult object
print(result.count)      # Total count
print(result.next)       # Whether there is a next page
print(result.previous)   # Whether there is a previous page
print(result.results)    # Current page data (already serialized)
```

### to_dict(sch_model)

Performs pagination and returns a dictionary:

```python
from schemas import ProductSchemaReader

paginator = PageNumberPagination.from_queryset(queryset, request)
result_dict = await paginator.to_dict(sch_model=ProductSchemaReader)

# result_dict is a dictionary
# {
#   "count": 100,
#   "next": true,
#   "previous": false,
#   "results": [...]
# }
```

## Combining pagination with filtering

Pagination is usually used together with filtering, search, and ordering:

```python
class ProductViewSet(BaseViewSet):
    search_fields = ["name", "description"]
    filter_fields = {
        "category": "category_id",
        "min_price": "price__gte",
    }
    ordering_fields = {
        "price": "price",
        "name": "name",
    }

    # Request example:
    # GET /api/products?category=1&min_price=1000&ordering=-price&page=1&page_size=20
    # Default filter_class execution order:
    # 1. SearchFilter
    # 2. JsonLogicFilter
    # 3. QueryParamFilter
    # 4. OrderingFactory
    # 5. Pagination
```

## Custom pagination logic

### Example 1: Adding extra metadata

```python
from srf.paginator import PageNumberPagination
from sanic.response import json


class ProductViewSet(BaseViewSet):
    async def list(self, request):
        """Custom list method that adds extra information"""
        # Get the queryset and apply filtering
        queryset = self.queryset
        for filter_class in self.filter_class:
            queryset = filter_class(self).filter_queryset(request, queryset)

        # Paginate
        paginator = PageNumberPagination.from_queryset(queryset, request)
        schema = self.get_schema()
        result = await paginator.to_dict(schema)

        # Add extra information
        result["total_pages"] = (result["count"] + paginator.page_size - 1) // paginator.page_size
        result["current_page"] = paginator.page
        result["page_size"] = paginator.page_size

        return json(result)
```

Response:

```json
{
  "count": 100,
  "next": true,
  "previous": false,
  "total_pages": 10,
  "current_page": 1,
  "page_size": 10,
  "results": [...]
}
```

### Example 2: Cursor pagination

For large datasets, you can implement cursor pagination:

```python
from sanic.response import json


class ProductViewSet(BaseViewSet):
    @action(methods=["get"], detail=False, url_path="cursor-list")
    async def cursor_list(self, request):
        """Use cursor pagination"""
        cursor = request.args.get("cursor", 0)  # The last ID of the previous page
        limit = int(request.args.get("limit", 20))

        # Query records greater than the cursor
        queryset = Product.filter(id__gt=cursor).limit(limit + 1)
        products = await queryset

        # Check whether there is a next page
        has_next = len(products) > limit
        if has_next:
            products = products[:limit]

        # Serialize
        results = [ProductSchemaReader.model_validate(p).model_dump() for p in products]

        # Return the result
        next_cursor = products[-1].id if products and has_next else None

        return json(
            {
                "results": results,
                "next_cursor": next_cursor,
                "has_next": has_next,
            }
        )
```

## Client usage examples

### Basic pagination

```javascript
// Get page 1
fetch('/api/products?page=1&page_size=20')
  .then(res => res.json())
  .then(data => {
    console.log('Total:', data.count);
    console.log('Current page:', data.results);
    console.log('Has next page:', data.next);
  });
```

### Pagination navigation

```javascript
let currentPage = 1;

async function loadPage(page) {
  const response = await fetch(`/api/products?page=${page}&page_size=20`);
  const data = await response.json();
  
  // Render the data
  renderProducts(data.results);
  
  // Update the navigation buttons
  document.getElementById('prev-btn').disabled = !data.previous;
  document.getElementById('next-btn').disabled = !data.next;
  
  currentPage = page;
}

// Previous page
document.getElementById('prev-btn').onclick = () => {
  if (currentPage > 1) {
    loadPage(currentPage - 1);
  }
};

// Next page
document.getElementById('next-btn').onclick = () => {
  loadPage(currentPage + 1);
};
```

### Infinite scrolling

```javascript
let currentPage = 1;
let isLoading = false;
let hasMore = true;

async function loadMore() {
  if (isLoading || !hasMore) return;
  
  isLoading = true;
  
  const response = await fetch(`/api/products?page=${currentPage}&page_size=20`);
  const data = await response.json();
  
  // Append data
  appendProducts(data.results);
  
  // Update state
  hasMore = data.next;
  currentPage++;
  isLoading = false;
}

// Listen for scrolling
window.addEventListener('scroll', () => {
  if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 500) {
    loadMore();
  }
});

// Initial load
loadMore();
```

## Performance optimization

### 1. Use count() for optimization

For large datasets, use `count()` instead of `len()`:

```python
# Not recommended: loads all data
total = len(await Product.all())

# Recommended: only counts the records
total = await Product.all().count()
```

### 2. Use only() to select fields

Query only the fields you need:

```python
@property
def queryset(self):
    # Only query the fields needed by the list
    return Product.all().only("id", "name", "price", "image")
```

### 3. Use prefetch_related to optimize related queries

```python
@property
def queryset(self):
    # Preload related objects to reduce the number of queries
    return Product.all().prefetch_related("category", "brand")
```

### 4. Add indexes

Add database indexes for fields commonly used in filtering and ordering:

```python
class Product(Model):
    name = fields.CharField(max_length=200, index=True)
    price = fields.DecimalField(max_digits=10, decimal_places=2, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
```

## Best practices

1. **Choose a reasonable page size**: 10-50 items is usually appropriate; avoid overly large values
2. **Limit the maximum page size**: subclass and set `MAX_PAGE_SIZE`
3. **Combine with filtering**: pagination should be used together with filtering, search, and ordering
4. **Optimize queries**: use `only()`, `prefetch_related()`, and similar techniques to optimize queries
5. **Cache the total count**: for data that rarely changes, you can cache the total count
6. **Add indexes**: add database indexes for ordering and filtering fields
7. **Return metadata**: return extra information such as the total page count and current page for client convenience

## FAQ

### How do I disable pagination?

The built-in `list()` must use a pagination class (`pagination_class = None` causes `list()` to raise an error).
For endpoints that should not paginate, override `list()` or add a custom action (see "Get all data" below).

### How do I get all data (without pagination)?

```bash
# page_size is limited by PageNumberPagination.MAX_PAGE_SIZE (default 100)
GET /api/products?page_size=100
```

Or add a custom action in the ViewSet:

```python
@action(methods=["get"], detail=False, url_path="all")
async def get_all(self, request):
    """Get all products (without pagination)"""
    products = await Product.all()
    results = [ProductSchemaReader.model_validate(p).model_dump() for p in products]
    return json({"results": results})
```

### How do I implement offset/limit pagination?

```python
@action(methods=["get"], detail=False, url_path="offset-list")
async def offset_list(self, request):
    """Use offset/limit pagination"""
    offset = int(request.args.get("offset", 0))
    limit = int(request.args.get("limit", 20))

    queryset = Product.all()
    total = await queryset.count()

    products = await queryset.offset(offset).limit(limit)

    results = [ProductSchemaReader.model_validate(p).model_dump() for p in products]

    return json(
        {
            "total": total,
            "offset": offset,
            "limit": limit,
            "results": results,
        }
    )
```

## Next steps

- Study [Filtering](filtering.md) to learn how to combine it with pagination
- Read [Views](viewsets.md) for the complete functionality of ViewSets
- See [Performance Optimization](../advanced/advanced-features.md) for more optimization techniques
