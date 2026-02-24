# 过滤

SRF 提供了强大而灵活的过滤系统，支持搜索、复杂查询和排序功能。

## 过滤概述

过滤系统允许客户端通过查询参数来筛选和排序数据，提供了多种内置过滤器：

- **SearchFilter**: 全文搜索
- **JsonLogicFilter**: 复杂的 JSON Logic 查询
- **QueryParamFilter**: 基于查询参数的精确过滤
- **OrderingFactory**: 排序功能

## BaseFilter

所有过滤器都继承自 `BaseFilter` 抽象基类：

```python
from srf.filters.filter import BaseFilter

class BaseFilter:
    """过滤器基类"""
    
    async def filter_queryset(self, request, queryset):
        """过滤查询集
        
        Args:
            request: 请求对象
            queryset: Tortoise ORM 查询集
        
        Returns:
            过滤后的查询集
        """
        raise NotImplementedError
```

## SearchFilter - 全文搜索

`SearchFilter` 提供全文搜索功能，在指定字段中搜索关键词。

### 基本用法

```python
from srf.views import BaseViewSet

class ProductViewSet(BaseViewSet):
    # 定义可搜索的字段
    search_fields = ["name", "description", "sku"]
    
    @property
    def queryset(self):
        return Product.all()
```

### 请求示例

```bash
# 搜索名称、描述或 SKU 包含 "手机" 的产品
GET /api/products?search=手机

# 搜索多个关键词（AND 关系）
GET /api/products?search=苹果 手机
```

### 搜索逻辑

- **多个关键词**：使用空格分隔，关系为 AND
- **多个字段**：在任一字段中匹配即可，关系为 OR
- **大小写不敏感**：自动转换为小写搜索

示例：`search=苹果 手机`

```python
# 转换为查询：
Q(name__icontains="苹果") | Q(description__icontains="苹果") | Q(sku__icontains="苹果")
AND
Q(name__icontains="手机") | Q(description__icontains="手机") | Q(sku__icontains="手机")
```

### 自定义搜索字段

```python
class ProductViewSet(BaseViewSet):
    search_fields = [
        "name",           # 产品名称
        "description",    # 描述
        "sku",           # SKU
        "brand__name",   # 品牌名称（关联字段）
    ]
```

## QueryParamFilter - 精确过滤

`QueryParamFilter` 基于查询参数进行精确匹配过滤。

### 基本用法

```python
class ProductViewSet(BaseViewSet):
    # 定义过滤字段映射
    filter_fields = {
        "category": "category_id",      # 分类ID
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

### 支持的查找类型

| 参数后缀 | Tortoise查找 | 说明 | 示例 |
|----------|--------------|------|------|
| 无 | `=` | 精确匹配 | `category=1` |
| `__gte` | `>=` | 大于等于 | `min_price__gte=100` |
| `__lte` | `<=` | 小于等于 | `max_price__lte=500` |
| `__gt` | `>` | 大于 | `stock__gt=0` |
| `__lt` | `<` | 小于 | `price__lt=1000` |
| `__in` | `IN` | 包含 | `id__in=1,2,3` |
| `__contains` | `LIKE %x%` | 包含 | `name__contains=手机` |
| `__icontains` | `ILIKE %x%` | 不区分大小写包含 | `name__icontains=Phone` |
| `__startswith` | `LIKE x%` | 以...开头 | `sku__startswith=PRD` |

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
        
        # IN 查询
        "ids": "id__in",
        "categories": "category_id__in",
    }
```

请求：

```bash
# 多个ID
GET /api/products?ids=1,2,3,4,5

# 多个分类
GET /api/products?categories=1,2,3

# 名称包含
GET /api/products?name_contains=手机

# SKU 开头
GET /api/products?sku_starts=PRD
```

## JsonLogicFilter - 复杂查询

`JsonLogicFilter` 支持使用 JSON Logic 表达式进行复杂查询。

### 基本用法

```python
class ProductViewSet(BaseViewSet):
    filter_fields = {
        "category": "category_id",
        "price": "price",
        "stock": "stock",
        "is_active": "is_active",
    }
```

### 请求示例

使用 `filter` 参数传递 JSON Logic 表达式：

```bash
# 价格大于100
GET /api/products?filter={"price": {">": 100}}

# 价格在100到500之间
GET /api/products?filter={"and": [{"price": {">=": 100}}, {"price": {"<=": 500}}]}

# 分类为1且有库存
GET /api/products?filter={"and": [{"category": 1}, {"stock": {">": 0}}]}
```

### 支持的操作符

#### 比较操作符

```bash
# 等于
{"price": 100}
{"price": {"==": 100}}

# 不等于
{"status": {"!=": "draft"}}

# 大于
{"price": {">": 100}}

# 大于等于
{"price": {">=": 100}}

# 小于
{"price": {"<": 500}}

# 小于等于
{"price": {"<=": 500}}
```

#### IN 操作符

```bash
# 在列表中
{"category": {"in": [1, 2, 3]}}

# 不在列表中
{"status": {"not in": ["draft", "archived"]}}
```

#### LIKE 操作符

```bash
# 模糊匹配
{"name": {"like": "%手机%"}}
```

#### 逻辑操作符

```bash
# AND（所有条件都满足）
{"and": [
  {"price": {">=": 100}},
  {"price": {"<=": 500}},
  {"is_active": true}
]}

# OR（任一条件满足）
{"or": [
  {"category": 1},
  {"category": 2}
]}

# NOT（条件不满足）
{"not": {"status": "archived"}}
```

### 复杂查询示例

#### 示例 1：价格范围和分类

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

#### 示例 2：多个OR条件

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

#### 示例 3：NOT条件

```json
{
  "and": [
    {"is_active": true},
    {"not": {"status": {"in": ["draft", "archived"]}}}
  ]
}
```

