# Permissions

SRF permission classes control access to ViewSets. View-level checks run before the handler through `check_permissions()`;
object-level checks run when `get_object()` calls `check_object_permissions()` (covering retrieve / update / destroy, as well as custom actions that call `get_object()`).

## Built-in permission classes

```python
from srf.permission.permission import (
    AllowAny,
    BasePermission,
    IsAuthenticated,
    SuperuserOnly,
    SafeMethodOnly,
)
```

- `AllowAny`: Always allow (the default value of `settings.DEFAULT_PERMISSION_CLASSES`).
- `IsAuthenticated`: `request.ctx.user` exists and the user's `is_active` is true.
- `SuperuserOnly`: `request.ctx.user.is_superuser` is true.
- `SafeMethodOnly`: Only GET, HEAD, and OPTIONS are allowed.

Declare permission classes on a ViewSet:

```python
from srf.permission.permission import IsAuthenticated
from srf.views import BaseViewSet


class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
```

`BaseViewSet.check_permissions()` calls
`has_permission(request, view)` **on the class** in order; both synchronous and asynchronous return values are supported. If any result is falsy, it raises
403 Forbidden. When there is no authentication information, the authentication middleware sets `request.ctx.user` to `None`, and the
permission class decides whether to allow the request; when the request header format is invalid, JWT is not configured, or the user does not exist, the authentication middleware returns
401, while a missing token or a failed signature/expiry check is treated as an anonymous request.

Permission methods are `@staticmethod`s: inheriting from `BasePermission` is recommended but not required; providing a static method with the same name is enough (duck typing).

## Custom view-level permissions

```python
from srf.permission.permission import BasePermission


class IsEditor(BasePermission):
    @staticmethod
    def has_permission(request, view=None):
        user = getattr(request.ctx, "user", None)
        # is_editor is an application-defined field; the built-in SRF User only has is_superuser and the roles relationship.
        return user is not None and getattr(user, "is_editor", False)
```

`view` is an optional parameter; `BaseViewSet` passes the current View instance.

Asynchronous checks work as well:

```python
from models import Subscription
from srf.permission.permission import BasePermission


class HasActiveSubscription(BasePermission):
    @staticmethod
    async def has_permission(request, view=None):
        user = getattr(request.ctx, "user", None)
        return user is not None and await Subscription.filter(user_id=user.id, active=True).exists()
```

## Setting permissions by request method

To differentiate permissions by operation, select permission classes based on `self.action` in `check_permissions()`:

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

## Object-level permissions

`BasePermission.has_object_permission(request, view, obj)` defines the object-level interface.
`get_object()` calls `check_object_permissions()`, which calls
`has_object_permission(request, view, obj)` on the permission class and raises `Forbidden` when the result is falsy.

Object-level checks are not applied item by item to list results. List endpoints should limit data in the `queryset`.

### Basic usage

```python
from models import Order
from srf.permission.permission import BasePermission, IsAuthenticated
from srf.views import BaseViewSet


class IsOwner(BasePermission):
    """Object-level permission: check whether the user is the owner"""

    @staticmethod
    def has_object_permission(request, view=None, obj=None):
        # Users can only view, modify, and delete their own objects
        return obj.owner_id == request.ctx.user.id


class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)
```

Limit visible data on the list side through `queryset`:

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

`self.request` is set by `BaseViewSet.as_view()` before handling the request.

## Permissions for custom actions

All actions registered by `SanicRouter` first run the ViewSet's
`check_permissions()`. If additional restrictions are needed, perform extra checks inside the action:

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
            raise Forbidden(message="Superuser permission required")
        product = await self.get_object(pk)
        product.is_approved = True
        await product.save()
        return json({"message": "Approved"})
```

## Best practices

1. **Principle of least privilege**: deny access by default and grant only the necessary permissions
2. **Separation of concerns**: keep permission logic in dedicated permission classes
3. **Composing permissions**: combine several simple permission classes to implement complex permissions
4. **Object-level permissions**: use object-level permission checks for sensitive resources
5. **Async support**: use asynchronous methods when database queries are needed
6. **Clear error messages**: provide friendly permission error messages
7. **Test permissions**: write unit tests for permission classes

## Next steps

- Read [Authentication](authentication.md) to learn about JWT authentication.
- Read [Authentication and Permissions Together](auth-permissions.md) for combined examples.
- See [Authentication Middleware](../advanced/middleware/auth-middleware.md) to learn how `request.ctx.user` is set.
