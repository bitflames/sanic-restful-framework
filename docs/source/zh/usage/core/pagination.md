# 分页

SRF 提供了基于页码的分页功能，用于处理大量数据的列表查询。

## 分页概述

分页将大量数据分割成多个页面，每次只返回一页的数据，提高 API 性能和用户体验。

### 主要特性

- **基于页码**：使用页码和每页数量进行分页
- **自动分页**：在 ViewSet 的 list 操作中自动应用
- **可配置**：支持自定义每页数量和最大数量限制
- **统一响应**：返回标准化的分页响应格式

## PaginationHandler

`PaginationHandler` 是 SRF 的分页处理类。

### 基本用法

分页在 `BaseViewSet` 的 `list` 方法中自动应用：

```python
from srf.views import BaseViewSet

class ProductViewSet(BaseViewSet):
    @property
    def queryset(self):
        return Product.all()
    
    def get_schema(self, request, is_safe=False):
        return ProductSchemaReader if is_safe else ProductSchemaWriter
    
    # list 方法会自动应用分页
```

### 请求示例

```bash
# 获取第1页，使用默认每页数量
GET /api/products?page=1

# 获取第2页，每页20条
GET /api/products?page=2&page_size=20

# 第一页可以省略 page 参数
GET /api/products?page_size=10
```

### 响应格式

```json
{
  "count": 100,
  "next": true,
  "previous": false,
  "results": [
    {
      "id": 1,
      "name": "产品1",
      "price": 99.99
    },
    {
      "id": 2,
      "name": "产品2",
      "price": 89.99
    }
  ]
}
```

**字段说明**：

- `count`: 总记录数
- `next`: 是否有下一页（boolean）
- `previous`: 是否有上一页（boolean）
- `results`: 当前页的数据列表

## 配置选项

### 默认配置

```python
class PaginationHandler:
    page_size = 10              # 默认每页数量
    max_page_size = 100         # 最大每页数量
    page_query_param = 'page'   # 页码参数名
    page_size_query_param = 'page_size'  # 每页数量参数名
```

### 自定义配置

#### 方法 1：在 ViewSet 中配置

```python
class ProductViewSet(BaseViewSet):
    page_size = 20           # 自定义每页数量
    max_page_size = 50       # 自定义最大每页数量
```

#### 方法 2：创建自定义分页类

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

## 手动使用分页

在自定义操作中手动应用分页：

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.paginator import PaginationHandler
from sanic.response import json

class ProductViewSet(BaseViewSet):
    @action(methods=["get"], detail=False, url_path="featured")
    async def list_featured(self, request):
        """获取推荐产品（带分页）"""
        # 获取查询集
        queryset = Product.filter(is_featured=True)
        
        # 创建分页器
        paginator = PaginationHandler.from_queryset(queryset, request)
        
        # 获取 Schema
        schema = self.get_schema(request, is_safe=True)
        
        # 执行分页并序列化
        result = await paginator.to_dict(schema)
        
        return json(result)
```

## 分页方法详解

### from_queryset(queryset, request)

从查询集和请求创建分页器实例：

```python
from srf.paginator import PaginationHandler

# 创建分页器
paginator = PaginationHandler.from_queryset(
    queryset=Product.all(),
    request=request
)
```

### paginate(sch_model)

执行分页并返回 `PaginationResult` 对象：

```python
from schemas import ProductSchemaReader

paginator = PaginationHandler.from_queryset(queryset, request)
result = await paginator.paginate(sch_model=ProductSchemaReader)

# result 是 PaginationResult 对象
print(result.count)      # 总数
print(result.next)       # 是否有下一页
print(result.previous)   # 是否有上一页
print(result.results)    # 当前页数据（已序列化）
```

### to_dict(sch_model)

执行分页并返回字典格式：

```python
from schemas import ProductSchemaReader

paginator = PaginationHandler.from_queryset(queryset, request)
result_dict = await paginator.to_dict(sch_model=ProductSchemaReader)

