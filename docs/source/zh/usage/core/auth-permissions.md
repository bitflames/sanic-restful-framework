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

请求进入 ViewSet 前，`BaseViewSet.check_permissions()` 会依次实例化
`permission_classes`，并调用 `has_permission(request)`。失败时抛出 403。
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
            result = permission_class().has_permission(request)
            if asyncio.iscoroutine(result):
                result = await result
            if not result:
                raise Forbidden(message="Forbidden")
```

## 对象级权限

当前 `BaseViewSet.check_object_permissions()` 是空钩子，不会自动调用权限类的
`has_object_permission()`。需要对象级检查时，必须在 ViewSet 中接线：

```python
import asyncio

from sanic.exceptions import Forbidden
from srf.permission.permission import BasePermission, IsAuthenticated


class IsOwner(BasePermission):
    # 框架调用视图级权限时只传 request，因此 view 必须可选。
    def has_permission(self, request, view=None):
        return True

    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.ctx.user.id


class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)

    async def check_object_permissions(self, request, obj):
        for permission_class in self.permission_classes:
            checker = getattr(
                permission_class(), "has_object_permission", None
            )
            if checker is None:
                continue
            result = checker(request, self, obj)
            if asyncio.iscoroutine(result):
                result = await result
            if not result:
                raise Forbidden(message="Forbidden")
```

`get_object()` 会调用这个钩子，因此 `retrieve`、`update`、`destroy` 以及显式
调用 `get_object()` 的自定义 action 都会执行检查。列表接口仍需通过过滤
`queryset` 限制可见数据。

## 自定义 action

自定义 action 同样会先执行 ViewSet 的全局 `check_permissions()`，不能通过
“手动实现 action”跳过权限。若某个 action 需要额外权限，可在 action 内
再次调用权限类：

```python
from sanic.exceptions import Forbidden
from srf.permission.permission import IsRoleAdminUser
from srf.views.decorators import action


@action(methods=["post"], detail=True)
async def publish(self, request, pk):
    if not IsRoleAdminUser().has_permission(request):
        raise Forbidden(message="需要管理员权限")
    product = await self.get_object(request, pk)
    # ...
```

## 注意事项

- `NON_AUTH_ENDPOINTS` 只按 URL 最后一段匹配，详见
  [认证中间件](../advanced/middleware/auth-middleware.md)。
- 自定义 `has_permission` 应使用签名
  `has_permission(self, request, view=None)`。
- 对象级权限必须显式接线；不要只把对象权限类放进
  `permission_classes` 就认为它已生效。
- 对公开接口，认证豁免与 ViewSet 权限都需要正确配置。
