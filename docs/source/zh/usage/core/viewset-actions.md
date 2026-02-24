# ViewSet 装饰器

ViewSet 装饰器用于扩展和定制 ViewSet 的行为，其中最重要的是 `@action` 装饰器。

## @action 装饰器

`@action` 装饰器用于为 ViewSet 添加自定义操作，超越标准的 CRUD 操作。

### 基本用法

```python
from srf.views import BaseViewSet
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

```python
@action(
    methods: list = ["get"],     # HTTP 方法列表
    detail: bool = False,        # 是否为详情级操作
    url_path: str = None,        # URL 路径（默认为方法名）
    url_name: str = None         # 路由名称（默认为方法名）
)
```

**参数说明**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `methods` | list | `["get"]` | HTTP 方法列表，如 `["get"]`, `["post"]`, `["get", "post"]` |
| `detail` | bool | `False` | `True` 为详情级操作（需要 pk），`False` 为集合级操作 |
| `url_path` | str | 方法名 | 自定义 URL 路径 |
| `url_name` | str | 方法名 | 路由名称，用于 URL 反向解析 |

### 集合级操作 vs 详情级操作

#### 集合级操作 (`detail=False`)

不需要资源 ID，作用于整个集合。

**特点**：
- 不需要 pk 参数
- URL 格式：`/api/products/action-name`
- 适用于批量操作、统计、搜索等

**示例**：

```python
@action(methods=["get"], detail=False, url_path="statistics")
async def get_statistics(self, request):
    """获取产品统计信息"""
    from tortoise.functions import Count, Avg, Sum
    
    stats = await Product.all().annotate(
        total=Count("id"),
        avg_price=Avg("price"),
        total_value=Sum("price")
    ).values("total", "avg_price", "total_value")
    
    return json(stats[0] if stats else {})

@action(methods=["post"], detail=False, url_path="bulk-update")
async def bulk_update(self, request):
    """批量更新产品"""
    ids = request.json.get("ids", [])
    updates = request.json.get("updates", {})
    
    if not ids:
        return json({"error": "请提供产品 ID 列表"}, status=400)
    
    await Product.filter(id__in=ids).update(**updates)
    
    return json({"message": f"成功更新 {len(ids)} 个产品"})

@action(methods=["get"], detail=False, url_path="search")
async def advanced_search(self, request):
    """高级搜索"""
    keyword = request.args.get("q", "")
    category = request.args.get("category")
    
    queryset = Product.all()
    
    if keyword:
        queryset = queryset.filter(name__icontains=keyword)
    
    if category:
        queryset = queryset.filter(category_id=category)
    
    products = await queryset
    schema = self.get_schema(request, is_safe=True)
    data = [schema.model_validate(p).model_dump() for p in products]
    
    return json({"results": data})
```

**生成的路由**：
- `GET /api/products/statistics`
- `POST /api/products/bulk-update`
- `GET /api/products/search`

#### 详情级操作 (`detail=True`)

需要资源 ID，作用于单个资源。

**特点**：
- 需要 pk 参数
- URL 格式：`/api/products/<pk>/action-name`
- 适用于状态变更、关联操作等

**示例**：

```python
@action(methods=["post"], detail=True, url_path="activate")
async def activate(self, request, pk):
    """激活产品"""
    product = await self.get_object(request, pk)
    
    if product.is_active:
        return json({"error": "产品已激活"}, status=400)
    
    product.is_active = True
    await product.save()
    
    return json({"message": "产品已激活"})

@action(methods=["post"], detail=True, url_path="duplicate")
async def duplicate(self, request, pk):
    """复制产品"""
    product = await self.get_object(request, pk)
    
    # 复制产品
    new_product = await Product.create(
        name=f"{product.name} (副本)",
        price=product.price,
        description=product.description,
        category_id=product.category_id
    )
    
    schema = self.get_schema(request, is_safe=True)
    data = schema.model_validate(new_product).model_dump()
    
    return json(data, status=201)

@action(methods=["get"], detail=True, url_path="related")
async def get_related(self, request, pk):
    """获取相关产品"""
    product = await self.get_object(request, pk)
    
    # 同类别的其他产品
    related = await Product.filter(
        category_id=product.category_id
    ).exclude(id=product.id).limit(5)
    
    schema = self.get_schema(request, is_safe=True)
    data = [schema.model_validate(p).model_dump() for p in related]
    
    return json({"results": data})
```

**生成的路由**：
- `POST /api/products/<pk>/activate`
- `POST /api/products/<pk>/duplicate`
- `GET /api/products/<pk>/related`

### 多 HTTP 方法

一个 action 可以支持多个 HTTP 方法：

```python
@action(methods=["get", "post"], detail=True, url_path="comments")
async def handle_comments(self, request, pk):
    """处理评论（GET 获取，POST 添加）"""
    product = await self.get_object(request, pk)
    
    if request.method == "GET":
        # 获取评论
        comments = await product.comments.all()
        return json({"results": [c.to_dict() for c in comments]})
    
    elif request.method == "POST":
        # 添加评论
        content = request.json.get("content")
        comment = await Comment.create(
            product=product,
            user=request.ctx.user,
            content=content
        )
        return json(comment.to_dict(), status=201)
```

### 自定义 URL 路径

使用 `url_path` 参数自定义 URL：

```python
@action(methods=["post"], detail=True, url_path="change-status")
async def change_status(self, request, pk):
    """更改状态"""
    product = await self.get_object(request, pk)
    new_status = request.json.get("status")
    
    product.status = new_status
    await product.save()
    
    return json({"message": "状态已更新"})