# result_dict 是字典
# {
#   "count": 100,
#   "next": true,
#   "previous": false,
#   "results": [...]
# }
```

## 分页与过滤结合

分页通常与过滤、搜索、排序一起使用：

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
    
    # 请求示例：
    # GET /api/products?search=手机&category=1&min_price=1000&sort=-price&page=1&page_size=20
    # 
    # 执行顺序：
    # 1. 应用搜索过滤
    # 2. 应用字段过滤
    # 3. 应用排序
    # 4. 应用分页
```

## 自定义分页逻辑

### 示例 1：添加额外的元数据

```python
from srf.paginator import PaginationHandler
from sanic.response import json

class ProductViewSet(BaseViewSet):
    async def list(self, request):
        """自定义列表方法，添加额外信息"""
        # 获取查询集并应用过滤
        queryset = self.queryset
        for filter_class in self.filter_class:
            queryset = await filter_class().filter_queryset(request, queryset)
        
        # 分页
        paginator = PaginationHandler.from_queryset(queryset, request)
        schema = self.get_schema(request, is_safe=True)
        result = await paginator.to_dict(schema)
        
        # 添加额外信息
        result['total_pages'] = (result['count'] + paginator.page_size - 1) // paginator.page_size
        result['current_page'] = paginator.page
        result['page_size'] = paginator.page_size
        
        return json(result)
```

响应：

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

### 示例 2：游标分页（Cursor Pagination）

对于大数据集，可以实现游标分页：

```python
from sanic.response import json

class ProductViewSet(BaseViewSet):
    @action(methods=["get"], detail=False, url_path="cursor-list")
    async def cursor_list(self, request):
        """使用游标分页"""
        cursor = request.args.get('cursor', 0)  # 上一页的最后一个 ID
        limit = int(request.args.get('limit', 20))
        
        # 查询大于 cursor 的记录
        queryset = Product.filter(id__gt=cursor).limit(limit + 1)
        products = await queryset
        
        # 检查是否有下一页
        has_next = len(products) > limit
        if has_next:
            products = products[:limit]
        
        # 序列化
        schema = self.get_schema(request, is_safe=True)
        results = [schema.model_validate(p).model_dump() for p in products]
        
        # 返回结果
        next_cursor = products[-1].id if products and has_next else None
        
        return json({
            "results": results,
            "next_cursor": next_cursor,
            "has_next": has_next,
        })
```

## 完整示例

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.permission.permission import IsAuthenticated
from srf.paginator import PaginationHandler
from sanic.response import json
from models import Product
from schemas import ProductSchemaReader, ProductSchemaWriter

class ProductViewSet(BaseViewSet):
    """产品 ViewSet - 分页示例"""
    
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
    
    # 自定义分页配置
    page_size = 20
    max_page_size = 100
    
    @property
    def queryset(self):
        return Product.all().prefetch_related("category")
    
    def get_schema(self, request, is_safe=False):
        return ProductSchemaReader if is_safe else ProductSchemaWriter
    
    # list 方法自动应用分页
    
    @action(methods=["get"], detail=False, url_path="search")
    async def search_products(self, request):
        """自定义搜索（带分页）"""
        keyword = request.args.get('q', '')
        
        if not keyword:
            return json({"error": "请提供搜索关键词"}, status=400)
        
        # 搜索
        queryset = Product.filter(name__icontains=keyword)
        
        # 分页
        paginator = PaginationHandler.from_queryset(queryset, request)
        schema = self.get_schema(request, is_safe=True)
        result = await paginator.to_dict(schema)
        
        # 添加搜索关键词到响应
        result['keyword'] = keyword
        
        return json(result)
```

### 客户端使用示例

#### 基本分页

```javascript
// 获取第1页
fetch('/api/products?page=1&page_size=20')
  .then(res => res.json())
  .then(data => {
    console.log('总数:', data.count);
    console.log('当前页:', data.results);
    console.log('有下一页:', data.next);
  });
