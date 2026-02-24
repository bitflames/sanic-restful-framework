"""Unit tests for srf.views.base (ViewSet mixins and BaseViewSet)."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from srf.views.base import (
    BaseViewSet,
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from srf.views.http_status import HTTPStatus


class MinimalViewSet(BaseViewSet):
    """Concrete ViewSet for testing; queryset is required."""

    @property
    def queryset(self):
        return MagicMock()


class TestCreateModelMixin:
    """Tests for CreateModelMixin."""

    @pytest.mark.asyncio
    async def test_create_rejects_none_json(self):
        mixin = CreateModelMixin()
        mixin._get_schema = MagicMock()
        mixin.check_permissions = AsyncMock()
        request = MagicMock()
        request.json = None
        from sanic.response import HTTPResponse
        response = await mixin.create(request)
        assert isinstance(response, HTTPResponse)
        assert response.status == HTTPStatus.HTTP_400_BAD_REQUEST


class TestRetrieveModelMixin:
    """Tests for RetrieveModelMixin."""

    @pytest.mark.asyncio
    async def test_retrieve_returns_json(self):
        mixin = RetrieveModelMixin()
        mixin.check_permissions = AsyncMock()
        mixin.get_object = AsyncMock(return_value=MagicMock(id=1, name="x"))
        mixin._get_schema = MagicMock()
        schema_class = MagicMock()
        schema_instance = MagicMock()
        schema_instance.model_dump.return_value = {"id": 1, "name": "x"}
        schema_class.model_validate.return_value = schema_instance
        mixin._get_schema.return_value = schema_class
        request = MagicMock()
        response = await mixin.retrieve(request, pk=1)
        assert response.body is not None
        assert response.status == 200


class TestUpdateModelMixin:
    """Tests for UpdateModelMixin."""

    @pytest.mark.asyncio
    async def test_update_rejects_none_json(self):
        mixin = UpdateModelMixin()
        mixin.check_permissions = AsyncMock()
        request = MagicMock()
        request.json = None
        from sanic.response import HTTPResponse
        response = await mixin.update(request, pk=1)
        assert isinstance(response, HTTPResponse)
        assert response.status == HTTPStatus.HTTP_400_BAD_REQUEST


class TestDestroyModelMixin:
    """Tests for DestroyModelMixin."""

    @pytest.mark.asyncio
    async def test_destroy_returns_204(self):
        mixin = DestroyModelMixin()
        mixin.check_permissions = AsyncMock()
        orm_model = MagicMock()
        orm_model.delete = AsyncMock()
        mixin.get_object = AsyncMock(return_value=orm_model)
        request = MagicMock()
        response = await mixin.destroy(request, pk=1)
        assert response.status == HTTPStatus.HTTP_204_NO_CONTENT


class TestBaseViewSet:
    """Tests for BaseViewSet."""

    def test_get_current_user_from_ctx(self):
        view = MinimalViewSet()
        request = MagicMock()
        request.ctx.user = "user_from_ctx"
        if hasattr(request, "auth"):
            del request.auth
        assert view.get_current_user(request) == "user_from_ctx"

    def test_get_current_user_from_auth(self):
        view = MinimalViewSet()
        request = MagicMock()
        request.ctx = type("Ctx", (), {})()  # no .user
        request.auth = "user_from_auth"
        assert view.get_current_user(request) == "user_from_auth"

    def test_get_current_user_none(self):
        view = MinimalViewSet()
        request = MagicMock()
        request.ctx = type("Ctx", (), {})()
        del request.auth
        assert view.get_current_user(request) is None

    @pytest.mark.asyncio
    async def test_check_permissions_raises_when_permission_denied(self):
        view = MinimalViewSet()
        view.permission_classes = [MagicMock()]
        perm = view.permission_classes[0].return_value
        perm.has_permission = MagicMock(return_value=False)
        request = MagicMock()
        from sanic.exceptions import Forbidden
        with pytest.raises(Forbidden):
            await view.check_permissions(request)

    @pytest.mark.asyncio
    async def test_check_permissions_async_permission(self):
        view = MinimalViewSet()
        view.permission_classes = [MagicMock()]
        perm = view.permission_classes[0].return_value
        perm.has_permission = AsyncMock(return_value=True)
        request = MagicMock()
        await view.check_permissions(request)

    @pytest.mark.asyncio
    async def test_as_view_method_not_allowed(self):
        view_fn = MinimalViewSet.as_view()
        request = MagicMock()
        request.method = "OPTIONS"
        response = await view_fn(request)
        assert response.status == HTTPStatus.HTTP_405_METHOD_NOT_ALLOWED
