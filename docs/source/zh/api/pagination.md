# API 参考：Pagination

分页行为由 ViewSet 的 `pagination_class` 决定，默认使用 `PageNumberPagination`。使用说明见 [分页](../usage/core/pagination.md)。

```python
from srf.paginator import PageNumberPagination
from srf.views import BaseViewSet


class BookViewSet(BaseViewSet):
    queryset = Book.all()  # Tortoise QuerySet
    schema = BookSchema  # Pydantic 模型
    pagination_class = PageNumberPagination
```

## 响应结构

`list()` 返回的对象固定包含四个字段：

```json
{
  "count": 42,
  "next": true,
  "previous": false,
  "results": [{ "id": 1, "title": "..." }]
}
```

!!! warning "与 DRF 的差异"
`next` / `previous` 是布尔值，不是下一页/上一页的 URL。前端需要自己拼装页码。

## 查询参数

| 参数        | 默认值 | 规则                                                                       |
| ----------- | ------ | -------------------------------------------------------------------------- |
| `page`      | `1`    | 非整数或小于 1 时回退/夹到 `1`                                             |
| `page_size` | `10`   | 非整数时回退为 `10`，小于 1 时夹到 `1`，上限为 `MAX_PAGE_SIZE`（默认 100） |

- 页码超出总页数时返回空 `results`，`count` 仍是总记录数。
- `page_size` 的上限由类属性 `MAX_PAGE_SIZE` 控制，子类可以覆盖；构造函数也会把 `page` / `page_size` 夹到合法范围。
- 参数名分别由 `PAGE_QUERY_PARAM` / `PAGE_SIZE_QUERY_PARAM` 控制。

## 分页器 API

::: srf.paginator.BasePagination
options:
heading_level: 4
members: - from_queryset - paginate - to_dict - num_pages - serialize_list
show_source: false
inherited_members: false

自定义分页器应继承 `BasePagination` 并实现 `from_queryset()`、`paginate()`、`num_pages()`。

::: srf.paginator.PageNumberPagination
options:
heading_level: 4
members: - **init** - MAX_PAGE_SIZE - PAGE_QUERY_PARAM - PAGE_SIZE_QUERY_PARAM - from_queryset - paginate - to_dict - num_pages
show_source: false
inherited_members: false

::: srf.paginator.PaginationResult
options:
heading_level: 4
members: true
show_source: false
inherited_members: false

`PaginationResult` 的字段对应响应中的四个键。

::: srf.paginator.serialize_page
options:
heading_level: 4
show_source: false

`serialize_page()` 使用按 Schema 缓存的 `TypeAdapter(list[schema])`，适合在自定义分页器中复用。