```

URL：`POST /api/products/<pk>/change-status`

如果不指定 `url_path`，默认使用方法名（转换为 kebab-case）：

```python
@action(methods=["post"], detail=True)
async def change_status(self, request, pk):
    """更改状态"""
    pass
```

URL：`POST /api/products/<pk>/change_status`

### 自定义路由名称

使用 `url_name` 参数自定义路由名称，用于 URL 反向解析：

```python
@action(methods=["get"], detail=False, url_name="featured_list")
async def featured(self, request):
    """推荐列表"""
    pass

# 反向解析
url = request.app.url_for("products-featured_list")
```

### 权限控制

可以在 action 中进行权限检查：

```python
from srf.permission.permission import IsRoleAdminUser
from sanic.exceptions import Forbidden

@action(methods=["post"], detail=True, url_path="approve")
async def approve(self, request, pk):
    """审核产品（仅管理员）"""
    # 检查管理员权限
    perm = IsRoleAdminUser()
    if not perm.has_permission(request, self):
        raise Forbidden("需要管理员权限")
    
    product = await self.get_object(request, pk)
    product.is_approved = True
    await product.save()
    
    return json({"message": "审核通过"})
```

### 完整示例

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.permission.permission import IsAuthenticated, IsRoleAdminUser
from sanic.response import json
from sanic.exceptions import Forbidden
from datetime import datetime
from models import Product, Comment
from schemas import ProductSchemaReader, ProductSchemaWriter

class ProductViewSet(BaseViewSet):
    """产品 ViewSet - 装饰器示例"""
    
    permission_classes = (IsAuthenticated,)
    
    @property
    def queryset(self):
        return Product.all()
    
    def get_schema(self, request, is_safe=False):
        return ProductSchemaReader if is_safe else ProductSchemaWriter
    
    # 集合级操作
    @action(methods=["get"], detail=False, url_path="featured")
    async def list_featured(self, request):
        """获取推荐产品"""
        products = await Product.filter(is_featured=True, is_active=True)
        schema = self.get_schema(request, is_safe=True)
        data = [schema.model_validate(p).model_dump() for p in products]
        return json({"results": data})
    
    @action(methods=["get"], detail=False, url_path="statistics")
    async def get_statistics(self, request):
        """获取统计信息"""
        from tortoise.functions import Count, Avg
        
        stats = await Product.all().annotate(
            total=Count("id"),
            avg_price=Avg("price")
        ).values("total", "avg_price")
        
        return json(stats[0] if stats else {})
    
    @action(methods=["post"], detail=False, url_path="bulk-delete")
    async def bulk_delete(self, request):
        """批量删除（仅管理员）"""
        # 检查管理员权限
        user = self.get_current_user(request)
        if not user.role or user.role.name != 'admin':
            raise Forbidden("需要管理员权限")
        
        ids = request.json.get("ids", [])
        count = await Product.filter(id__in=ids).delete()
        
        return json({"message": f"成功删除 {count} 个产品"})
    
    # 详情级操作
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
    
    @action(methods=["post"], detail=True, url_path="duplicate")
    async def duplicate(self, request, pk):
        """复制产品"""
        product = await self.get_object(request, pk)
        
        new_product = await Product.create(
            name=f"{product.name} (副本)",
            price=product.price,
            description=product.description,
            category_id=product.category_id
        )
        
        schema = self.get_schema(request, is_safe=True)
        data = schema.model_validate(new_product).model_dump()
        
        return json(data, status=201)
    
    @action(methods=["get", "post"], detail=True, url_path="comments")
    async def handle_comments(self, request, pk):
        """处理评论"""
        product = await self.get_object(request, pk)
        
        if request.method == "GET":
            # 获取评论
            comments = await product.comments.all()
            return json({"results": [c.to_dict() for c in comments]})
        
        elif request.method == "POST":
            # 添加评论
            content = request.json.get("content")
            if not content:
                return json({"error": "评论内容不能为空"}, status=400)
            
            comment = await Comment.create(
                product=product,
                user=request.ctx.user,
                content=content
            )
            return json(comment.to_dict(), status=201)
```

## 最佳实践

1. **语义化命名**：方法名应清晰表达操作意图
2. **适当分组**：相关操作使用一致的 URL 路径前缀
3. **权限检查**：敏感操作添加权限验证
4. **错误处理**：提供友好的错误信息
5. **文档字符串**：为每个 action 添加清晰的文档
6. **HTTP 方法**：遵循 RESTful 约定（GET 查询，POST 创建/操作）
7. **幂等性**：GET 操作应该是幂等的

## 常见模式

### 状态变更

```python
@action(methods=["post"], detail=True, url_path="archive")
async def archive(self, request, pk):
    """归档"""
    obj = await self.get_object(request, pk)
    obj.status = "archived"
    await obj.save()
    return json({"message": "已归档"})
```

### 关联资源

```python
@action(methods=["get"], detail=True, url_path="reviews")
async def get_reviews(self, request, pk):
    """获取评论"""
    obj = await self.get_object(request, pk)
    reviews = await obj.reviews.all()
    return json({"results": [r.to_dict() for r in reviews]})
```

### 批量操作

```python
@action(methods=["post"], detail=False, url_path="bulk-update")
async def bulk_update(self, request):
    """批量更新"""
    ids = request.json.get("ids", [])
    updates = request.json.get("updates", {})
    await Model.filter(id__in=ids).update(**updates)
    return json({"message": "更新成功"})
```

## 下一步

- 阅读 [路由](routing.md) 了解路由系统
- 学习 [权限](permissions.md) 添加权限控制
- 查看 [ViewSet](viewsets.md) 了解 ViewSet 基础
