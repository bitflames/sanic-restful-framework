# Permissions

The permission classes in SRF are used to control access to ViewSets.
View-level checks run in `check_permissions()` before the handler; 
object-level checks run in `check_object_permissions()` from `get_object()` (retrieve / update / destroy and custom actions that call `get_object()`).

## Built-in Permission Classes

```python
from srf.permission.permission import (
    AllowAny,
    BasePermission,
    IsAuthenticated,
    IsRoleAdminUser,
    IsSafeMethodOnly,
)
```

- `AllowAny`: Always allow (default in `settings.DEFAULT_PERMISSION_CLASSES`).
- `IsAuthenticated`: `request.ctx.user` exists and the user's `is_active` is true.
- `IsRoleAdminUser`: The name of the role associated with the current user is equal to `"admin"`.
- `IsSafeMethodOnly`: Only allows GET, HEAD, OPTIONS.

Declare permission classes on a ViewSet:

```python
from srf.permission.permission import IsAuthenticated
from srf.views import BaseViewSet


class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
```

`BaseViewSet.check_permissions()` calls `has_permission(request, view)` on each class **without instantiating**; both synchronous and asynchronous return values are supported. If any result is false, it throws 403 Forbidden. When the authentication middleware rejects a request due to missing or invalid Token, it returns 401.

Permission methods are `@staticmethod`s. Inheriting `BasePermission` is recommended but not required; any class with the same static methods works (duck typing).

## Custom View-Level Permissions

```python
from srf.permission.permission import BasePermission


class IsEditor(BasePermission):
    @staticmethod
    def has_permission(request, view=None):
        user = getattr(request.ctx, "user", None)
        role = getattr(user, "role", None)
        return role is not None and role.name == "editor"
```

`view` is optional; `BaseViewSet` passes the current view instance.

Asynchronous checks are also available:

```python
class HasActiveSubscription(BasePermission):
    @staticmethod
    async def has_permission(request, view=None):
        user = getattr(request.ctx, "user", None)
        return user is not None and await Subscription.filter(
            user_id=user.id, active=True
        ).exists()
```

## Setting Permissions by Request Method

The current framework does not have `self.action`, `get_permissions()`, or action-level permission parameters. When different operations need to be distinguished, you can override `check_permissions()`:

```python
import asyncio

from sanic.exceptions import Forbidden
from srf.permission.permission import IsAuthenticated, IsRoleAdminUser
from srf.views import BaseViewSet


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

## Object-Level Permissions

`BasePermission.has_object_permission(request, view, obj)` defines the object-level interface.
`get_object()` calls `check_object_permissions()`, which invokes
`has_object_permission(request, view, obj)` on each class (no instantiation).

Object-level checks are not applied per item to list results. For list interfaces, limit data in `queryset`.

### Basic Usage

```python
class IsOwner(BasePermission):
    """Object-level permission: Check if it is the owner"""

    @staticmethod
    def has_object_permission(request, view=None, obj=None):
        # Users can only view, modify, or delete their own objects
        return obj.owner_id == request.ctx.user.id


class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)
```

Limit list visibility via `queryset`:

```python
class OrderViewSet(BaseViewSet):
    @property
    def queryset(self):
        user = self.get_current_user(self.request)
        role = getattr(user, "role", None)
        if role is not None and role.name == "admin":
            return Order.all()
        return Order.filter(user_id=user.id)
```

`self.request` is set by `BaseViewSet.as_view()` before handling the request.

## Permissions for Custom Actions

All actions registered by `SanicRouter` will first execute the ViewSet's `check_permissions()`. If additional restrictions are needed, perform additional checks within the action:

```python
from sanic.exceptions import Forbidden
from srf.permission.permission import IsRoleAdminUser
from srf.views.decorators import action


@action(methods=["post"], detail=True, url_path="approve")
async def approve(self, request, pk):
    if not IsRoleAdminUser.has_permission(request, self):
        raise Forbidden(message="Administrator privileges required")
    product = await self.get_object(request, pk)
    product.is_approved = True
    await product.save()
    return json({"message": "Approved"})
```

## Best Practices

1. **Principle of Least Privilege**: Default to denying access and grant only necessary permissions explicitly.
2. **Separation of Concerns**: Isolate permission logic into permission classes.
3. **Combining Permissions**: Use multiple simple permission classes to achieve complex permissions.
4. **Object-Level Permissions**: Use object-level permission checks for sensitive resources.
5. **Asynchronous Support**: Use asynchronous methods when database queries are needed.
6. **Clear Error Messages**: Provide friendly permission error messages.
7. **Test Permissions**: Write unit tests for permission classes.

## Next Steps

- Read [Authentication](authentication.md) to learn about JWT authentication.
- Read [Authentication and Permissions Integration](auth-permissions.md) to see combination examples.
- View [Authentication Middleware](../advanced/middleware/auth-middleware.md) to understand public endpoint rules.