# 过滤

SRF 提供了灵活的过滤系统，支持搜索、查询参数过滤和排序功能。

## 过滤概述

过滤系统允许客户端通过查询参数来筛选和排序数据，提供了多种内置过滤器：

- **SearchFilter**: 按配置字段执行关键词搜索
- **QueryParamFilter**: 基于查询参数的精确过滤
- **OrderingFactory**: 排序功能

`search_fields`、`filter_fields` 和 `ordering_fields` 默认都为空列表 `[]`。三项都接受列表或字典：列表中的字段名会映射到同名 ORM 字段；字典通过值指定 ORM 字段名，`filter_fields` 和 `ordering_fields` 的键分别是请求参数名和可用排序名。需要字段别名或 ORM 查找表达式时使用字典。

## BaseFilter

所有过滤器都继承自 `BaseFilter` 抽象基类：

```python
from srf.filters.filter import BaseFilter


class BaseFilter:
    """过滤器基类"""

    # 子类必须设置：ViewSet 上保存字段白名单的属性名
    cls_fields: str | None = None

    def filter_queryset(self, request, queryset):
        """过滤查询集

        Args:
            request: 请求对象
            queryset: Tortoise ORM 查询集

        Returns:
            过滤后的查询集
        """
        raise NotImplementedError
```

`BaseFilter.__init_subclass__()` 会检查 `cls_fields`：子类忘记设置时会直接在类定义阶段抛出 `TypeError`。如果不使用字段白名单，也请把它设为 `"filter_fields"`（或任意存在的 ViewSet 属性名）。`filter_fields` 在过滤器实例化时会被归一化为 `{参数名: ORM 字段名}`。

## SearchFilter - 全文搜索

`SearchFilter` 从 `search_fields` 获取搜索字段，并读取请求中的 `search` 参数。列表中的字段名以及字典的值都会作为 ORM 字段名。

```python
class ProductViewSet(BaseViewSet):
    search_fields = ["name", "description", "sku"]
    # 也可提供字典，字典值为 ORM 字段名：
    # search_fields = {"product_name": "name", "product_description": "description"}
```

```bash
GET /api/products?search=phone
GET /api/products?search=wireless headphones
```

多个搜索字段之间按 OR 组合；多个关键词之间按 AND 组合。也就是说，结果需匹配每个关键词，但每个关键词可出现在任一配置字段中。

## JsonLogicFilter - 表达式过滤

`?filter=` 接收 JSON Logic 表达式，可按 `filter_fields` 白名单组合条件。常用操作符包括 `==`、`!=`、`>`、`>=`、`<`、`<=`、`in`、`not in`、`like`（包含），并支持 `and` / `or` / `not` 嵌套。

```bash
# 实际请求需对 JSON 做 URL 编码
GET /api/products?filter={"and":[{"==":[{"var":"is_active"},true]},{"like":[{"var":"name"},"phone"]}]}
```

