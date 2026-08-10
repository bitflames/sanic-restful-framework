"""Unit tests for srf.views.base (ViewSet mixins and BaseViewSet)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from srf.views import GenericAPIView
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

    @pytest.mark.asyncio
    async def test_create_calls_perform_create_with_schema(self):
        mixin = CreateModelMixin()
        sch_model = MagicMock(model_dump=MagicMock(return_value={"name": "x"}))
        schema_in = MagicMock()
        schema_in.model_validate.return_value = sch_model
        schema_out = MagicMock()
        schema_out.model_validate.return_value = MagicMock(model_dump=MagicMock(return_value={"id": 1, "name": "x"}))
        mixin._get_schema = MagicMock(side_effect=lambda req, is_safe=False: schema_out if is_safe else schema_in)
        orm = MagicMock()
        mixin.perform_create = AsyncMock(return_value=orm)
        request = MagicMock()
        request.json = {"name": "x"}
        response = await mixin.create(request)
        mixin.perform_create.assert_awaited_once_with(sch_model)
        assert response.status == HTTPStatus.HTTP_201_CREATED


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
        orm_model.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_destroy_calls_perform_destroy(self):
        mixin = DestroyModelMixin()
        orm_model = MagicMock()
        mixin.get_object = AsyncMock(return_value=orm_model)
        mixin.perform_destroy = AsyncMock()
        request = MagicMock()
        response = await mixin.destroy(request, pk=1)
        mixin.perform_destroy.assert_awaited_once_with(orm_model)
        assert response.status == HTTPStatus.HTTP_204_NO_CONTENT


class TestGenericAPIView:
    def test_exported_from_views(self):
        assert issubclass(GenericAPIView, object)

    def test_filter_class_class_attr_override(self):
        class CustomFilter:
            pass

        class View(GenericAPIView):
            filter_class = [CustomFilter]

            @property
            def queryset(self):
                return MagicMock()

        view = View()
        assert view.filter_class == [CustomFilter]

    def test_permission_classes_defaults_from_settings(self):
        from srf.config import settings

        view = MinimalViewSet()
        assert view.permission_classes == settings.DEFAULT_PERMISSION_CLASSES

    def test_permission_classes_class_attr_override(self):
        from srf.permission.permission import IsAuthenticated

        class View(GenericAPIView):
            permission_classes = (IsAuthenticated,)

            @property
            def queryset(self):
                return MagicMock()

        view = View()
        assert view.permission_classes == (IsAuthenticated,)


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
        perm_cls = MagicMock()
        perm_cls.has_permission = MagicMock(return_value=False)
        view.permission_classes = [perm_cls]
        request = MagicMock()
        from sanic.exceptions import Forbidden

        with pytest.raises(Forbidden):
            await view.check_permissions(request)

    @pytest.mark.asyncio
    async def test_check_permissions_async_permission(self):
        view = MinimalViewSet()
        perm_cls = MagicMock()
        perm_cls.has_permission = AsyncMock(return_value=True)
        view.permission_classes = [perm_cls]
        request = MagicMock()
        await view.check_permissions(request)

    @pytest.mark.asyncio
    async def test_check_object_permissions_raises_when_denied(self):
        view = MinimalViewSet()
        perm_cls = MagicMock()
        perm_cls.has_object_permission = MagicMock(return_value=False)
        view.permission_classes = [perm_cls]
        request = MagicMock()
        from sanic.exceptions import Forbidden

        with pytest.raises(Forbidden):
            await view.check_object_permissions(request, MagicMock())

    @pytest.mark.asyncio
    async def test_check_object_permissions_async(self):
        view = MinimalViewSet()
        perm_cls = MagicMock()
        perm_cls.has_object_permission = AsyncMock(return_value=True)
        view.permission_classes = [perm_cls]
        request = MagicMock()
        await view.check_object_permissions(request, MagicMock())

    def test_get_queryset_returns_queryset_attribute(self):
        qs = object()

        class View(GenericAPIView):
            queryset = qs

        assert View().get_queryset() is qs

    def test_get_queryset_asserts_when_missing(self):
        class View(GenericAPIView):
            pass

        with pytest.raises(AssertionError, match="queryset"):
            View().get_queryset()

    @pytest.mark.asyncio
    async def test_get_object_uses_get_queryset(self):
        view = MinimalViewSet()
        instance = MagicMock()
        qs = MagicMock()
        qs.get_or_none = AsyncMock(return_value=instance)
        view.get_queryset = MagicMock(return_value=qs)
        view.check_object_permissions = AsyncMock()
        request = MagicMock()

        result = await view.get_object(request, 1)

        view.get_queryset.assert_called_once_with()
        qs.get_or_none.assert_awaited_once_with(id=1)
        view.check_object_permissions.assert_awaited_once_with(request, instance)
        assert result is instance

    @pytest.mark.asyncio
    async def test_get_object_raises_not_found(self):
        view = MinimalViewSet()
        qs = MagicMock()
        qs.get_or_none = AsyncMock(return_value=None)
        view.get_queryset = MagicMock(return_value=qs)
        request = MagicMock()
        from sanic.exceptions import NotFound

        with pytest.raises(NotFound):
            await view.get_object(request, 99)

    @pytest.mark.asyncio
    async def test_as_view_method_not_allowed(self):
        view_fn = MinimalViewSet.as_view()
        request = MagicMock()
        request.method = "OPTIONS"
        response = await view_fn(request)
        assert response.status == HTTPStatus.HTTP_405_METHOD_NOT_ALLOWED
