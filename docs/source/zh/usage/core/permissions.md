# 权限

权限系统用于控制用户对 API 端点和资源的访问权限。SRF 提供了灵活的权限检查机制，支持视图级和对象级权限。

## 权限基础

### BasePermission

所有权限类都继承自 `BasePermission`，它定义了两个核心方法：

```python
from srf.permission.permission import BasePermission

class BasePermission:
    """权限基类"""
    
    def has_permission(self, request, view):
        """视图级权限检查
        
        Args:
            request: 请求对象
            view: ViewSet 实例
        
        Returns:
            bool: True 表示有权限，False 表示无权限
        """
        return True
    
    def has_object_permission(self, request, view, obj):
        """对象级权限检查
        
        Args:
            request: 请求对象
            view: ViewSet 实例
            obj: 要访问的对象
        
        Returns:
            bool: True 表示有权限，False 表示无权限
        """
        return True
```

### 权限检查流程

1. **视图级权限**：在处理请求前，检查用户是否有权访问该端点
2. **对象级权限**：在获取具体对象后，检查用户是否有权访问该对象

## 内置权限类

### IsAuthenticated

要求用户必须已登录。

```python
from srf.views import BaseViewSet
from srf.permission.permission import IsAuthenticated

class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
```

**实现**：

```python
class IsAuthenticated(BasePermission):
    """要求用户必须已认证"""
    
    def has_permission(self, request, view):
        user = request.ctx.user if hasattr(request.ctx, 'user') else None
        return user is not None and user.is_active
```

**适用场景**：
- 用户个人资料
- 购物车
- 订单管理
- 收藏和评论

### IsRoleAdminUser

要求用户必须是管理员角色。

```python
from srf.permission.permission import IsAuthenticated, IsRoleAdminUser

class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsRoleAdminUser)
```

**实现**：

```python
class IsRoleAdminUser(BasePermission):
    """要求用户角色为 admin"""
    
    def has_permission(self, request, view):
        user = request.ctx.user if hasattr(request.ctx, 'user') else None
        if not user:
            return False
        
        role = user.role if hasattr(user, 'role') else None
        return role and role.name == 'admin'
```

**适用场景**：
- 后台管理
- 用户管理
- 系统配置
- 数据统计

### IsSafeMethodOnly

仅允许安全的 HTTP 方法（GET、HEAD、OPTIONS）。

```python
from srf.permission.permission import IsSafeMethodOnly

class ProductViewSet(BaseViewSet):
    permission_classes = (IsSafeMethodOnly,)
```

**实现**：

```python
class IsSafeMethodOnly(BasePermission):
    """仅允许安全方法"""
    
    SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')
    
    def has_permission(self, request, view):
        return request.method in self.SAFE_METHODS
```

**适用场景**：
- 公开只读 API
- 文档页面
- 产品目录（浏览但不能修改）

## 自定义权限类

### 简单权限

创建自定义权限类：

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

使用自定义权限：

```python
from permissions import IsOwner

class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)
```

### 复杂权限

基于角色和操作类型的权限：

```python
class ProductPermission(BasePermission):
    """产品权限：
    - 所有人可以查看
    - 登录用户可以创建
    - 管理员可以修改和删除
    """
    
    def has_permission(self, request, view):
        # GET 请求：所有人可访问
        if request.method == 'GET':
            return True
        
        # POST 请求：需要登录
        if request.method == 'POST':
            user = request.ctx.user if hasattr(request.ctx, 'user') else None
            return user is not None
        
        # PUT、PATCH、DELETE：需要管理员
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            user = request.ctx.user if hasattr(request.ctx, 'user') else None
            if not user:
                return False
            role = user.role if hasattr(user, 'role') else None
            return role and role.name == 'admin'
        
        return False
```

### 异步权限检查

权限类支持异步方法：

```python
class IsProductOwner(BasePermission):
    """检查用户是否是产品的创建者"""
    
    async def has_object_permission(self, request, view, obj):
        # 可以执行异步数据库查询
        creator = await obj.creator
        return creator.id == request.ctx.user.id
```

## 权限组合

### 使用多个权限类

权限类按顺序检查，所有权限都必须通过：

```python
class OrderViewSet(BaseViewSet):
    # 必须同时满足：已登录 AND 是所有者
    permission_classes = (IsAuthenticated, IsOwner)
```

### 条件权限

根据不同操作使用不同权限：

