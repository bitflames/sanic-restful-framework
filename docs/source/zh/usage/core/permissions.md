# 权限

SRF 的权限类用于控制 ViewSet 访问。视图级检查在 handler 前由`check_permissions()` 执行；
对象级检查由 `get_object()` 调用 `check_object_permissions()`（覆盖 retrieve / update / destroy，以及调用 `get_object()` 的自定义 action）。

## 内置权限类

```python
from srf.permission.permission import (
    AllowAny,
    BasePermission,
    IsAuthenticated,
    SuperuserOnly,
    SafeMethodOnly,
)
```

- `AllowAny`：始终允许（`settings.DEFAULT_PERMISSION_CLASSES` 默认值）。
- `IsAuthenticated`：`request.ctx.user` 存在，且用户的 `is_active` 为真。
- `SuperuserOnly`：`request.ctx.user.is_superuser` 为真。
- `SafeMethodOnly`：只允许 GET、HEAD、OPTIONS。

在 ViewSet 上声明权限类：

```python
from srf.permission.permission import IsAuthenticated
from srf.views import BaseViewSet


class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
```

`BaseViewSet.check_permissions()` 会按顺序在**类上**调用
`has_permission(request, view)` 同步和异步返回值都受支持。任一结果为假时抛出
403 Forbidden。没有认证信息时，认证中间件会将 `request.ctx.user` 设为 `None`，由
权限类决定是否允许请求；请求头格式错误、JWT 未配置或用户不存在时认证中间件返回
401，而 Token 缺失或签名/有效期校验失败会按匿名请求处理。

权限方法是 `@staticmethod`：推荐继承 `BasePermission`，但不强制；只要提供同名静态方法即可（鸭式）。

## 自定义视图级权限

```python
from srf.permission.permission import BasePermission


class IsEditor(BasePermission):
    @staticmethod
    def has_permission(request, view=None):
        user = getattr(request.ctx, "user", None)
        # is_editor 是应用自定义字段；SRF 内置 User 只有 is_superuser 和 roles 关系。
        return user is not None and getattr(user, "is_editor", False)
```

`view` 为可选参数；`BaseViewSet` 会传入当前 View 实例。

异步检查同样可用：

```python
from models import Subscription
from srf.permission.permission import BasePermission


class HasActiveSubscription(BasePermission):
    @staticmethod
    async def has_permission(request, view=None):
        user = getattr(request.ctx, "user", None)
        return user is not None and await Subscription.filter(user_id=user.id, active=True).exists()
```

## 按请求方法设置权限

按操作区分权限时，可在 `check_permissions()` 中根据 `self.action` 选择权限类：

```python
import asyncio

from sanic.exceptions import Forbidden
from srf.permission.permission import IsAuthenticated, SuperuserOnly
from srf.views import BaseViewSet


class ProductViewSet(BaseViewSet):
    async def check_permissions(self, request):
        if request.method.upper() in ("GET", "HEAD", "OPTIONS"):
            return

        classes = (IsAuthenticated,) if request.method.upper() == "POST" else (IsAuthenticated, SuperuserOnly)
        for permission_class in classes:
            result = permission_class.has_permission(request, self)
            if asyncio.iscoroutine(result):
                result = await result
            if not result:
                raise Forbidden(message="Forbidden")
```

## 对象级权限

`BasePermission.has_object_permission(request, view, obj)` 定义对象级接口。
`get_object()` 会调用 `check_object_permissions()`，后者在权限类上调用
`has_object_permission(request, view, obj)`，结果为假时抛出 `Forbidden`。

对象级检查不会逐条应用于列表结果。列表接口应在 `queryset` 中限制数据。

### 基本用法

```python
from models import Order
from srf.permission.permission import BasePermission, IsAuthenticated
from srf.views import BaseViewSet


class IsOwner(BasePermission):
    """对象级权限：检查是否是所有者"""

    @staticmethod
    def has_object_permission(request, view=None, obj=None):
        # 用户只能查看、修改、删除自己的对象
        return obj.owner_id == request.ctx.user.id


class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)
```

列表侧通过 `queryset` 限制可见数据：

```python
from models import Order
from srf.permission.permission import IsAuthenticated
from srf.views import BaseViewSet


class OrderViewSet(BaseViewSet):
    @property
    def queryset(self):
        user = self.get_current_user(self.request)
        if user.is_superuser:
            return Order.all()
        return Order.filter(user_id=user.id)
```

`self.request` 由 `BaseViewSet.as_view()` 在处理请求前设置。

## 自定义 action 的权限

所有由 `SanicRouter` 注册的 action 都会先执行 ViewSet 的
`check_permissions()`。如需额外限制，在 action 内执行附加检查：

```python
from sanic.exceptions import Forbidden
from sanic.response import json
from models import Product
from srf.permission.permission import SuperuserOnly
from srf.views import BaseViewSet
from srf.views.decorators import action


class ProductViewSet(BaseViewSet):
    @action(methods=["post"], detail=True, url_path="approve")
    async def approve(self, request, pk):
        if not SuperuserOnly.has_permission(request, self):
            raise Forbidden(message="需要超级用户权限")
        product = await self.get_object(pk)
        product.is_approved = True
        await product.save()
        return json({"message": "审核通过"})
```

## 最佳实践

1. **最小权限原则**：默认拒绝访问，明确授予必要权限
2. **分离关注点**：将权限逻辑独立到权限类中
3. **组合权限**：使用多个简单权限类组合实现复杂权限
4. **对象级权限**：对敏感资源使用对象级权限检查
5. **异步支持**：在需要数据库查询时使用异步方法
6. **清晰的错误消息**：提供友好的权限错误提示
7. **测试权限**：为权限类编写单元测试

## 下一步

- 阅读[认证](authentication.md)了解 JWT 身份验证。
- 阅读[认证与权限配合](auth-permissions.md)查看组合示例。
- 查看[认证中间件](../advanced/middleware/auth-middleware.md)了解 `request.ctx.user` 的设置方式。
