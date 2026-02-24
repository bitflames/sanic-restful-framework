"""Unit tests for srf.permission.permission."""
import pytest
from unittest.mock import MagicMock

from srf.permission.permission import (
    BasePermission,
    IsAuthenticated,
    IsRoleAdminUser,
    IsSafeMethodOnly,
)


class TestBasePermission:
    def test_has_permission_default_true(self):
        p = BasePermission()
        assert p.has_permission(MagicMock(), None) is True

    def test_has_object_permission_default_true(self):
        p = BasePermission()
        assert p.has_object_permission(MagicMock(), None, MagicMock()) is True


class TestIsAuthenticated:
    def test_no_user_denied(self):
        request = MagicMock()
        request.ctx = MagicMock()
        request.ctx.user = None
        assert IsAuthenticated().has_permission(request, None) is False

    def test_with_user_allowed(self):
        request = MagicMock()
        request.ctx = MagicMock()
        request.ctx.user = MagicMock()
        request.ctx.user.is_active = True
        assert IsAuthenticated().has_permission(request, None) is True

    def test_user_inactive_denied(self):
        request = MagicMock()
        request.ctx = MagicMock()
        request.ctx.user = MagicMock()
        request.ctx.user.is_active = False
        assert IsAuthenticated().has_permission(request, None) is False


class TestIsRoleAdminUser:
    def test_no_user_denied(self):
        request = MagicMock()
        request.ctx = MagicMock()
        request.ctx.user = None
        assert IsRoleAdminUser().has_permission(request, None) is False

    def test_no_role_denied(self):
        request = MagicMock()
        request.ctx = MagicMock()
        request.ctx.user = MagicMock()
        request.ctx.user.role = None
        assert IsRoleAdminUser().has_permission(request, None) is False

    def test_role_not_admin_denied(self):
        request = MagicMock()
        request.ctx = MagicMock()
        request.ctx.user = MagicMock()
        request.ctx.user.role = MagicMock()
        request.ctx.user.role.name = "user"
        assert IsRoleAdminUser().has_permission(request, None) is False

    def test_role_admin_allowed(self):
        request = MagicMock()
        request.ctx = MagicMock()
        request.ctx.user = MagicMock()
        request.ctx.user.role = MagicMock()
        request.ctx.user.role.name = "admin"
        assert IsRoleAdminUser().has_permission(request, None) is True


class TestIsSafeMethodOnly:
    def test_get_allowed(self):
        request = MagicMock()
        request.method = "GET"
        assert IsSafeMethodOnly().has_permission(request, None) is True

    def test_options_allowed(self):
        request = MagicMock()
        request.method = "OPTIONS"
        assert IsSafeMethodOnly().has_permission(request, None) is True

    def test_post_denied(self):
        request = MagicMock()
        request.method = "POST"
        assert IsSafeMethodOnly().has_permission(request, None) is False

    def test_put_denied(self):
        request = MagicMock()
        request.method = "PUT"
        assert IsSafeMethodOnly().has_permission(request, None) is False

    def test_delete_denied(self):
        request = MagicMock()
        request.method = "DELETE"
        assert IsSafeMethodOnly().has_permission(request, None) is False
