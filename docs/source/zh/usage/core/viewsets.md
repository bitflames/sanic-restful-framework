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
下文中未重复导入的代码块是添加到已有 ViewSet 的方法片段，继续使用基本用法
中的 `BaseViewSet`、`Product` 和 Schema 导入。

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

    def get_schema(self):
        """按 HTTP 方法选择读写 Schema；self.request 已由 as_view 设置。"""
        return ProductSchemaReader if self.request.is_safe else ProductSchemaWriter
```

### 必需属性和方法

#### 1. `queryset` / `get_queryset`

提供 Tortoise ORM 查询集。按请求做数据范围限制时优先重写 `get_queryset()`；也可以设置名为 `queryset` 的类属性或 `@property`，默认的 `get_queryset()` 会读取它（若是 `QuerySet` 会用 `.all()` 克隆）。

`list()` 使用 `filter_queryset(self.get_queryset())`。`get_object()` 与 `perform_create()` 同样走 `get_queryset()`。

```python
# 类属性
queryset = Product.all()


# 或 property（仍由 get_queryset 读取）
@property
def queryset(self):
    """只返回已发布的产品"""
    return Product.filter(is_published=True)


# 或重写 get_queryset，按请求限定范围
def get_queryset(self):
    return Product.filter(owner_id=self.request.ctx.user.id).prefetch_related("category", "tags")
```

#### 2. `get_schema` 方法

返回用于数据验证和序列化的 Pydantic Schema。

固定使用一个 Schema 时，设置类属性 `schema` 即可。需要按请求或操作选择时，重写
`get_schema()`；选择方式和内置 `create` / `update` 如何使用返回的 Schema，见
[Schema 选择说明](schema.md)。

**为什么要分离读写 Schema？**

- **安全性**：写入时排除只读字段（如 id, created_at）
- **灵活性**：读取时可以包含计算字段、关联数据
- **验证**：写入时有更严格的验证规则

示例：

```python
from pydantic import BaseModel, Field, ConfigDict
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

    model_config = ConfigDict(from_attributes=True)
```

## CRUD 操作

BaseViewSet 通过 Mixin 提供了标准的 CRUD 操作。

### ListModelMixin - 列表操作

**路由**: `GET /api/products`

**功能**：

- 获取资源列表
- 支持分页
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
from sanic.response import json
from srf.paginator import PageNumberPagination


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
            queryset = filter_class(self).filter_queryset(request, queryset)

        paginator = PageNumberPagination.from_queryset(queryset, request)
        schema = self.get_schema()
        result = await paginator.to_dict(schema)

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
    async def perform_create(self, sch_model):
        """自定义创建逻辑

        Args:
            sch_model: 已验证的 Pydantic Schema 实例

        需要 request 时使用 self.request（as_view 会赋值）。
        """
        data = sch_model.model_dump(exclude_unset=True, by_alias=False)
        data["created_by"] = self.request.ctx.user.id

        obj = await Product.create(**data)
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
        obj = await self.get_object(pk)

        # 记录访问
        await self.log_view(obj, request.ctx.user)

        # 序列化
        schema = self.get_schema()
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
  "price": 109.99,
  "description": "产品描述",
  "category_id": 1
}
```

!!! warning "当前不是部分更新"
`update()` 会用 `get_schema()` 返回的 Schema 以 `strict=True` 校验完整请求体，
并且 `PUT` 与 `PATCH` 映射到同一个方法。请求体必须满足该 Schema 的必填字段；
`perform_update()` 中的 `exclude_unset=True` 只决定“校验通过后哪些字段写回数据库”，
不代表可以省略必填字段。

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
    async def perform_update(self, sch_model, orm_model):
        """自定义更新逻辑

        Args:
            sch_model: 已验证的 Pydantic Schema 实例
            orm_model: 要更新的 ORM 模型实例

        Returns:
            更新后的模型实例
        """
        # 记录变更
        old_price = orm_model.price

        # 更新对象
        update_data = sch_model.model_dump(exclude_unset=True, exclude_none=True, exclude=["id"], by_alias=False)
        for field, value in update_data.items():
            if hasattr(orm_model, field):
                setattr(orm_model, field, value)
        await orm_model.save()

        # 如果价格变化，发送通知
        if old_price != orm_model.price:
            await self.notify_price_change(orm_model, old_price)

        return orm_model

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
    async def perform_destroy(self, orm_model):
        """自定义删除逻辑

        Args:
            orm_model: 要删除的 ORM 模型实例
        """
        # 软删除
        orm_model.is_deleted = True
        await orm_model.save()

        # 或硬删除
        # await orm_model.delete()

        # 清理关联数据
        await self.cleanup_related(orm_model)

    async def cleanup_related(self, product):
        """清理关联数据"""
        # 删除相关的图片、评论等
        pass
```

## 自定义操作 - @action 装饰器

`@action` 用来添加 CRUD 之外的端点：`detail=False` 注册为
`/api/products/<url_path>`，`detail=True` 注册为 `/api/products/<pk>/<url_path>`。
参数、示例、权限检查等完整说明见 [ViewSet 装饰器](viewset-actions.md)。

## ViewSet 配置选项

### 权限控制

```python
from srf.permission.permission import IsAuthenticated, SuperuserOnly


class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, SuperuserOnly)
```

### 搜索字段

三个字段配置默认均为空列表 `[]`，也接受字典。列表中的字段名直接映射到同名 ORM 字段；字典值指定 ORM 字段名，`filter_fields` 和 `ordering_fields` 的键分别作为查询参数名和排序名。详见[过滤](filtering.md)。

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
class ProductViewSet(BaseViewSet):
    filter_class = [
        SearchFilter,
        QueryParamFilter,
        OrderingFactory,
    ]
```

## 完整示例

```python
from srf.views import BaseViewSet
from srf.permission.permission import IsAuthenticated
from models import Product
from schemas import ProductSchemaReader, ProductSchemaWriter


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

    def get_schema(self):
        """根据 HTTP 方法选择 Schema。"""
        return ProductSchemaReader if self.request.is_safe else ProductSchemaWriter

    # 自定义创建逻辑
    async def perform_create(self, sch_model):
        """创建产品；需要 request 时用 self.request"""
        data = sch_model.model_dump(exclude_unset=True, by_alias=False)
        data["created_by"] = self.request.ctx.user.id
        return await Product.create(**data)

    # 自定义更新逻辑
    async def perform_update(self, sch_model, orm_model):
        """更新产品"""
        update_data = sch_model.model_dump(exclude_unset=True, exclude_none=True, exclude=["id"], by_alias=False)
        for field, value in update_data.items():
            if hasattr(orm_model, field):
                setattr(orm_model, field, value)
        orm_model.updated_by = self.request.ctx.user.id
        await orm_model.save()
        return orm_model
```

## 最佳实践

1. **保持 ViewSet 简洁**：复杂逻辑应该放在 Service 层或 Manager 中
2. **使用 perform\_\* 方法**：重写 `perform_create`、`perform_update` 等方法来自定义逻辑
3. **合理使用 @action**：为特定的业务操作添加自定义端点
4. **权限检查**：始终为敏感操作添加权限检查
5. **异常处理**：捕获并处理可能的异常
6. **文档字符串**：为方法添加清晰的文档字符串

## 下一步

- 学习 [路由](routing.md) 了解如何注册 ViewSet
- 阅读 [权限](permissions.md) 了解权限系统
- 查看 [过滤](filtering.md) 了解数据过滤
