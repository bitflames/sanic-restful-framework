# 认证与权限配合

认证负责把当前用户写入 `request.ctx.user`，权限负责决定该用户能否访问
ViewSet。权限类的完整说明和对象级权限接线方式见[权限](permissions.md)；
本文只说明两者如何组合，避免与权限参考重复。

## 基本配置

```python
from srf.middleware.authmiddleware import set_user_to_request_ctx
from srf.permission.permission import IsAuthenticated
from srf.views import BaseViewSet


@app.middleware("request")
async def auth_middleware(request):
    await set_user_to_request_ctx(request)


class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
```

请求进入 ViewSet 前，`BaseViewSet.check_permissions()` 会在类上调用
`has_permission(request, view)`（不实例化）。失败时抛出 Forbidden。
如果认证中间件先发现 Bearer Token 缺失或无效，则会返回 401。

## 按 HTTP 方法设置权限

当前框架没有 `self.action` 或 `get_permissions()`。需要按操作区分时，应重写
`check_permissions()`：

```python
import asyncio

from sanic.exceptions import Forbidden
from srf.permission.permission import IsAuthenticated, IsRoleAdminUser


class ProductViewSet(BaseViewSet):
    async def check_permissions(self, request):
        if request.method.upper() in ("GET", "HEAD", "OPTIONS"):
            return

        classes = (
            (IsAuthenticated,)
            if request.method.upper() == "POST"
            else (IsAuthenticated, IsRoleAdminUser)
        )
        for permission_class in classes:
            result = permission_class.has_permission(request, self)
            if asyncio.iscoroutine(result):
                result = await result
            if not result:
                raise Forbidden(message="Forbidden")
```

## 对象级权限

`BaseViewSet.check_object_permissions()` 会在类上调用
`has_object_permission(request, view, obj)`。`get_object()` 会触发该检查，
因此 `retrieve` / `update` / `destroy` 以及显式调用 `get_object()` 的自定义
action 都会执行。自定义对象权限时使用 `@staticmethod`：

```python
from srf.permission.permission import BasePermission, IsAuthenticated


class IsOwner(BasePermission):
    @staticmethod
    def has_object_permission(request, view=None, obj=None):
        return obj.user_id == request.ctx.user.id


class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)


列表接口仍需通过过滤 `queryset` 限制可见数据。

## 自定义 action

自定义 action 同样会先执行 ViewSet 的全局 `check_permissions()`，不能通过
“手动实现 action”跳过权限。若某个 action 需要额外权限，可在 action 内
再次调用权限类：

```python
from sanic.exceptions import Forbidden
from srf.permission.permission import IsRoleAdminUser
from srf.views.decorators import action


@action(detail=True, methods=["post"], url_path="publish")
async def publish(self, request, pk):
    if not IsRoleAdminUser.has_permission(request, self):
        raise Forbidden(message="需要管理员权限")
    product = await self.get_object(request, pk)
    # ...
```

## 注意事项

- `NON_AUTH_ENDPOINTS` 只按 URL 最后一段匹配，详见
  [认证中间件](../advanced/middleware/auth-middleware.md)。
- 自定义权限应使用 `@staticmethod`，签名为 `has_permission(request, view=None)` / `has_object_permission(request, view=None, obj=None)`。
- 列表接口的对象可见性仍需通过 `get_queryset()`（或 `queryset`）限定范围。
- 对公开接口，认证豁免与 ViewSet 权限都需要正确配置。
