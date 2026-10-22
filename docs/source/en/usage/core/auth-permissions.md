# Authentication and Permissions Together

Authentication is responsible for writing the current user into `request.ctx.user`, while permissions decide whether that user may access
the ViewSet. See [Permissions](permissions.md) for complete documentation of permission classes and how object-level permissions are wired;
this article only explains how the two combine, to avoid duplicating the permission reference.

## Basic configuration

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

Before a request enters the ViewSet, `BaseViewSet.check_permissions()` calls
`has_permission(request, view)` on the class (without instantiating it). It raises Forbidden on failure.
When there is no authentication information, the middleware sets `request.ctx.user` to `None`; for example,
`IsAuthenticated` rejects that user (403). The authentication middleware returns 401 only when the request header format is invalid, JWT is not configured,
or the user does not exist; a missing token or a failed signature/expiry check is treated as an anonymous request.

## Setting permissions by HTTP method

To differentiate permissions by operation, simply override `check_permissions()`; see
[Permissions: Setting permissions by request method](permissions.md) for the full approach (the permission reference page has a complete example).

## Object-level permissions

`BaseViewSet.check_object_permissions()` calls
`has_object_permission(request, view, obj)` on the class. `get_object()` triggers this check,
so `retrieve` / `update` / `destroy` as well as custom actions that explicitly call `get_object()` all run it. Use `@staticmethod` for custom object permissions:

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

The list endpoint still needs to limit visible data by filtering the `queryset`.

## Custom actions

All actions first run the ViewSet's global `check_permissions()`; when additional checks are needed inside an action,
follow the "Permissions for custom actions" section in [Permissions](permissions.md).

## Notes

- Custom permissions should use `@staticmethod`, with the signatures `has_permission(request, view=None)` / `has_object_permission(request, view=None, obj=None)`.
- Object visibility for list endpoints still needs to be scoped via `get_queryset()` (or `queryset`).
