# Pagination

SRF provides a page-based pagination feature for handling list queries with large amounts of data.

## Overview of Pagination

Pagination divides large amounts of data into multiple pages, returning only one page of data at a time, which improves API performance and user experience.

### Key Features

- **Page-based**: Use page numbers and the number of items per page for pagination
- **Automatic Pagination**: Applied automatically in the `list` operation of ViewSet
- **Configurable**: Supports customizing the number of items per page and maximum limit
- **Standardized Response**: Returns a standardized pagination response format

## PaginationHandler

`PaginationHandler` is the pagination handler class in SRF.

### Basic Usage

Pagination is automatically applied in the `list` method of `BaseViewSet`:

```python
from srf.views import BaseViewSet

class ProductViewSet(BaseViewSet):
    @property
    def queryset(self):
        return Product.all()
    
    def get_schema(self, request, is_safe=False):
        return ProductSchemaReader if is_safe else ProductSchemaWriter
    
    # The list method automatically applies pagination
```

### Request Examples

```bash
# Get page 1, using default items per page
GET /api/products?page=1

# Get page 2, 20 items per page
GET /api/products?page=2&page_size=20

# Page 1 can omit the page parameter
GET /api/products?page_size=10
```

### Response Format

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

**Field Description**:

- `count`: Total number of records
- `next`: Whether there is a next page (boolean)
- `previous`: Whether there is a previous page (boolean)
- `results`: List of data on the current page

## Configuration Options

### Default Configuration

```python
class PaginationHandler:
    page_size = 10              # Default number of items per page
    max_page_size = 100         # Maximum number of items per page
    page_query_param = 'page'   # Page number parameter name
    page_size_query_param = 'page_size'  # Number of items per page parameter name
```

### Custom Configuration

#### Method 1: Configure in ViewSet

```python
class ProductViewSet(BaseViewSet):
    page_size = 20           # Custom number of items per page
    max_page_size = 50       # Custom maximum number of items per page
```

#### Method 2: Create a Custom Pagination Class

```python
from srf.paginator import PaginationHandler

class CustomPagination(PaginationHandler):
    page_size = 20
    max_page_size = 50
    page_query_param = 'p'
    page_size_query_param = 'size'

class ProductViewSet(BaseViewSet):
    pagination_class = CustomPagination
```

## Manually Using Pagination

Apply pagination manually in custom operations:

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.paginator import PaginationHandler
from sanic.response import json

class ProductViewSet(BaseViewSet):
    @action(methods=["get"], detail=False, url_path="featured")
    async def list_featured(self, request):
        """Get featured products (with pagination)"""
        # Get the query set
        queryset = Product.filter(is_featured=True)
        
        # Create paginator
        paginator = PaginationHandler.from_queryset(queryset, request)
        
        # Get Schema
        schema = self.get_schema(request, is_safe=True)
        
        # Execute pagination and serialization
        result = await paginator.to_dict(schema)
        
        return json(result)
```

## Detailed Pagination Methods

### from_queryset(queryset, request)

Create a paginator instance from a query set and request:

```python
from srf.paginator import PaginationHandler

# Create paginator
paginator = PaginationHandler.from_queryset(
    queryset=Product.all(),
    request=request
)
```

### paginate(sch_model)

Execute pagination and return a `PaginationResult` object:

```python
from schemas import ProductSchemaReader

paginator = PaginationHandler.from_queryset(queryset, request)
result = await paginator.paginate(sch_model=ProductSchemaReader)

# result is a PaginationResult object
print(result.count)      # Total count
print(result.next)       # Whether there is a next page
print(result.previous)   # Whether there is a previous page
print(result.results)    # Current page data (serialized)
```

### to_dict(sch_model)

Execute pagination and return a dictionary format:

```python
from schemas import ProductSchemaReader

paginator = PaginationHandler.from_queryset(queryset, request)
result_dict = await paginator.to_dict(sch_model=ProductSchemaReader)

# result_dict is a dictionary
# {
#   "count": 100,
#   "next": true,
#   "previous": false,
#   "results": [...]
# }
```

## Pagination Combined with Filtering

Pagination is often used with filtering, search, and sorting:

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
    
    # Example request:
    # GET /api/products?search=phone&category=1&min_price=1000&sort=-price&page=1&page_size=20
    # 
    # Execution order:
    # 1. Apply search filtering
    # 2. Apply field filtering
    # 3. Apply sorting
    # 4. Apply pagination
```

## Custom Pagination Logic

### Example 1: Adding Extra Metadata

```python
from srf.paginator import PaginationHandler
from sanic.response import json

class ProductViewSet(BaseViewSet):
    async def list(self, request):
        """Custom list method, adding extra information"""
        # Get the query set and apply filters
        queryset = self.queryset
        for filter_class in self.filter_class:
            queryset = await filter_class().filter_queryset(request, queryset)
        
        # Pagination
        paginator = PaginationHandler.from_queryset(queryset, request)
        schema = self.get_schema(request, is_safe=True)
        result = await paginator.to_dict(schema)
        
        # Add extra information
        result['total_pages'] = (result['count'] + paginator.page_size - 1) // paginator.page_size
        result['current_page'] = paginator.page
        result['page_size'] = paginator.page_size
        
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

### Example 2: Cursor Pagination

For large datasets, you can implement cursor pagination:

```python
from sanic.response import json