```python
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    def get_permissions(self):
        """根据操作返回不同的权限类"""
        if self.action in ['update', 'destroy']:
            # 更新和删除需要管理员权限
            return [IsAuthenticated(), IsRoleAdminUser()]
        elif self.action == 'create':
            # 创建只需要登录
            return [IsAuthenticated()]
        else:
            # 列表和详情不需要权限
            return []
```

## 对象级权限

对象级权限在获取具体对象后检查，用于细粒度的访问控制。

### 基本用法

```python
class IsOwner(BasePermission):
    """对象级权限：检查是否是所有者"""
    
    def has_object_permission(self, request, view, obj):
        return obj.owner_id == request.ctx.user.id

class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)
    
    # 用户只能查看、修改、删除自己的订单
```

### 自定义对象权限检查

重写 `check_object_permissions` 方法：

```python
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    async def check_object_permissions(self, request, obj):
        """自定义对象权限检查"""
        # 先执行默认的权限检查
        await super().check_object_permissions(request, obj)
        
        # 额外的业务逻辑检查
        user = self.get_current_user(request)
        
        # 检查产品是否已发布
        if not obj.is_published and not user.is_staff:
            from sanic.exceptions import Forbidden
            raise Forbidden("产品未发布")
        
        # 检查地区限制
        if obj.region and obj.region != user.region:
            raise Forbidden("该产品在您的地区不可用")
```

### 多条件对象权限

```python
class CommentPermission(BasePermission):
    """评论权限：所有者或管理员可以修改/删除"""
    
    def has_object_permission(self, request, view, obj):
        user = request.ctx.user
        
        # 安全方法：所有人可以访问
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # 修改/删除：所有者或管理员
        is_owner = obj.user_id == user.id
        is_admin = user.role and user.role.name == 'admin'
        
        return is_owner or is_admin
```

## 权限示例

### 示例 1：博客文章权限

```python
class ArticlePermission(BasePermission):
    """文章权限：
    - 所有人可以查看已发布的文章
    - 作者可以查看、编辑自己的所有文章
    - 管理员可以操作所有文章
    """
    
    def has_permission(self, request, view):
        # GET 列表：所有人可访问
        if request.method == 'GET' and view.action == 'list':
            return True
        
        # 其他操作需要登录
        return hasattr(request.ctx, 'user') and request.ctx.user is not None
    
    def has_object_permission(self, request, view, obj):
        user = request.ctx.user
        
        # 管理员可以操作所有文章
        if user.role and user.role.name == 'admin':
            return True
        
        # GET 请求：已发布的文章或作者自己的文章
        if request.method == 'GET':
            return obj.is_published or obj.author_id == user.id
        
        # 修改/删除：仅作者
        return obj.author_id == user.id

class ArticleViewSet(BaseViewSet):
    permission_classes = (ArticlePermission,)
    
    @property
    def queryset(self):
        user = self.get_current_user(request)
        
        # 管理员可以看到所有文章
        if user and user.role and user.role.name == 'admin':
            return Article.all()
        
        # 普通用户只能看到已发布的文章
        return Article.filter(is_published=True)
```

### 示例 2：订单权限

```python
class OrderPermission(BasePermission):
    """订单权限：
    - 用户只能访问自己的订单
    - 管理员可以访问所有订单
    """
    
    def has_permission(self, request, view):
        # 所有操作都需要登录
        return hasattr(request.ctx, 'user') and request.ctx.user is not None
    
    async def has_object_permission(self, request, view, obj):
        user = request.ctx.user
        
        # 管理员可以访问所有订单
        if user.role and user.role.name == 'admin':
            return True
        
        # 用户只能访问自己的订单
        return obj.user_id == user.id

class OrderViewSet(BaseViewSet):
    permission_classes = (OrderPermission,)
    
    @property
    def queryset(self):
        user = self.get_current_user(request)
        
        # 管理员可以看到所有订单
        if user and user.role and user.role.name == 'admin':
            return Order.all()
        
        # 普通用户只能看到自己的订单
        return Order.filter(user_id=user.id)
    
    @action(methods=["post"], detail=True, url_path="cancel")
    async def cancel_order(self, request, pk):
        """取消订单"""
        order = await self.get_object(request, pk)
        
        # 额外的业务逻辑检查
        if order.status != 'pending':
            from sanic.response import json
            return json({"error": "只能取消待处理的订单"}, status=400)
        
        order.status = 'cancelled'
        await order.save()
        
        from sanic.response import json
        return json({"message": "订单已取消"})
```

### 示例 3：团队协作权限

