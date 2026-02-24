# 接口权限验证

本文介绍如何使用 SRF 的权限类来控制 API 访问。

## 概述

权限验证是 API 安全的重要组成部分，SRF 提供了灵活的权限系统来控制谁可以访问哪些资源。

## 内置权限类

### IsAuthenticated

要求用户必须已登录。

```python
from srf.views import BaseViewSet
from srf.permission.permission import IsAuthenticated

class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    # 所有操作都需要登录
```

**场景举例**：
- 用户个人资料
- 购物车
- 订单管理
- 收藏和评论

**测试**：

```bash
# 未登录 - 返回 401
curl http://localhost:8000/api/products

# 已登录 - 返回数据
curl http://localhost:8000/api/products \
  -H "Authorization: Bearer your-jwt-token"
```

### IsRoleAdminUser

要求用户必须是管理员角色。

```python
from srf.permission.permission import IsAuthenticated, IsRoleAdminUser

class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsRoleAdminUser)
    
    # 只有管理员可以访问
```

**场景举例**：
- 后台管理
- 用户管理
- 系统配置
- 数据统计

**角色检查逻辑**：

```python
# 检查用户是否有 admin 角色
user = request.ctx.user
if user.role and user.role.name == 'admin':
    # 允许访问
    pass
else:
    # 拒绝访问
    raise Forbidden("需要管理员权限")
```

### IsSafeMethodOnly

仅允许安全的 HTTP 方法（GET、HEAD、OPTIONS）。

```python
from srf.permission.permission import IsSafeMethodOnly

class ProductViewSet(BaseViewSet):
    permission_classes = (IsSafeMethodOnly,)
    
    # 只能读取，不能修改
```

**场景举例**：
- 公开只读 API
- 文档页面
- 产品目录（浏览但不能修改）

**允许的方法**：
- GET - 获取资源
- HEAD - 获取资源头信息
- OPTIONS - 获取支持的方法

## 权限组合

可以同时使用多个权限类，所有权限都必须通过：

```python
class OrderViewSet(BaseViewSet):
    # 必须同时满足：已登录 AND 是管理员
    permission_classes = (IsAuthenticated, IsRoleAdminUser)
```

### 检查顺序

权限按定义顺序检查：

1. `IsAuthenticated` - 检查是否登录
2. `IsRoleAdminUser` - 检查是否为管理员
3. ...

任一权限检查失败，立即返回 403 Forbidden。

## 不同操作使用不同权限

### 方法 1：重写 get_permissions

```python
class ProductViewSet(BaseViewSet):
    def get_permissions(self):
        """根据操作返回不同的权限类"""
        if self.action in ['list', 'retrieve']:
            # 查看：所有人可访问
            return []
        elif self.action == 'create':
            # 创建：需要登录
            return [IsAuthenticated()]
        elif self.action in ['update', 'destroy']:
            # 更新/删除：需要管理员
            return [IsAuthenticated(), IsRoleAdminUser()]
        else:
            return [IsAuthenticated()]
```

### 方法 2：在方法中检查

```python
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    async def destroy(self, request, pk):
        """删除（需要管理员）"""
        # 额外的权限检查
        user = self.get_current_user(request)
        if not user.role or user.role.name != 'admin':
            from sanic.exceptions import Forbidden
            raise Forbidden("需要管理员权限")
        
        # 执行删除
        obj = await self.get_object(request, pk)
        await obj.delete()
        
        from sanic.response import json
        return json({}, status=204)
```

### 方法 3：使用装饰器

```python
from srf.views.decorators import action
from srf.permission.permission import IsRoleAdminUser
from sanic.exceptions import Forbidden

class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
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
        
        from sanic.response import json
        return json({"message": "审核通过"})
```

## 自定义权限类

### 创建权限类

```python
from srf.permission.permission import BasePermission

class IsOwner(BasePermission):
    """要求用户是资源的所有者"""
    
    def has_object_permission(self, request, view, obj):
        # 检查对象是否有 owner 或 user 属性
        if hasattr(obj, 'owner'):
            return obj.owner == request.ctx.user
        if hasattr(obj, 'user'):
            return obj.user == request.ctx.user
        return False
```

### 使用自定义权限

```python
from permissions import IsOwner

class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)
    
    # 用户只能访问自己的订单
```

### 高级权限类

```python
class IsOwnerOrAdmin(BasePermission):
    """所有者或管理员可访问"""
    
    def has_object_permission(self, request, view, obj):
        user = request.ctx.user
        
        # 管理员可以访问
        if user.role and user.role.name == 'admin':
            return True
        
        # 所有者可以访问
        if hasattr(obj, 'user_id'):
            return obj.user_id == user.id
        
        return False
```

## 对象级权限

对象级权限在获取具体对象后检查。

### 基本用法

```python
class IsOwner(BasePermission):
    """对象级权限：检查是否是所有者"""
    
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.ctx.user.id

class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)
    
    # 用户只能查看、修改、删除自己的订单
```

### 自定义检查逻辑

```python
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    async def check_object_permissions(self, request, obj):
        """自定义对象权限检查"""
        # 先执行默认的权限检查
        await super().check_object_permissions(request, obj)
        
        user = self.get_current_user(request)
        
        # 检查产品是否已发布
        if not obj.is_published and not user.is_staff:
            from sanic.exceptions import Forbidden
            raise Forbidden("产品未发布")
        
        # 检查地区限制
        if obj.region and obj.region != user.region:
            from sanic.exceptions import Forbidden
            raise Forbidden("该产品在您的地区不可用")
```

