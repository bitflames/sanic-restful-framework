from sanic.constants import SAFE_HTTP_METHODS


class BasePermission(metaclass=type):
    """
    A base class from which all permission classes should inherit.
    """

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return True

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return True


class IsRoleAdminUser(BasePermission):
    def has_permission(self, request, view=None):
        user = getattr(request.ctx, "user", None)
        if user is None:
            return False
        role = getattr(user, "role", None)
        return role is not None and getattr(role, "name", None) == "admin"


class IsAuthenticated(BasePermission):
    def has_permission(self, request, view=None):
        user = getattr(request.ctx, "user", None)
        return user is not None and getattr(user, "is_active", True)


class IsSafeMethodOnly(BasePermission):
    """
    Allow only safe HTTP methods (GET, HEAD, OPTIONS). Reject unsafe methods (POST, PUT, PATCH, DELETE, etc.).
    Use for read-only endpoints: anyone can read, all write operations are denied.
    """

    def has_permission(self, request, view=None):
        return request.method.upper() in SAFE_HTTP_METHODS