```python
class TeamMemberPermission(BasePermission):
    """团队成员权限：
    - 团队成员可以查看
    - 团队所有者可以修改
    """
    
    async def has_object_permission(self, request, view, obj):
        user = request.ctx.user
        
        # 检查用户是否是团队成员
        is_member = await obj.members.filter(id=user.id).exists()
        
        # GET 请求：团队成员可访问
        if request.method == 'GET':
            return is_member
        
        # 修改/删除：仅团队所有者
        return obj.owner_id == user.id

class ProjectViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, TeamMemberPermission)
```

## 权限错误处理

### 自动处理

SRF 会自动处理权限检查失败：

- 未登录：返回 401 Unauthorized
- 权限不足：返回 403 Forbidden

### 自定义错误消息

```python
from sanic.exceptions import Forbidden

class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.owner_id != request.ctx.user.id:
            raise Forbidden("您没有权限访问此资源")
        return True
```

### 捕获权限错误

```python
from sanic.exceptions import Forbidden, Unauthorized

@app.exception(Forbidden)
async def handle_forbidden(request, exception):
    from sanic.response import json
    return json({
        "error": "权限不足",
        "message": str(exception)
    }, status=403)

@app.exception(Unauthorized)
async def handle_unauthorized(request, exception):
    from sanic.response import json
    return json({
        "error": "未登录",
        "message": "请先登录"
    }, status=401)
```

## 完整示例

```python
# permissions.py
from srf.permission.permission import BasePermission

class IsOwnerOrAdmin(BasePermission):
    """所有者或管理员权限"""
    
    async def has_object_permission(self, request, view, obj):
        user = request.ctx.user
        
        # 管理员
        if user.role and user.role.name == 'admin':
            return True
        
        # 所有者
        if hasattr(obj, 'owner_id'):
            return obj.owner_id == user.id
        if hasattr(obj, 'user_id'):
            return obj.user_id == user.id
        
        return False

class IsPublishedOrOwner(BasePermission):
    """已发布或所有者可访问"""
    
    def has_object_permission(self, request, view, obj):
        # 已发布的内容所有人可访问
        if hasattr(obj, 'is_published') and obj.is_published:
            return True
        
        # 未发布的内容仅所有者可访问
        user = request.ctx.user
        if not user:
            return False
        
        return obj.user_id == user.id

# viewsets.py
from srf.views import BaseViewSet
from srf.permission.permission import IsAuthenticated
from permissions import IsOwnerOrAdmin, IsPublishedOrOwner

class ArticleViewSet(BaseViewSet):
    """文章 ViewSet"""
    
    @property
    def queryset(self):
        return Article.all()
    
    def get_schema(self, request, is_safe=False):
        return ArticleSchemaReader if is_safe else ArticleSchemaWriter
    
    def get_permissions(self):
        """根据操作返回不同权限"""
        if self.action in ['list', 'retrieve']:
            # 查看：已发布或所有者
            return [IsPublishedOrOwner()]
        elif self.action == 'create':
            # 创建：需要登录
            return [IsAuthenticated()]
        else:
            # 更新/删除：所有者或管理员
            return [IsAuthenticated(), IsOwnerOrAdmin()]
```

## 最佳实践

1. **最小权限原则**：默认拒绝访问，明确授予必要权限
2. **分离关注点**：将权限逻辑独立到权限类中
3. **组合权限**：使用多个简单权限类组合实现复杂权限
4. **对象级权限**：对敏感资源使用对象级权限检查
5. **异步支持**：在需要数据库查询时使用异步方法
6. **清晰的错误消息**：提供友好的权限错误提示
7. **测试权限**：为权限类编写单元测试

## 常见问题

### 如何跳过某些操作的权限检查？

```python
class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    @action(methods=["get"], detail=False)
    async def public_list(self, request):
        """公开的产品列表（跳过权限检查）"""
        # 手动实现，不会触发权限检查
        products = await Product.filter(is_public=True)
        # ...
```

### 如何为自定义操作添加特定权限？

```python
from srf.permission.permission import IsRoleAdminUser

class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    @action(methods=["post"], detail=True)
    async def publish(self, request, pk):
        """发布产品（需要管理员权限）"""
        # 手动检查管理员权限
        perm = IsRoleAdminUser()
        if not perm.has_permission(request, self):
            from sanic.exceptions import Forbidden
            raise Forbidden("需要管理员权限")
        
        # ...
```

## 下一步

- 学习 [认证](authentication.md) 了解用户身份验证
- 阅读 [视图](viewsets.md) 了解如何在 ViewSet 中使用权限
- 查看 [认证中间件](../advanced/middleware/auth-middleware.md) 了解权限检查的底层机制
