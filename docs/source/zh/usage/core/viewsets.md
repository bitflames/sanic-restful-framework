# 视图（ViewSet）

ViewSet 是 SRF 的核心概念之一，它提供了一种优雅的方式来组织和管理 RESTful API 端点。

## 什么是 ViewSet？

ViewSet 是一个基于类的视图，它将相关的 API 操作组织在一起。一个 ViewSet 通常对应一个资源类型（如产品、订单等），并提供该资源的 CRUD（创建、读取、更新、删除）操作。

### 基本概念

- **资源导向**：每个 ViewSet 对应一个资源类型
- **自动路由**：自动生成 RESTful 路由
- **Mixin 模式**：通过 Mixin 组合功能
- **灵活扩展**：支持自定义操作

## BaseViewSet

`BaseViewSet` 是所有 ViewSet 的基类，它继承了所有 CRUD Mixin。

### 基本用法

```python
from srf.views import BaseViewSet
from models import Product
from schemas import ProductSchemaReader, ProductSchemaWriter

class ProductViewSet(BaseViewSet):
    """产品 ViewSet"""
    
    @property
    def queryset(self):
        """返回查询集"""
        return Product.all()
    
    def get_schema(self, request, is_safe=False):
        """返回 Schema
        
        Args:
            request: 请求对象
            is_safe: True 表示读取操作，False 表示写入操作
        """
        return ProductSchemaReader if is_safe else ProductSchemaWriter
```

### 必需属性和方法

#### 1. `queryset` 属性

定义数据查询集，必须返回 Tortoise ORM 查询对象。

```python
@property
def queryset(self):
    """返回所有产品"""
    return Product.all()

# 带过滤的查询集
@property
def queryset(self):
    """只返回已发布的产品"""
    return Product.filter(is_published=True)

# 带预加载的查询集
@property
def queryset(self):
    """预加载关联对象"""
    return Product.all().prefetch_related("category", "tags")
```

#### 2. `get_schema` 方法

返回用于数据验证和序列化的 Pydantic Schema。

```python
def get_schema(self, request, is_safe=False):
    """
    在同一个请求中可能使用不用的schema，比如输入或输出要控制不同的字段，输入就使用不安全的schema

    is_safe=True: 读取操作（GET），使用 Reader Schema
    is_safe=False: 写入操作（POST/PUT/PATCH），使用 Writer Schema
    """
    return ProductSchemaReader if is_safe else ProductSchemaWriter
```

**为什么要分离读写 Schema？**

- **安全性**：写入时排除只读字段（如 id, created_at）
- **灵活性**：读取时可以包含计算字段、关联数据
- **验证**：写入时有更严格的验证规则

示例：

```python
from pydantic import BaseModel, Field
from typing import Optional

class ProductSchemaWriter(BaseModel):
    """写入 Schema - 用于创建和更新"""
    name: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = None
    category_id: int

class ProductSchemaReader(BaseModel):
    """读取 Schema - 用于序列化"""
    id: int
    name: str
    price: float
    description: Optional[str]
    category_id: int
    category_name: str  # 额外的关联字段
    created_at: str
    
    class Config:
        from_attributes = True
```

## CRUD 操作

BaseViewSet 通过 Mixin 提供了标准的 CRUD 操作。

### ListModelMixin - 列表操作

**路由**: `GET /api/products`

**功能**：
- 获取资源列表
- 支持分页
- 支持过滤和搜索
- 支持排序

**响应格式**：

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
    }
  ]
}
```

**自定义 list 方法**：

```python
class ProductViewSet(BaseViewSet):
    async def list(self, request):
        """自定义列表逻辑"""
        # 获取查询集
        queryset = self.queryset
        
        # 应用过滤
        if "category" in request.args:
            category_id = request.args.get("category")
            queryset = queryset.filter(category_id=category_id)
        
        # 应用过滤器类
        for filter_class in self.filter_class:
            queryset = await filter_class().filter_queryset(request, queryset)
        
        # 分页
        from srf.paginator import PaginationHandler
        paginator = PaginationHandler.from_queryset(queryset, request)
        schema = self.get_schema(request, is_safe=True)
        result = await paginator.to_dict(schema)
        
        from sanic.response import json
        return json(result)
