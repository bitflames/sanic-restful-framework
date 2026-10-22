# API Reference: Permissions

Permission classes run before each request enters a view method. See [Permissions](../usage/core/permissions.md) and [API Permissions](../usage/core/auth-permissions.md) for usage.

```python
from srf.permission import IsAuthenticated, SuperuserOnly
```

## Permission contract

Permission class methods are defined as **static methods**; the framework calls them directly on the class and does not instantiate it:

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

- Both synchronous and asynchronous (`async def`) methods are supported; the framework automatically awaits coroutine results.
- A falsy return value raises `403 Forbidden`.
- Because methods are called on the class, permission classes cannot rely on instance state stored in `__init__`; data that must be shared across methods should be placed on class attributes or `request.ctx`.

!!! warning "When object-level permissions are checked"
    `has_object_permission()` is only called inside `get_object()`, so it only applies to `retrieve` / `update` / `destroy`. `list` does not check object permissions per item; filter by user in `get_queryset()` instead. `create` also performs no object-level checks.


## Using in a ViewSet

```python
from your_py import IsOwner
from srf.views import BaseViewSet


class ProfileViewSet(BaseViewSet):
    queryset = User.all()
    schema = UserSchema
    permission_classes = (IsOwner,)
```

## Built-in permission classes

| Class | `has_permission` behavior |
| --- | --- |
| `AllowAny` | Always allow (default permission) |
| `IsAuthenticated` | `request.ctx.user` exists and `is_active` is true |
| `SafeMethodOnly` | Only safe methods are allowed: `GET` / `HEAD` / `OPTIONS` |
| `SuperuserOnly` | `request.ctx.user` exists and `is_superuser` is true |

When `permission_classes` is not declared, `settings.DEFAULT_PERMISSION_CLASSES` is used, which defaults to `(AllowAny,)`.

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


`permission_classes` can be any iterable; each element must provide `has_permission(request, view)`, and optionally `has_object_permission(request, view, obj)` when object-level permissions are needed.
