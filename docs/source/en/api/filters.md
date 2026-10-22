# API Reference: Filters

Filters convert query parameters into Tortoise `Q` expressions or `filter()` calls. `ListModelMixin.list()` runs them in the order of `filter_class`. See [Filtering](../usage/core/filtering.md) for usage.

```python
from srf.filters import (
    JsonLogicFilter,
    OrderingFactory,
    QueryParamFilter,
    SearchFilter,
)
```

## Default filters and parameters

`settings.DEFAULT_FILTERS` has the order `SearchFilter`, `JsonLogicFilter`, `QueryParamFilter`, `OrderingFactory`, so the following parameters can be used together:

| Parameter | Filter | Purpose |
| --- | --- | --- |
| `search` | `SearchFilter` | Fuzzy search across multiple fields |
| `filter` | `JsonLogicFilter` | JSON Logic expressions |
| `ordering` | `OrderingFactory` | Sorting |
| Any key in `filter_fields` | `QueryParamFilter` | Exact matching |

The field allowlists come from ViewSet class attributes:

```python
from srf.views import BaseViewSet


class BookViewSet(BaseViewSet):
    search_fields = ["title", "author"]
    # alias -> ORM field
    filter_fields = {"published": "is_published", "author_id": "author__id"}
    ordering_fields = ["create_time", "title"]
```

Lists are treated as "the field name is the parameter name", while dictionaries map external parameter names to internal ORM fields.

## Filter classes

All four built-in filters inherit from `BaseFilter` and declare the allowlist fields they need through class attributes.

::: srf.filters.filter.BaseFilter
    options:
      heading_level: 4
      members:
        - __init__
        - cls_fields
        - filter_queryset
      show_source: false
      inherited_members: false

Subclasses must set `cls_fields` (the name of the ViewSet attribute that stores the field allowlist); otherwise a `TypeError` is raised at class definition time. `filter_fields` is normalized at instantiation into a `{field: ORM field}` dictionary.

::: srf.filters.filter.SearchFilter
    options:
      heading_level: 4
      members:
        - get_search_terms
        - filter_queryset
      show_source: false
      inherited_members: false

Semantics of `?search=alice admin`:

- Split into multiple keywords by whitespace;
- Each keyword is matched across all fields with __OR__ (`__icontains`);
- Multiple keywords are combined with __AND__.

::: srf.filters.filter.JsonLogicFilter
    options:
      heading_level: 4
      members:
        - OPERATOR_MAP
        - filter_queryset
      show_source: false
      inherited_members: false

`?filter=` accepts a JSON Logic expression. Supported operators:

| Operator | Meaning | Generated query |
| --- | --- | --- |
| `==` | Equals | `field=value` |
| `!=` / `!` | Not equals | `NOT field=value` |
| `>` | Greater than | `field__gt` |
| `>=` | Greater than or equal | `field__gte` |
| `<` | Less than | `field__lt` |
| `<=` | Less than or equal | `field__lte` |
| `in` | In | `field__in` |
| `not in` | Not in | `NOT field__in` |
| `like` | Contains | `field__icontains` |

Combination rules:

- The arguments of `and` / `or` are an __array of expressions__;
- The argument of `not` is a single expression;
- Fields must appear in `filter_fields`; otherwise the condition is ignored;
- If the JSON cannot be parsed, `400 Bad Request` is returned.

```python
# ?filter=<urlencoded JSON>
{
    "and": [
        {"==": [{"var": "published"}, True]},
        {"like": [{"var": "title"}, "python"]},
    ]
}
```

::: srf.filters.filter.QueryParamFilter
    options:
      heading_level: 4
      members:
        - filter_queryset
      show_source: false
      inherited_members: false

Parameter names must exactly match the keys of `filter_fields`:

- Single value: `?published=true` → exact match;
- Repeated parameter: `?id=1&id=2` → `id__in=[1, 2]`.

Parameters not in the allowlist are ignored and do not raise an error.

::: srf.filters.filter.OrderingFactory
    options:
      heading_level: 4
      members:
        - filter_queryset
      show_source: false
      inherited_members: false

`?ordering=-create_time,title`: comma-separated; a `-` prefix means descending. Fields not present in `ordering_fields` are ignored; if all fields are invalid, the default order is kept.