class ProductViewSet(BaseViewSet):
    @action(methods=["get"], detail=False, url_path="cursor-list")
    async def cursor_list(self, request):
        """Use cursor pagination"""
        cursor = request.args.get('cursor', 0)  # Last ID of the previous page
        limit = int(request.args.get('limit', 20))
        
        # Query records greater than cursor
        queryset = Product.filter(id__gt=cursor).limit(limit + 1)
        products = await queryset
        
        # Check if there is a next page
        has_next = len(products) > limit
        if has_next:
            products = products[:limit]
        
        # Serialization
        schema = self.get_schema(request, is_safe=True)
        results = [schema.model_validate(p).model_dump() for p in products]
        
        # Return result
        next_cursor = products[-1].id if products and has_next else None
        
        return json({
            "results": results,
            "next_cursor": next_cursor,
            "has_next": has_next,
        })
```

## Complete Example

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.permission.permission import IsAuthenticated
from srf.paginator import PaginationHandler
from sanic.response import json
from models import Product
from schemas import ProductSchemaReader, ProductSchemaWriter

class ProductViewSet(BaseViewSet):
    """Product ViewSet - Pagination Example"""
    
    permission_classes = (IsAuthenticated,)
    search_fields = ["name", "description", "sku"]
    filter_fields = {
        "category": "category_id",
        "min_price": "price__gte",
        "max_price": "price__lte",
    }
    ordering_fields = {
        "price": "price",
        "name": "name",
        "created": "created_at",
    }
    
    # Custom pagination configuration
    page_size = 20
    max_page_size = 100
    
    @property
    def queryset(self):
        return Product.all().prefetch_related("category")
    
    def get_schema(self, request, is_safe=False):
        return ProductSchemaReader if is_safe else ProductSchemaWriter
    
    # The list method automatically applies pagination
    
    @action(methods=["get"], detail=False, url_path="search")
    async def search_products(self, request):
        """Custom search (with pagination)"""
        keyword = request.args.get('q', '')
        
        if not keyword:
            return json({"error": "Please provide a search keyword"}, status=400)
        
        # Search
        queryset = Product.filter(name__icontains=keyword)
        
        # Pagination
        paginator = PaginationHandler.from_queryset(queryset, request)
        schema = self.get_schema(request, is_safe=True)
        result = await paginator.to_dict(schema)
        
        # Add search keyword to response
        result['keyword'] = keyword
        
        return json(result)
```

### Client Usage Example

#### Basic Pagination

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

#### Pagination Navigation

```javascript
let currentPage = 1;

async function loadPage(page) {
  const response = await fetch(`/api/products?page=${page}&page_size=20`);
  const data = await response.json();
  
  // Display data
  renderProducts(data.results);
  
  // Update navigation buttons
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

#### Infinite Scroll

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

// Listen to scroll
window.addEventListener('scroll', () => {
  if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 500) {
    loadMore();
  }
});

// Initial load
loadMore();
```

## Performance Optimization

### 1. Use count() Optimization

For large datasets, use `count()` instead of `len()`:

```python
# Not recommended: Load all data
total = len(await Product.all())

# Recommended: Only count the number
total = await Product.all().count()
```

### 2. Use only() to Select Fields

Query only the required fields:

```python
@property
def queryset(self):
    # Query only the fields needed for the list
    return Product.all().only('id', 'name', 'price', 'image')
```

### 3. Use prefetch_related to Optimize Related Queries

```python
@property
def queryset(self):
    # Prefetch related objects to reduce the number of queries
    return Product.all().prefetch_related('category', 'brand')
```

### 4. Add Indexes

Add database indexes for frequently used filtering and sorting fields:

```python
class Product(Model):
    name = fields.CharField(max_length=200, index=True)
    price = fields.DecimalField(max_digits=10, decimal_places=2, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
```

## Best Practices

1. **Set a reasonable number of items per page**: Typically 10-50 items are appropriate, avoid too large.
2. **Limit maximum page size**: Set `max_page_size` to prevent abuse.
3. **Combine with filtering**: Pagination should be used together with filtering, search, and sorting.
4. **Optimize queries**: Use `only()`, `prefetch_related()` and other optimizations.
5. **Cache total count**: For data that doesn't change often, cache the total count.
6. **Add indexes**: Add database indexes for sorting and filtering fields.
7. **Return metadata**: Return additional information such as total pages and current page for client usage.

## Common Issues

### How to Disable Pagination?

```python
class ProductViewSet(BaseViewSet):
    pagination_class = None  # Disable pagination
```

### How to Get All Data (Without Pagination)?

```bash
# Set a very large page_size
GET /api/products?page_size=10000
```

Or add a custom action in the ViewSet:

```python
@action(methods=["get"], detail=False, url_path="all")
async def get_all(self, request):
    """Get all products (without pagination)"""
    products = await Product.all()
    schema = self.get_schema(request, is_safe=True)
    results = [schema.model_validate(p).model_dump() for p in products]
    return json({"results": results})
```

### How to Implement Offset/Limit Pagination?

```python
@action(methods=["get"], detail=False, url_path="offset-list")
async def offset_list(self, request):
    """Use offset/limit pagination"""
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    
    queryset = Product.all()
    total = await queryset.count()
    
    products = await queryset.offset(offset).limit(limit)
    
    schema = self.get_schema(request, is_safe=True)
    results = [schema.model_validate(p).model_dump() for p in products]
    
    return json({
        "total": total,
        "offset": offset,
        "limit": limit,
        "results": results,
    })
```

## Next Steps

- Learn [Filtering](filtering.md) to understand how to combine it with pagination
- Read [Views](viewsets.md) to learn about the full features of ViewSet
- View [Performance Optimization](../advanced/advanced-features.md) for more optimization techniques