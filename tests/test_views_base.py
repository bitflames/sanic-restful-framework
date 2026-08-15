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

    @pytest.mark.asyncio
    async def test_perform_update_uses_update_from_dict(self):
        mixin = UpdateModelMixin()
        sch_model = MagicMock()
        sch_model.model_dump.return_value = {"id": 99, "name": "alice"}
        orm_model = MagicMock()
        orm_model._meta.pk_attr = "id"
        orm_model.update_from_dict = MagicMock(return_value=orm_model)
        orm_model.save = AsyncMock()

        result = await mixin.perform_update(sch_model, orm_model)

        sch_model.model_dump.assert_called_once_with(exclude_unset=True, exclude_none=True)
        orm_model.update_from_dict.assert_called_once_with({"name": "alice"})
        orm_model.save.assert_awaited_once()
        assert result is orm_model

    @pytest.mark.asyncio
    async def test_perform_update_strips_custom_pk_attr(self):
        mixin = UpdateModelMixin()
        sch_model = MagicMock()
        sch_model.model_dump.return_value = {"uuid": "keep-me-out", "title": "x"}
        orm_model = MagicMock()
        orm_model._meta.pk_attr = "uuid"
        orm_model.update_from_dict = MagicMock(return_value=orm_model)
        orm_model.save = AsyncMock()

        await mixin.perform_update(sch_model, orm_model)

        orm_model.update_from_dict.assert_called_once_with({"title": "x"})

    @pytest.mark.asyncio
    async def test_partial_update_passes_partial_true_to_get_schema(self):
        mixin = UpdateModelMixin()
        schema_in = MagicMock()
        sch_model = MagicMock()
        schema_in.model_validate.return_value = sch_model
        schema_out = MagicMock()
        schema_out.model_validate.return_value = MagicMock(model_dump=MagicMock(return_value={"id": 1}))
        seen = []

        def _get_schema(request, is_safe=False, partial=False):
            seen.append({"is_safe": is_safe, "partial": partial})
            return schema_out if is_safe else schema_in

        mixin._get_schema = MagicMock(side_effect=_get_schema)
        orm = MagicMock()
        mixin.get_object = AsyncMock(return_value=orm)
        mixin.perform_update = AsyncMock(return_value=orm)
        request = MagicMock()
        request.json = {"username": "bob"}

        response = await mixin.partial_update(request, pk=1)
        assert response.status == 200
        schema_in.model_validate.assert_called_once_with(
            {"username": "bob"},
            strict=True,
            by_alias=True,
        )
        assert {"is_safe": False, "partial": True} in seen
        assert {"is_safe": True, "partial": False} in seen

    @pytest.mark.asyncio
    async def test_update_defaults_partial_false(self):
        mixin = UpdateModelMixin()
        schema_in = MagicMock()
        sch_model = MagicMock()
        schema_in.model_validate.return_value = sch_model
        schema_out = MagicMock()
        schema_out.model_validate.return_value = MagicMock(model_dump=MagicMock(return_value={"id": 1}))
        seen = {}

        def _get_schema(request, is_safe=False, partial=False):
            if not is_safe:
                seen["partial"] = partial
            return schema_out if is_safe else schema_in

        mixin._get_schema = MagicMock(side_effect=_get_schema)
        orm = MagicMock()
        mixin.get_object = AsyncMock(return_value=orm)
        mixin.perform_update = AsyncMock(return_value=orm)
        request = MagicMock()
        request.json = {"username": "bob"}

        await mixin.update(request, pk=1)
        assert seen["partial"] is False


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

    def test_pagination_class_defaults_from_settings(self):
        from srf.config import settings

        view = MinimalViewSet()
        assert view.pagination_class is settings.PAGINATION_CLASS

    def test_pagination_class_follows_bound_app(self):
        from types import SimpleNamespace

        from srf.config import settings

        class CustomPagination:
            pass

        previous = getattr(settings, "app", None)
        try:
            app = MagicMock()
            app.config = SimpleNamespace(PAGINATION_CLASS=CustomPagination)
            settings.set_app(app)
            view = MinimalViewSet()
            assert view.pagination_class is CustomPagination
        finally:
            if previous is None:
                if hasattr(settings, "app"):
                    delattr(settings, "app")
            else:
                object.__setattr__(settings, "app", previous)

    def test_pagination_class_class_attr_override(self):
        class CustomPagination:
            pass

        class View(GenericAPIView):
            pagination_class = CustomPagination

            @property
            def queryset(self):
                return MagicMock()

        view = View()
        assert view.pagination_class is CustomPagination

    def test_new_view_follows_last_bound_app(self):
        """Two apps in one process: each new ViewSet reads the currently bound app."""
        from types import SimpleNamespace

        from srf.config import settings
        from srf.permission.permission import AllowAny, IsAuthenticated

        class PaginationA:
            pass

        class PaginationB:
            pass

        previous = getattr(settings, "app", None)
        try:
            app1 = MagicMock()
            app1.config = SimpleNamespace(
                PAGINATION_CLASS=PaginationA,
                DEFAULT_PERMISSION_CLASSES=(AllowAny,),
            )
            app2 = MagicMock()
            app2.config = SimpleNamespace(
                PAGINATION_CLASS=PaginationB,
                DEFAULT_PERMISSION_CLASSES=(IsAuthenticated,),
            )

            settings.set_app(app1)
            view1 = MinimalViewSet()
            assert view1.pagination_class is PaginationA
            assert view1.permission_classes == (AllowAny,)

            settings.set_app(app2)
            view2 = MinimalViewSet()
            assert view2.pagination_class is PaginationB
            assert view2.permission_classes == (IsAuthenticated,)
            # Already-built instances keep the copy from their __init__
            assert view1.pagination_class is PaginationA
        finally:
            if previous is None:
                if hasattr(settings, "app"):
                    delattr(settings, "app")
            else:
                object.__setattr__(settings, "app", previous)


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

    @pytest.mark.asyncio
    async def test_as_view_validation_error_returns_422(self):
        from pydantic import ValidationError

        class View(MinimalViewSet):
            async def list(self, request):
                raise ValidationError.from_exception_data("Body", [{"type": "missing", "loc": ("name",), "input": {}}])

        view_fn = View.as_view(actions={"get": "list"})
        request = MagicMock()
        request.method = "GET"
        response = await view_fn(request)
        assert response.status == HTTPStatus.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_as_view_http_exception_returns_status(self):
        from sanic.exceptions import Forbidden

        class View(MinimalViewSet):
            async def list(self, request):
                raise Forbidden("nope")

        view_fn = View.as_view(actions={"get": "list"})
        request = MagicMock()
        request.method = "GET"
        response = await view_fn(request)
        assert response.status == 403

    @pytest.mark.asyncio
    async def test_as_view_does_not_exist_returns_404(self):
        from tortoise.exceptions import DoesNotExist

        class View(MinimalViewSet):
            async def retrieve(self, request, pk):
                raise DoesNotExist("User")

        view_fn = View.as_view(actions={"get": "retrieve"})
        request = MagicMock()
        request.method = "GET"
        response = await view_fn(request, pk=1)
        assert response.status == HTTPStatus.HTTP_404_NOT_FOUND