```

### CreateModelMixin - 创建操作

**路由**: `POST /api/products`

**功能**：创建新资源

**请求体**：

```json
{
  "name": "新产品",
  "price": 99.99,
  "description": "产品描述",
  "category_id": 1
}
```

**响应**：

```json
{
  "id": 1,
  "name": "新产品",
  "price": 99.99,
  "description": "产品描述",
  "category_id": 1,
  "created_at": "2026-02-07 10:00:00"
}
```

**自定义创建逻辑**：

```python
class ProductViewSet(BaseViewSet):
    async def perform_create(self, request, schema):
        """自定义创建逻辑
        
        Args:
            request: 请求对象
            schema: 已验证的 Pydantic Schema 实例
        
        Returns:
            创建的模型实例
        """
        # 添加额外字段
        data = schema.dict()
        data["created_by"] = request.ctx.user.id
        
        # 创建对象
        obj = await Product.create(**data)
        
        # 执行其他操作（如发送通知）
        await self.send_notification(obj)
        
        return obj
    
    async def send_notification(self, product):
        """发送通知"""
        # 实现通知逻辑
        pass
```

### RetrieveModelMixin - 详情操作

**路由**: `GET /api/products/<pk>`

**功能**：获取单个资源

**响应**：

```json
{
  "id": 1,
  "name": "产品1",
  "price": 99.99,
  "description": "产品描述",
  "category_id": 1,
  "category_name": "电子产品",
  "created_at": "2026-02-07 10:00:00"
}
```

**自定义获取逻辑**：

```python
class ProductViewSet(BaseViewSet):
    async def retrieve(self, request, pk):
        """自定义获取逻辑"""
        # 获取对象
        obj = await self.get_object(request, pk)
        
        # 记录访问
        await self.log_view(obj, request.ctx.user)
        
        # 序列化
        schema = self.get_schema(request, is_safe=True)
        data = schema.model_validate(obj).model_dump()
        
        from sanic.response import json
        return json(data)
    
    async def log_view(self, product, user):
        """记录浏览"""
        # 实现浏览记录逻辑
        pass
```

### UpdateModelMixin - 更新操作

**路由**: `PUT /api/products/<pk>` 或 `PATCH /api/products/<pk>`

**功能**：更新资源

**请求体**：

```json
{
  "name": "更新后的产品名",
  "price": 109.99
}
```

**响应**：

```json
{
  "id": 1,
  "name": "更新后的产品名",
  "price": 109.99,
  "updated_at": "2026-02-07 11:00:00"
}
```

**自定义更新逻辑**：

```python
class ProductViewSet(BaseViewSet):
    async def perform_update(self, request, obj, schema):
        """自定义更新逻辑
        
        Args:
            request: 请求对象
            obj: 要更新的模型实例
            schema: 已验证的 Pydantic Schema 实例
        
        Returns:
            更新后的模型实例
        """
        # 记录变更
        old_price = obj.price
        
        # 更新对象
        update_data = schema.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(obj, field, value)
        await obj.save()
        
        # 如果价格变化，发送通知
        if old_price != obj.price:
            await self.notify_price_change(obj, old_price)
        
        return obj
    
    async def notify_price_change(self, product, old_price):
        """通知价格变化"""
        # 实现通知逻辑
        pass
```

### DestroyModelMixin - 删除操作

**路由**: `DELETE /api/products/<pk>`

**功能**：删除资源

**响应**：HTTP 204 No Content

**自定义删除逻辑**：

```python
class ProductViewSet(BaseViewSet):
    async def perform_destroy(self, request, obj):
        """自定义删除逻辑
        
        Args:
            request: 请求对象
            obj: 要删除的模型实例
        """
        # 软删除
        obj.is_deleted = True
        await obj.save()
        
        # 或硬删除
        # await obj.delete()
        
        # 清理关联数据
        await self.cleanup_related(obj)
    
    async def cleanup_related(self, product):
        """清理关联数据"""
        # 删除相关的图片、评论等
        pass
```

## 自定义操作 - @action 装饰器

`@action` 装饰器用于添加自定义操作到 ViewSet。

### 基本用法

```python
from srf.views.decorators import action
from sanic.response import json

class ProductViewSet(BaseViewSet):
    @action(methods=["get"], detail=False, url_path="featured")
    async def list_featured(self, request):
        """获取推荐产品（集合级操作）"""
        products = await Product.filter(is_featured=True)
        schema = self.get_schema(request, is_safe=True)
        data = [schema.model_validate(p).model_dump() for p in products]
        return json({"results": data})
    
    @action(methods=["post"], detail=True, url_path="publish")
    async def publish(self, request, pk):
        """发布产品（详情级操作）"""
        product = await self.get_object(request, pk)
        product.is_published = True
        product.published_at = datetime.now()
        await product.save()
        
        return json({"message": "产品已发布"})
