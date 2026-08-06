# Permissions

The permission classes in SRF are used to control access to ViewSets. The current version automatically executes view-level permissions; object-level permissions provide an extension interface, but require the application to implement it.

## Built-in Permission Classes

```python
from srf.permission.permission import (
    BasePermission,
    IsAuthenticated,
    IsRoleAdminUser,
    IsSafeMethodOnly,
)
```

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

`BaseViewSet.check_permissions()` will instantiate each class in order and call `has_permission(request)`; both synchronous and asynchronous return values are supported. If any result is false, it throws 403 Forbidden. When the authentication middleware rejects a request due to missing or invalid Token, it returns 401.

## Custom View-Level Permissions

```python
from srf.permission.permission import BasePermission


class IsEditor(BasePermission):
    def has_permission(self, request, view=None):
        user = getattr(request.ctx, "user", None)
        role = getattr(user, "role", None)
        return role is not None and role.name == "editor"
```

The `view` is an optional parameter. Although the base class signature of `BasePermission` includes `view`, the current `BaseViewSet` only passes `request`.

Asynchronous checks are also available:

```python
class HasActiveSubscription(BasePermission):
    async def has_permission(self, request, view=None):
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


class ProductViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated,)
    
    def get_permissions(self):
        """Return different permission classes based on the operation"""
        if self.action in ['update', 'destroy']:
            # Update and delete require admin privileges
            return [IsAuthenticated(), IsRoleAdminUser()]
        elif self.action == 'create':
            # Create only requires login
            return [IsAuthenticated()]
        else:
            # List and detail do not require permissions
            return []
```

## Object-Level Permissions

`BasePermission.has_object_permission(request, view, obj)` defines the object-level interface. Adding it to `permission_classes` **will not** automatically protect objects.

### Basic Usage

```python
class IsOwner(BasePermission):
    """Object-level permission: Check if it is the owner"""

    def has_object_permission(self, request, view, obj):
        # Users can only view, modify, or delete their own objects
        return obj.owner_id == request.ctx.user.id

class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwnerOrAdmin)

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

The built-in `get_object()` calls this hook after obtaining the object. Therefore, standard detail, update, delete operations and custom actions that call `get_object()` are protected.

Object-level checks are not applied per item to list results. For list interfaces, limit data in `queryset`:

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
    if not IsRoleAdminUser().has_permission(request):
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