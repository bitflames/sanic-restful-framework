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
没有认证信息时，中间件将 `request.ctx.user` 设为 `None`；例如
`IsAuthenticated` 会拒绝该用户（403）。认证中间件只在请求头格式错误、JWT 未配置
或用户不存在时返回 401；Token 缺失或签名/有效期校验失败会按匿名请求处理。

## 按 HTTP 方法设置权限

按操作区分权限时，重写 `check_permissions()` 即可；完整写法见
[权限：按请求方法设置权限](permissions.md)（权限参考页中有完整示例）。

## 对象级权限

`BaseViewSet.check_object_permissions()` 会在类上调用
`has_object_permission(request, view, obj)`。`get_object()` 会触发该检查，
因此 `retrieve` / `update` / `destroy` 以及显式调用 `get_object()` 的自定义
action 都会执行。自定义对象权限时使用 `@staticmethod`：

```python
from models import Order
from srf.permission.permission import BasePermission, IsAuthenticated
from srf.views import BaseViewSet


class IsOwner(BasePermission):
    @staticmethod
    def has_object_permission(request, view=None, obj=None):
        return obj.user_id == request.ctx.user.id


class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)
```

列表接口仍需通过过滤 `queryset` 限制可见数据。

## 自定义 action

所有 action 都会先执行 ViewSet 的全局 `check_permissions()`；需要在 action 内
追加检查时，按[权限](permissions.md)中“自定义 action 的权限”一节处理即可。

## 注意事项

- 自定义权限应使用 `@staticmethod`，签名为 `has_permission(request, view=None)` / `has_object_permission(request, view=None, obj=None)`。
- 列表接口的对象可见性仍需通过 `get_queryset()`（或 `queryset`）限定范围。