字段不在 `filter_fields` 中的条件会被忽略；JSON 无法解析时返回 400。完整操作符表见 [过滤器 API](../../api/filters.md#srf.filters.filter.JsonLogicFilter)。

## QueryParamFilter - 精确过滤

`QueryParamFilter` 基于查询参数进行精确匹配过滤。

### 基本用法

```python
class ProductViewSet(BaseViewSet):
    # 定义过滤字段映射
    # 也可写成列表，例如 filter_fields = ["category_id", "is_active", ...]
    filter_fields = {
        "category": "category_id",       # 分类ID
        "brand": "brand_id",             # 品牌ID
        "is_active": "is_active",        # 是否激活
        "min_price": "price__gte",       # 最低价格（大于等于）
        "max_price": "price__lte",       # 最高价格（小于等于）
    }
```

### 请求示例

```bash
# 按分类过滤
GET /api/products?category=1

# 价格范围过滤
GET /api/products?min_price=100&max_price=500

# 多条件组合
GET /api/products?category=1&brand=2&min_price=100&is_active=true
```

### `filter_fields` 与查询参数的映射

查询参数名必须**精确等于** `filter_fields` 的**键**。查找后缀写在映射的**值**里，而不是写在查询参数名上。

| 写在 VALUE 中的查找 | Tortoise | 说明 | `filter_fields` 示例 | 请求 |
| --------------------- | ---------- | ------ | ---------------------- | ------ |
| （无） | `=` | 精确匹配 | `"category": "category_id"` | `?category=1` |
| `__gte` | `>=` | 大于等于 | `"min_price": "price__gte"` | `?min_price=100` |
| `__lte` | `<=` | 小于等于 | `"max_price": "price__lte"` | `?max_price=500` |
| `__gt` | `>` | 大于 | `"min_stock": "stock__gt"` | `?min_stock=0` |
| `__lt` | `<` | 小于 | `"max_price_lt": "price__lt"` | `?max_price_lt=1000` |
| `__icontains` | `ILIKE %x%` | 不区分大小写包含 | `"name_contains": "name__icontains"` | `?name_contains=Phone` |
| `__startswith` | `LIKE x%` | 以...开头 | `"sku_starts": "sku__startswith"` | `?sku_starts=PRD` |

### 示例

```python
class ProductViewSet(BaseViewSet):
    filter_fields = {
        # 精确匹配
        "category": "category_id",
        "status": "status",
        # 范围查询
        "min_price": "price__gte",
        "max_price": "price__lte",
        "min_stock": "stock__gt",
        # 包含查询
        "name_contains": "name__icontains",
        "sku_starts": "sku__startswith",
        # 重复同名参数会由 QueryParamFilter 自动追加 __in
        "ids": "id",
        "categories": "category_id",
    }
```

请求：

```bash
# 多个 ID（重复键 → id__in）
GET /api/products?ids=1&ids=2&ids=3&ids=4&ids=5

# 多个分类
GET /api/products?categories=1&categories=2&categories=3

# 名称包含
GET /api/products?name_contains=手机

# SKU 开头
GET /api/products?sku_starts=PRD

# 价格范围（键匹配 filter_fields；查找在值里）
GET /api/products?min_price=100&max_price=500
```

## OrderingFactory - 排序

`OrderingFactory` 提供排序功能。

### 基本用法

```python
class ProductViewSet(BaseViewSet):
    # 列表形式会把字段名映射到相同的 ORM 字段名
    # ordering_fields = ["price", "username", "created_at", "stock"]
    ordering_fields = {
        "price": "price",
        "name": "username",
        "created": "created_at",
        "stock": "stock",
    }
```

### 请求示例

```bash
# 按价格升序
GET /api/products?ordering=price

# 按价格降序（加负号）
GET /api/products?ordering=-price

# 多字段排序
GET /api/products?ordering=-price,name

# 先按分类降序，再按价格升序
GET /api/products?ordering=-category,price
```

### 排序规则

- **升序**：字段名
- **降序**：字段名前加 `-`
- **多字段**：用逗号分隔

## 过滤器组合使用

所有过滤器可以同时使用：

```python
class ProductViewSet(BaseViewSet):
    # 定义搜索字段
    search_fields = ["name", "description"]
    
    # 定义过滤字段
    filter_fields = {
        "category": "category_id",
        "min_price": "price__gte",
        "max_price": "price__lte",
        "is_active": "is_active",
    }
    
    # 定义排序字段
    ordering_fields = {
        "price": "price",
        "name": "name",
        "created": "created_at",
    }
```

### 组合查询示例

```bash
# 搜索 + 过滤 + 排序 + 分页
GET /api/products?search=phone&category=1&min_price=1000&max_price=5000&ordering=-price&page=1&page_size=20
```

使用默认 `filter_class` 时，执行顺序为：

1. 应用搜索过滤（SearchFilter）
2. 应用 JSON Logic 过滤（JsonLogicFilter）
3. 应用精确过滤（QueryParamFilter）
4. 应用排序（OrderingFactory）
5. 应用分页（PageNumberPagination）

如果 ViewSet 自定义了 `filter_class`，则完全以自定义列表的顺序为准。

## 自定义过滤器

### 创建自定义过滤器

```python
from srf.filters.filter import BaseFilter
from tortoise.expressions import Q


class PriceRangeFilter(BaseFilter):
    """价格范围过滤器"""

    # BaseFilter 要求子类声明 cls_fields；本例不读取白名单，填一个存在的属性名即可
    cls_fields = "filter_fields"

    def filter_queryset(self, request, queryset):
        """按价格范围过滤（同步）"""
        price_range = request.args.get("price_range")

        if not price_range:
            return queryset

        # 解析价格范围: "100-500"
        try:
            min_price, max_price = map(float, price_range.split("-"))
            queryset = queryset.filter(Q(price__gte=min_price) & Q(price__lte=max_price))
        except ValueError:
            pass

        return queryset
```

### 使用自定义过滤器

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

请求：

```bash
GET /api/products?price_range=100-500
```

## 在自定义 action 中组合过滤器

`filter_queryset()` 在 `list()` 中自动执行；自定义 action 需要手动构造过滤器：

```python
from sanic.response import json


class ProductViewSet(BaseViewSet):
    @action(methods=["get"], detail=False, url_path="popular")
    async def popular(self, request):
        queryset = Product.filter(is_active=True, stock__gt=0)

        # filter_queryset 是同步的；用 ViewSet 实例构造
        for filter_cls in [SearchFilter, OrderingFactory]:
            queryset = filter_cls(self).filter_queryset(request, queryset)

        products = await queryset.limit(10)
        results = [ProductSchemaReader.model_validate(p).model_dump() for p in products]
        return json({"results": results})
```

## 性能优化

### 1. 添加数据库索引

为常用的过滤和排序字段添加索引：

```python
class Product(Model):
    category_id = fields.IntField(index=True)
    price = fields.DecimalField(max_digits=10, decimal_places=2, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    is_active = fields.BooleanField(default=True, index=True)
```

### 2. 限制搜索字段

只选择必要字段，避免全表扫描：

```python
# 不推荐：搜索太多字段
search_fields = ["name", "description", "content", "notes", "metadata"]

# 推荐：只搜索关键字段
search_fields = ["name", "sku"]
```

## 最佳实践

1. **合理选择过滤字段**：只暴露必要的过滤字段
2. **添加数据库索引**：为过滤和排序字段添加索引
3. **限制搜索字段**：避免在大文本字段上搜索
4. **验证输入**：验证过滤参数的有效性
5. **组合使用过滤器**：充分利用多个过滤器的组合
6. **文档化过滤参数**：在 API 文档中说明支持的过滤参数

## 常见问题

### 如何实现日期范围查询？

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

### 如何实现模糊搜索？

使用 SearchFilter 或 QueryParamFilter：

```python
# 方法1：SearchFilter
search_fields = ["name", "description"]

# 方法2：QueryParamFilter
filter_fields = {
    "name": "name__icontains",
}
```

### 如何禁用某个过滤器？

```python
class ProductViewSet(BaseViewSet):
    # 只使用部分过滤器
    filter_class = [
        SearchFilter,
        QueryParamFilter,
        # 不使用 OrderingFactory
    ]
```

## 下一步

- 学习 [分页](pagination.md) 了解如何与过滤结合
- 阅读 [视图](viewsets.md) 了解 ViewSet 的完整功能
- 查看 [过滤器 API](../../api/filters.md) 了解详细的 API 文档
