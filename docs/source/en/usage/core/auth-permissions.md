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

Before the request reaches the ViewSet, `BaseViewSet.check_permissions()` calls `has_permission(request, view)` on each class **without instantiating**. If it fails, it raises a Forbidden error. 
If the authentication middleware detects a missing or invalid Bearer Token first, it returns a 401.

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
            result = permission_class.has_permission(request, self)
            if asyncio.iscoroutine(result):
                result = await result
            if not result:
                raise Forbidden(message="Forbidden")
```

## Object-Level Permissions

`BaseViewSet.check_object_permissions()` calls `has_object_permission(request, view, obj)` on each class. `get_object()` triggers this check, so `retrieve` / `update` / `destroy` and custom actions that call `get_object()` are covered. Use `@staticmethod` for custom object permissions:

```python
from srf.permission.permission import BasePermission, IsAuthenticated


class IsOwner(BasePermission):
    @staticmethod
    def has_object_permission(request, view=None, obj=None):
        return obj.user_id == request.ctx.user.id


class OrderViewSet(BaseViewSet):
    permission_classes = (IsAuthenticated, IsOwner)
```

List endpoints still need to filter `queryset` to limit visible data.

## Custom Actions

Custom actions will also first execute the ViewSet's global `check_permissions()`, and cannot skip the permissions by "manually implementing the action". If a certain action requires additional permissions, you can call the permission class again within the action:

```python
from sanic.exceptions import Forbidden
from srf.permission.permission import IsRoleAdminUser
from srf.views.decorators import action


@action(detail=True, methods=["post"], url_path="publish")
async def publish(self, request, pk):
    if not IsRoleAdminUser.has_permission(request, self):
        raise Forbidden(message="Requires admin privileges")
    product = await self.get_object(request, pk)
    # ...
```

## Notes

- `NON_AUTH_ENDPOINTS` matches only the last part of the URL; see [Authentication Middleware](../advanced/middleware/auth-middleware.md) for details.
- Custom permissions should use `@staticmethod` with signatures  `has_permission(request, view=None)` /  `has_object_permission(request, view=None, obj=None)`.
- List visibility must still be enforced by scoping `get_queryset()` (or `queryset`).
- For public interfaces, both authentication exemptions and ViewSet permissions need to be correctly configured.
