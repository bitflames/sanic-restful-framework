# API Reference: Pagination

Pagination behavior is determined by the ViewSet's `pagination_class`, which defaults to `PageNumberPagination`. See [Pagination](../usage/core/pagination.md) for usage.

```python
from srf.paginator import PageNumberPagination
from srf.views import BaseViewSet


class BookViewSet(BaseViewSet):
    queryset = Book.all()  # Tortoise QuerySet
    schema = BookSchema  # Pydantic model
    pagination_class = PageNumberPagination
```

## Response structure

The object returned by `list()` always contains four fields:

```json
{
  "count": 42,
  "next": true,
  "previous": false,
  "results": [
    {"id": 1, "title": "..."}
  ]
}
```

!!! warning "Differences from DRF"
    `next` / `previous` are booleans, not URLs to the next/previous page. The frontend must construct page numbers itself.

## Query parameters

| Parameter | Default | Rule |
| --- | --- | --- |
| `page` | `1` | Falls back to `1` when it is not an integer or is less than 1 |
| `page_size` | `10` | Falls back to `10` when it is not an integer, and is limited to `1 ~ MAX_PAGE_SIZE` (default 100) |

- When the page number exceeds the total number of pages, an empty `results` is returned and `count` is still the total record count.
- The upper bound of `page_size` is controlled by the `MAX_PAGE_SIZE` class attribute, which subclasses can override.
- The parameter names are controlled by `PAGE_QUERY_PARAM` / `PAGE_SIZE_QUERY_PARAM`.

## Paginator API

::: srf.paginator.BasePagination
    options:
      heading_level: 4
      members:
        - from_queryset
        - paginate
        - to_dict
        - num_pages
        - serialize_list
      show_source: false
      inherited_members: false

Custom paginators should inherit from `BasePagination` and implement `from_queryset()`, `paginate()`, and `num_pages()`.

::: srf.paginator.PageNumberPagination
    options:
      heading_level: 4
      members:
        - __init__
        - MAX_PAGE_SIZE
        - PAGE_QUERY_PARAM
        - PAGE_SIZE_QUERY_PARAM
        - from_queryset
        - paginate
        - to_dict
        - num_pages
      show_source: false
      inherited_members: false

::: srf.paginator.PaginationResult
    options:
      heading_level: 4
      members: true
      show_source: false
      inherited_members: false

::: srf.paginator.PaginationParams
    options:
      heading_level: 4
      members: true
      show_source: false
      inherited_members: false

The fields of `PaginationResult` correspond to the four keys in the response; the fields of `PaginationParams` correspond to `page` / `page_size`.

::: srf.paginator.serialize_page
    options:
      heading_level: 4
      show_source: false

`serialize_page()` uses a `TypeAdapter(list[schema])` cached per schema, making it suitable for reuse in custom paginators. `PaginationParams` is a reusable parameter validation model; `PageNumberPagination` parses directly from request parameters and does not depend on it.
