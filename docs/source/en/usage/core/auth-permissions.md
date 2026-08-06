# Integration of Authentication and Permissions

Authentication writes the current user into `request.ctx.user`, while permissions determine whether the user can access the ViewSet. For a complete explanation of permission classes and object-level permission wiring, see [Permissions](permissions.md); this article only explains how they are combined to avoid repetition with the permission reference.

## Basic Configuration

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

Before the request reaches the ViewSet, `BaseViewSet.check_permissions()` will instantiate `permission_classes` in sequence and call `has_permission(request)`. If it fails, it raises a 403 error. If the authentication middleware detects a missing or invalid Bearer Token first, it returns a 401.

## Setting Permissions by HTTP Method

The current framework does not have `self.action` or `get_permissions()`. When you need to distinguish operations, you should override `check_permissions()`:

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

## Object-Level Permissions

Currently, `BaseViewSet.check_object_permissions()` is an empty hook and does not automatically call the permission class's `has_object_permission()`. When object-level checks are needed, they must be wired in the ViewSet:

```python
import asyncio

from sanic.exceptions import Forbidden
from srf.permission.permission import BasePermission, IsAuthenticated


class IsOwner(BasePermission):
    # The framework only passes request when calling view-level permissions, so view must be optional.
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

This hook is called by `get_object()`, so `retrieve`, `update`, `destroy`, and custom actions that explicitly call `get_object()` will perform the check. The list interface still needs to filter the `queryset` to limit visible data.

## Custom Actions

Custom actions will also first execute the ViewSet's global `check_permissions()`, and cannot skip the permissions by "manually implementing the action". If a certain action requires additional permissions, you can call the permission class again within the action:

```python
from sanic.exceptions import Forbidden
from srf.permission.permission import IsRoleAdminUser
from srf.views.decorators import action


@action(methods=["post"], detail=True)
async def publish(self, request, pk):
    if not IsRoleAdminUser().has_permission(request):
        raise Forbidden(message="Requires admin privileges")
    product = await self.get_object(request, pk)
    # ...
```

## Notes

- `NON_AUTH_ENDPOINTS` matches only the last part of the URL; see [Authentication Middleware](../advanced/middleware/auth-middleware.md) for details.
- Custom `has_permission` should use the signature `has_permission(self, request, view=None)`.
- Object-level permissions must be explicitly wired; do not assume they take effect just by placing object permission classes in `permission_classes`.
- For public interfaces, both authentication exemptions and ViewSet permissions need to be correctly configured.