### Python 客户端示例

```python
import json
import requests

# 构建过滤条件
filter_logic = {
    "and": [
        {"category": {"in": [1, 2, 3]}},
        {"price": {">=": 100}},
        {"price": {"<=": 500}},
        {"is_active": True}
    ]
}

# 发送请求
response = requests.get(
    "http://localhost:8000/api/products",
    params={"filter": json.dumps(filter_logic)}
)

products = response.json()
```

## OrderingFactory - 排序

`OrderingFactory` 提供排序功能。

### 基本用法

```python
class ProductViewSet(BaseViewSet):
    ordering_fields = {
        "price": "price",
        "name": "name",
        "created": "created_at",
        "stock": "stock",
    }
```

### 请求示例

```bash
# 按价格升序
GET /api/products?sort=price

# 按价格降序（加负号）
GET /api/products?sort=-price

# 多字段排序
GET /api/products?sort=-price,name

# 先按分类降序，再按价格升序
GET /api/products?sort=-category,price
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
GET /api/products?search=手机&category=1&min_price=1000&max_price=5000&sort=-price&page=1&page_size=20
```

执行顺序：

1. 应用搜索（SearchFilter）
2. 应用精确过滤（QueryParamFilter）
3. 应用 JSON 过滤（JsonLogicFilter）
4. 应用排序（OrderingFactory）
5. 应用分页（PaginationHandler）

## 自定义过滤器

### 创建自定义过滤器

```python
from srf.filters.filter import BaseFilter
from tortoise.expressions import Q

class PriceRangeFilter(BaseFilter):
    """价格范围过滤器"""
    
    async def filter_queryset(self, request, queryset):
        """按价格范围过滤"""
        price_range = request.args.get('price_range')
        
        if not price_range:
            return queryset
        
        # 解析价格范围: "100-500"
        try:
            min_price, max_price = map(float, price_range.split('-'))
            queryset = queryset.filter(
                Q(price__gte=min_price) & Q(price__lte=max_price)
            )
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

## 完整示例

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.filters.filter import SearchFilter, JsonLogicFilter, QueryParamFilter, OrderingFactory
from sanic.response import json
from models import Product
from schemas import ProductSchemaReader, ProductSchemaWriter

class ProductViewSet(BaseViewSet):
    """产品 ViewSet - 完整的过滤示例"""
    
    # 搜索字段
    search_fields = [
        "name",
        "description",
        "sku",
        "brand__name",       # 关联字段
        "category__name",    # 关联字段
    ]
    
    # 过滤字段
    filter_fields = {
        # 精确匹配
        "category": "category_id",
        "brand": "brand_id",
        "status": "status",
        "is_active": "is_active",
        
        # 范围查询
        "min_price": "price__gte",
        "max_price": "price__lte",
        "min_stock": "stock__gte",
        
        # 模糊查询
        "name_contains": "name__icontains",
        
        # IN 查询
        "ids": "id__in",
        "categories": "category_id__in",
    }
    
    # 排序字段
    ordering_fields = {
        "price": "price",
        "name": "name",
        "stock": "stock",
        "created": "created_at",
        "updated": "updated_at",
    }
    
    # 指定使用的过滤器类
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
        """热门产品（自定义过滤）"""
        # 获取查询集
        queryset = Product.filter(is_active=True, stock__gt=0)
        
        # 应用搜索和排序
        for filter_class in [SearchFilter, OrderingFactory]:
            queryset = await filter_class().filter_queryset(request, queryset)
        
        # 限制数量
        queryset = queryset.limit(10)
        
        # 序列化
        products = await queryset
        schema = self.get_schema(request, is_safe=True)
        results = [schema.model_validate(p).model_dump() for p in products]
        
        return json({"results": results})
```

### 查询示例

```bash
# 1. 基本搜索
GET /api/products?search=手机

# 2. 搜索 + 分类过滤
GET /api/products?search=手机&category=1

# 3. 价格范围 + 排序
GET /api/products?min_price=1000&max_price=5000&sort=-price

# 4. 复杂过滤（JSON Logic）
GET /api/products?filter={"and":[{"category":{"in":[1,2]}},{"price":{">=":1000}}]}

# 5. 组合查询
GET /api/products?search=苹果&category=1&min_price=3000&sort=-created&page=1&page_size=20

# 6. 多个分类
GET /api/products?categories=1,2,3&sort=price

# 7. 名称包含
GET /api/products?name_contains=iPhone&is_active=true

# 8. 多个ID
GET /api/products?ids=1,2,3,4,5
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

### 2. 使用覆盖索引

为常用的查询组合创建复合索引：

```python
class Meta:
    indexes = [
        ("category_id", "is_active"),
        ("price", "created_at"),
    ]
```

### 3. 优化关联查询

使用 `prefetch_related` 优化关联字段搜索：

```python
@property
def queryset(self):
    return Product.all().prefetch_related("category", "brand", "tags")
```

### 4. 限制搜索字段

只在必要的字段上启用搜索，避免全表扫描：

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
5. **使用 JSON Logic 谨慎**：复杂查询可能影响性能
6. **组合使用过滤器**：充分利用多个过滤器的组合
7. **文档化过滤参数**：在 API 文档中说明支持的过滤参数

## 常见问题

### 如何实现 OR 查询？

使用 JSON Logic Filter：

```bash
GET /api/products?filter={"or":[{"category":1},{"category":2}]}
```

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
        # 不使用 JsonLogicFilter 和 OrderingFactory
    ]
```

## 下一步

- 学习 [分页](pagination.md) 了解如何与过滤结合
- 阅读 [视图](viewsets.md) 了解 ViewSet 的完整功能
- 查看 [API 参考](../../api-reference.md) 了解详细的 API 文档
