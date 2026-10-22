# API 参考：Filters

过滤器负责把查询参数转换成 Tortoise 的 `Q` 表达式或 `filter()` 调用。`ListModelMixin.list()` 会按 `filter_class` 的顺序依次执行。使用说明见 [过滤](../usage/core/filtering.md)。

```python
from srf.filters import (
    JsonLogicFilter,
    OrderingFactory,
    QueryParamFilter,
    SearchFilter,
)
```

## 默认过滤器与参数

`settings.DEFAULT_FILTERS` 的顺序是 `SearchFilter`、`JsonLogicFilter`、`QueryParamFilter`、`OrderingFactory`，因此以下参数可以同时使用：

| 参数 | 过滤器 | 作用 |
| --- | --- | --- |
| `search` | `SearchFilter` | 多字段模糊搜索 |
| `filter` | `JsonLogicFilter` | JSON Logic 表达式 |
| `ordering` | `OrderingFactory` | 排序 |
| 任意 `filter_fields` 中的键 | `QueryParamFilter` | 精确匹配 |

字段白名单来自 ViewSet 的类属性：

```python
from srf.views import BaseViewSet


class BookViewSet(BaseViewSet):
    search_fields = ["title", "author"]
    # 别名 -> ORM 字段
    filter_fields = {"published": "is_published", "author_id": "author__id"}
    ordering_fields = ["create_time", "title"]
```

列表会被当作“字段名即参数名”，字典则用于把外部参数名映射到内部 ORM 字段。

## 过滤器类

四个内置过滤器都继承 `BaseFilter`，通过类属性声明各自需要的白名单字段。

::: srf.filters.filter.BaseFilter
    options:
      heading_level: 4
      members:
        - __init__
        - cls_fields
        - filter_queryset
      show_source: false
      inherited_members: false

子类必须设置 `cls_fields`（取值为 ViewSet 上保存字段白名单的属性名），否则在类定义阶段就会抛出 `TypeError`。`filter_fields` 在实例化时被归一化为 `{字段: ORM 字段}` 的字典。

::: srf.filters.filter.SearchFilter
    options:
      heading_level: 4
      members:
        - get_search_terms
        - filter_queryset
      show_source: false
      inherited_members: false

`?search=alice admin` 的语义：

- 按空白切分成多个关键词；
- 每个关键词在所有字段之间用 __OR__ 匹配（`__icontains`）；
- 多个关键词之间用 __AND__ 组合。

::: srf.filters.filter.JsonLogicFilter
    options:
      heading_level: 4
      members:
        - OPERATOR_MAP
        - filter_queryset
      show_source: false
      inherited_members: false

`?filter=` 接收一段 JSON Logic 表达式，支持的操作符：

| 操作符 | 含义 | 生成的查询 |
| --- | --- | --- |
| `==` | 等于 | `field=value` |
| `!=` / `!` | 不等于 | `NOT field=value` |
| `>` | 大于 | `field__gt` |
| `>=` | 大于等于 | `field__gte` |
| `<` | 小于 | `field__lt` |
| `<=` | 小于等于 | `field__lte` |
| `in` | 属于 | `field__in` |
| `not in` | 不属于 | `NOT field__in` |
| `like` | 包含 | `field__icontains` |

组合规则：

- `and` / `or` 的参数是__表达式数组__；
- `not` 的参数是单个表达式；
- 字段必须出现在 `filter_fields` 中，否则该条件被忽略；
- JSON 无法解析时返回 `400 Bad Request`。

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

参数名必须与 `filter_fields` 的键完全一致：

- 单值：`?published=true` → 精确匹配；
- 重复参数：`?id=1&id=2` → `id__in=[1, 2]`。

不在白名单中的参数会被忽略，不会报错。

::: srf.filters.filter.OrderingFactory
    options:
      heading_level: 4
      members:
        - filter_queryset
      show_source: false
      inherited_members: false

`?ordering=-create_time,title`：逗号分隔，前缀 `-` 表示倒序。未出现在 `ordering_fields` 中的字段会被忽略；所有字段都无效时保持默认顺序。
