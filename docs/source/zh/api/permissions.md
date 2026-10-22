# API 参考：Permissions

权限类在每次请求进入视图方法之前执行。使用说明见 [权限](../usage/core/permissions.md) 与 [接口权限](../usage/core/auth-permissions.md)。

```python
from srf.permission import IsAuthenticated, SuperuserOnly
```

## 权限契约

权限类的方法以**静态方法**形式定义，框架直接通过类调用，不会实例化：

```python
from sanic import Request


class IsOwner:
    @staticmethod
    def has_permission(request: Request, view=None) -> bool:
        return getattr(request.ctx, "user", None) is not None

    @staticmethod
    def has_object_permission(request: Request, view=None, obj=None) -> bool:
        user = getattr(request.ctx, "user", None)
        return user is not None and obj.user_id == user.id
```

- 同步与异步（`async def`）方法都支持，框架会自动 `await` 协程结果。
- 方法返回假值时抛出 `403 Forbidden`。
- 因为是按类调用，不能在权限类里依赖 `__init__` 保存的实例状态；需要跨方法共享的数据请放在类属性或 `request.ctx` 上。

!!! warning "对象级权限的触发时机"
    `has_object_permission()` 只在 `get_object()` 中被调用，因此只对 `retrieve` / `update` / `destroy` 生效。`list` 不会逐条检查对象权限，需要在 `get_queryset()` 中按用户过滤；`create` 也不做对象级检查。


## 在 ViewSet 中使用

```python
from your_py import IsOwner
from srf.views import BaseViewSet


class ProfileViewSet(BaseViewSet):
    queryset = User.all()
    schema = UserSchema
    permission_classes = (IsOwner,)
```

## 内置权限类

| 类 | `has_permission` 行为 |
| --- | --- |
| `AllowAny` | 始终允许（默认权限） |
| `IsAuthenticated` | `request.ctx.user` 存在且 `is_active` 为真 |
| `SafeMethodOnly` | 只允许安全方法：`GET` / `HEAD` / `OPTIONS` |
| `SuperuserOnly` | `request.ctx.user` 存在且 `is_superuser` 为真 |

未声明 `permission_classes` 时使用 `settings.DEFAULT_PERMISSION_CLASSES`，默认值为 `(AllowAny,)`。

::: srf.permission.permission.BasePermission
    options:
      heading_level: 4
      members:
        - has_permission
        - has_object_permission
      show_source: false
      inherited_members: false

::: srf.permission.permission.AllowAny
    options:
      heading_level: 4
      members:
        - has_permission
        - has_object_permission
      show_source: false
      inherited_members: false

::: srf.permission.permission.IsAuthenticated
    options:
      heading_level: 4
      members:
        - has_permission
      show_source: false
      inherited_members: false

::: srf.permission.permission.SafeMethodOnly
    options:
      heading_level: 4
      members:
        - has_permission
      show_source: false
      inherited_members: false

::: srf.permission.permission.SuperuserOnly
    options:
      heading_level: 4
      members:
        - has_permission
      show_source: false
      inherited_members: false


`permission_classes` 可以是任意可迭代对象；每个元素都需要提供 `has_permission(request, view)`，需要对象级权限时再提供 `has_object_permission(request, view, obj)`。