## 权限检查流程

### 视图级权限

在处理请求前检查：

```python
1. 请求到达 ViewSet
   ↓
2. 调用 check_permissions(request)
   ↓
3. 遍历 permission_classes
   ↓
4. 调用每个权限类的 has_permission()
   ↓
5. 所有权限通过 → 继续处理
   任一权限失败 → 返回 403
```

### 对象级权限

在获取对象后检查：

```python
1. 调用 get_object(request, pk)
   ↓
2. 从数据库获取对象
   ↓
3. 调用 check_object_permissions(request, obj)
   ↓
4. 遍历 permission_classes
   ↓
5. 调用每个权限类的 has_object_permission()
   ↓
6. 所有权限通过 → 返回对象
   任一权限失败 → 返回 403
```

## 完整示例

```python
from srf.views import BaseViewSet
from srf.views.decorators import action
from srf.permission.permission import IsAuthenticated, IsRoleAdminUser, BasePermission
from sanic.response import json
from sanic.exceptions import Forbidden
from models import Article
from schemas import ArticleSchemaReader, ArticleSchemaWriter

# 自定义权限类
class IsAuthorOrReadOnly(BasePermission):
    """作者可以编辑，其他人只能读取"""
    
    def has_permission(self, request, view):
        # GET 请求允许所有人
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # 其他请求需要登录
        return hasattr(request.ctx, 'user') and request.ctx.user is not None
    
    def has_object_permission(self, request, view, obj):
        # GET 请求允许所有人
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # 修改和删除需要是作者或管理员
        user = request.ctx.user
        is_author = obj.author_id == user.id
        is_admin = user.role and user.role.name == 'admin'
        
        return is_author or is_admin

class ArticleViewSet(BaseViewSet):
    """文章 ViewSet - 权限示例"""
    
    permission_classes = (IsAuthorOrReadOnly,)
    
    @property
    def queryset(self):
        user = self.get_current_user(request)
        
        # 管理员可以看到所有文章
        if user and user.role and user.role.name == 'admin':
            return Article.all()
        
        # 普通用户只能看到已发布的文章和自己的文章
        if user:
            from tortoise.expressions import Q
            return Article.filter(
                Q(is_published=True) | Q(author_id=user.id)
            )
        
        # 未登录用户只能看到已发布的文章
        return Article.filter(is_published=True)
    
    def get_schema(self, request, is_safe=False):
        return ArticleSchemaReader if is_safe else ArticleSchemaWriter
    
    async def perform_create(self, request, schema):
        """创建文章时自动设置作者"""
        user = self.get_current_user(request)
        data = schema.dict()
        data['author_id'] = user.id
        
        article = await Article.create(**data)
        return article
    
    @action(methods=["post"], detail=True, url_path="publish")
    async def publish(self, request, pk):
        """发布文章（作者或管理员）"""
        article = await self.get_object(request, pk)
        
        # 已经通过 IsAuthorOrReadOnly 检查，这里是额外逻辑
        if article.is_published:
            return json({"error": "文章已发布"}, status=400)
        
        article.is_published = True
        await article.save()
        
        return json({"message": "文章已发布"})
    
    @action(methods=["post"], detail=False, url_path="bulk-publish")
    async def bulk_publish(self, request):
        """批量发布（仅管理员）"""
        # 检查管理员权限
        user = self.get_current_user(request)
        if not user.role or user.role.name != 'admin':
            raise Forbidden("需要管理员权限")
        
        ids = request.json.get("ids", [])
        await Article.filter(id__in=ids).update(is_published=True)
        
        return json({"message": f"成功发布 {len(ids)} 篇文章"})
```

## 权限与认证的关系

- **认证（Authentication）**：验证"你是谁"
- **权限（Permission）**：验证"你能做什么"

```python
# 认证：验证用户身份
@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)  # 设置 request.ctx.user

# 权限：验证用户能否访问
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)  # 检查权限
```

## 最佳实践

1. **最小权限原则**：默认拒绝访问，明确授予必要权限
2. **分离关注点**：将权限逻辑独立到权限类中
3. **清晰的错误消息**：提供友好的权限错误提示
4. **对象级权限**：对敏感资源使用对象级权限检查
5. **测试权限**：为权限类编写单元测试
6. **文档化**：在 API 文档中说明权限要求

## 常见问题

### 如何跳过权限检查？

```python
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    @action(methods=["get"], detail=False)
    async def public_list(self, request):
        """公开列表（跳过权限检查）"""
        # 手动实现，不触发权限检查
        products = await Product.filter(is_public=True)
        # ...
```

### 如何为特定用户角色设置权限？

```python
class HasRole(BasePermission):
    """检查用户是否有指定角色"""
    
    def __init__(self, *roles):
        self.roles = roles
    
    def has_permission(self, request, view):
        user = request.ctx.user if hasattr(request.ctx, 'user') else None
        if not user:
            return False
        
        return user.role and user.role.name in self.roles

# 使用
class AdminViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, HasRole('admin', 'moderator'))
```

## 下一步

- 学习 [认证](authentication.md) 了解用户身份验证
- 阅读 [权限详解](permissions.md) 了解完整的权限系统
- 查看 [认证中间件](../advanced/middleware/auth-middleware.md) 了解底层机制