```

#### 分页导航

```javascript
let currentPage = 1;

async function loadPage(page) {
  const response = await fetch(`/api/products?page=${page}&page_size=20`);
  const data = await response.json();
  
  // 显示数据
  renderProducts(data.results);
  
  // 更新导航按钮
  document.getElementById('prev-btn').disabled = !data.previous;
  document.getElementById('next-btn').disabled = !data.next;
  
  currentPage = page;
}

// 上一页
document.getElementById('prev-btn').onclick = () => {
  if (currentPage > 1) {
    loadPage(currentPage - 1);
  }
};

// 下一页
document.getElementById('next-btn').onclick = () => {
  loadPage(currentPage + 1);
};
```

#### 无限滚动

```javascript
let currentPage = 1;
let isLoading = false;
let hasMore = true;

async function loadMore() {
  if (isLoading || !hasMore) return;
  
  isLoading = true;
  
  const response = await fetch(`/api/products?page=${currentPage}&page_size=20`);
  const data = await response.json();
  
  // 追加数据
  appendProducts(data.results);
  
  // 更新状态
  hasMore = data.next;
  currentPage++;
  isLoading = false;
}

// 监听滚动
window.addEventListener('scroll', () => {
  if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 500) {
    loadMore();
  }
});

// 初始加载
loadMore();
```

## 性能优化

### 1. 使用 count() 优化

对于大数据集，使用 `count()` 而不是 `len()`：

```python
# 不推荐：加载所有数据
total = len(await Product.all())

# 推荐：只统计数量
total = await Product.all().count()
```

### 2. 使用 only() 选择字段

只查询需要的字段：

```python
@property
def queryset(self):
    # 只查询列表需要的字段
    return Product.all().only('id', 'name', 'price', 'image')
```

### 3. 使用 prefetch_related 优化关联查询

```python
@property
def queryset(self):
    # 预加载关联对象，减少查询次数
    return Product.all().prefetch_related('category', 'brand')
```

### 4. 添加索引

为经常用于过滤和排序的字段添加数据库索引：

```python
class Product(Model):
    name = fields.CharField(max_length=200, index=True)
    price = fields.DecimalField(max_digits=10, decimal_places=2, index=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)
```

## 最佳实践

1. **合理设置每页数量**：通常10-50条为宜，避免过大
2. **限制最大页数**：设置 `max_page_size` 防止滥用
3. **结合过滤使用**：分页应该与过滤、搜索、排序结合使用
4. **优化查询**：使用 `only()`, `prefetch_related()` 等优化查询
5. **缓存总数**：对于不常变化的数据，可以缓存总数
6. **添加索引**：为排序和过滤字段添加数据库索引
7. **返回元数据**：返回总页数、当前页等额外信息方便客户端使用

## 常见问题

### 如何禁用分页？

```python
class ProductViewSet(BaseViewSet):
    pagination_class = None  # 禁用分页
```

### 如何获取所有数据（不分页）？

```bash
# 设置一个很大的 page_size
GET /api/products?page_size=10000
```

或在 ViewSet 中添加自定义操作：

```python
@action(methods=["get"], detail=False, url_path="all")
async def get_all(self, request):
    """获取所有产品（不分页）"""
    products = await Product.all()
    schema = self.get_schema(request, is_safe=True)
    results = [schema.model_validate(p).model_dump() for p in products]
    return json({"results": results})
```

### 如何实现偏移量分页（offset/limit）？

```python
@action(methods=["get"], detail=False, url_path="offset-list")
async def offset_list(self, request):
    """使用 offset/limit 分页"""
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

## 下一步

- 学习 [过滤](filtering.md) 了解如何与分页结合使用
- 阅读 [视图](viewsets.md) 了解 ViewSet 的完整功能
- 查看 [性能优化](../advanced/advanced-features.md) 了解更多优化技巧