```

### 装饰器参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `methods` | list | HTTP 方法列表 | `["get"]` |
| `detail` | bool | 是否为详情级操作 | `False` |
| `url_path` | str | URL 路径 | 方法名 |
| `url_name` | str | 路由名称 | 方法名 |

### 集合级 vs 详情级操作

**集合级操作** (`detail=False`)：

- 不需要 pk 参数
- URL: `/api/products/featured`
- 示例：获取推荐列表、批量操作

```python
@action(methods=["get"], detail=False)
async def featured(self, request):
    """集合级操作"""
    # 不需要 pk
    pass
```

**详情级操作** (`detail=True`)：

- 需要 pk 参数
- URL: `/api/products/<pk>/publish`
- 示例：发布、激活、归档

```python
@action(methods=["post"], detail=True)
async def publish(self, request, pk):
    """详情级操作"""
    # 需要 pk 参数
    product = await self.get_object(request, pk)
    pass
```

### 高级示例

#### 参考[视图装饰器](viewset-actions.md) 

## ViewSet 配置选项

### 权限控制

```python
from srf.permission.permission import IsAuthenticated, IsRoleAdminUser

class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsRoleAdminUser)
```

### 搜索字段

```python
class ProductViewSet(BaseViewSet):
    search_fields = ["name", "description", "sku"]
```

### 过滤字段

```python
class ProductViewSet(BaseViewSet):
    filter_fields = {
        "category": "category_id",
        "min_price": "price__gte",
        "max_price": "price__lte",
        "is_published": "is_published",
    }
```

### 排序字段

```python
class ProductViewSet(BaseViewSet):
    ordering_fields = {
        "price": "price",
        "name": "name",
        "created": "created_at",
    }
```

### 过滤器类

```python
from srf.filters.filter import SearchFilter, JsonLogicFilter, QueryParamFilter, OrderingFactory

class ProductViewSet(BaseViewSet):
    filter_class = [
        SearchFilter,
        JsonLogicFilter,
        QueryParamFilter,
        OrderingFactory,
    ]
```

## 完整示例

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.permission.permission import IsAuthenticated, IsRoleAdminUser
from sanic.response import json
from models import Product
from schemas import ProductSchemaReader, ProductSchemaWriter
from datetime import datetime

class ProductViewSet(BaseViewSet):
    """产品 ViewSet - 完整示例"""
    
    # 权限配置
    permission_classes = (IsAuthenticated,)
    
    # 搜索配置
    search_fields = ["name", "description", "sku"]
    
    # 过滤配置
    filter_fields = {
        "category": "category_id",
        "min_price": "price__gte",
        "max_price": "price__lte",
    }
    
    # 排序配置
    ordering_fields = {
        "price": "price",
        "name": "name",
        "created": "created_at",
    }
    
    @property
    def queryset(self):
        """返回查询集"""
        return Product.all().prefetch_related("category")
    
    def get_schema(self, request, is_safe=False):
        """返回 Schema"""
        return ProductSchemaReader if is_safe else ProductSchemaWriter
    
    # 自定义创建逻辑
    async def perform_create(self, request, schema):
        """创建产品"""
        data = schema.dict()
        data["created_by"] = request.ctx.user.id
        return await Product.create(**data)
    
    # 自定义更新逻辑
    async def perform_update(self, request, obj, schema):
        """更新产品"""
        update_data = schema.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(obj, field, value)
        obj.updated_by = request.ctx.user.id
        await obj.save()
        return obj
    
    # 集合级自定义操作
    @action(methods=["get"], detail=False, url_path="featured")
    async def list_featured(self, request):
        """获取推荐产品"""
        products = await Product.filter(is_featured=True)
        schema = self.get_schema(request, is_safe=True)
        data = [schema.model_validate(p).model_dump() for p in products]
        return json({"results": data})
    
    # 详情级自定义操作
    @action(methods=["post"], detail=True, url_path="publish")
    async def publish(self, request, pk):
        """发布产品"""
        product = await self.get_object(request, pk)
        
        if product.is_published:
            return json({"error": "产品已发布"}, status=400)
        
        product.is_published = True
        product.published_at = datetime.now()
        await product.save()
        
        return json({"message": "产品已发布"})
```

## 最佳实践

1. **保持 ViewSet 简洁**：复杂逻辑应该放在 Service 层或 Manager 中
2. **使用 perform_* 方法**：重写 `perform_create`、`perform_update` 等方法来自定义逻辑
3. **合理使用 @action**：为特定的业务操作添加自定义端点
4. **权限检查**：始终为敏感操作添加权限检查
5. **异常处理**：捕获并处理可能的异常
6. **文档字符串**：为方法添加清晰的文档字符串

## 下一步

- 学习 [路由](routing.md) 了解如何注册 ViewSet
- 阅读 [权限](permissions.md) 了解权限系统
- 查看 [过滤](filtering.md) 了解数据过滤
