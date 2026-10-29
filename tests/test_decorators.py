"""Unit tests for srf.views.decorators (action, validate_request)."""

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel
from sanic.exceptions import BadRequest

from srf.exceptions import PydanticValidationException
from srf.views.decorators import action, validate_request


class TestActionDecorator:
    def test_action_sets_extra_info(self):
        @action(detail=False, url_path="custom", methods=["get"])
        def my_action(self):
            pass

        assert hasattr(my_action, "extra_info")
        assert my_action.extra_info["detail"] is False
        assert my_action.extra_info["url_path"] == "custom"
        assert my_action.extra_info["methods"] == ["get"]

    def test_action_default_methods(self):
        @action(detail=True, url_path="archive")
        def archive(self, request, pk):
            pass

        assert archive.extra_info["methods"] == ("GET",)
        assert archive.extra_info["detail"] is True
        assert archive.extra_info["url_path"] == "archive"

    def test_action_default_url_path_and_name(self):
        @action(detail=False)
        def list_featured(self, request):
            pass

        assert list_featured.extra_info["url_path"] == "/list_featured"
        assert list_featured.extra_info["url_name"] == "list_featured"

    def test_action_custom_url_name_is_suffix_only(self):
        @action(detail=False, url_path="ping", url_name="ping")
        def ping(self, request):
            pass

        assert ping.extra_info["url_name"] == "ping"

    def test_action_async_passthrough(self):
        @action(detail=False, url_path="ping")
        async def ping(self, request):
            return {"ok": True}

        assert ping.extra_info["url_path"] == "ping"

    @pytest.mark.asyncio
    async def test_action_async_wrapper_invokes_fun(self):
        @action(detail=False, url_path="ping")
        async def ping(self, request):
            return {"ok": True, "user": request}

        result = await ping(None, "req")
        assert result == {"ok": True, "user": "req"}

    def test_action_detail_must_be_bool(self):
        with pytest.raises(TypeError, match="detail must be bool"):

            @action(detail="yes")
            def bad(self, request):
                pass

    def test_action_keyword_only(self):
        with pytest.raises(TypeError):

            @action(False, ("GET",), "path")
            def positional_args(self, request):
                pass


class _Body(BaseModel):
    name: str
    age: int


class TestValidateRequest:
    @pytest.mark.asyncio
    async def test_validation_error_becomes_422(self):
        @validate_request(show_errors=True)
        async def handler(request):
            return _Body.model_validate(request.json)

        request = MagicMock()
        request.json = {"age": "not-an-int"}

        with pytest.raises(PydanticValidationException) as exc_info:
            await handler(request)

        assert exc_info.value.status_code == 422
        assert "name" in str(exc_info.value)
        assert "age" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validation_error_hides_details_by_default(self):
        @validate_request()
        async def handler(request):
            return _Body.model_validate(request.json)

        request = MagicMock()
        request.json = {}

        with pytest.raises(PydanticValidationException, match="Invalid request parameters"):
            await handler(request)

    @pytest.mark.asyncio
    async def test_non_validation_errors_pass_through(self):
        @validate_request()
        async def handler(request):
            raise BadRequest("business error")

        with pytest.raises(BadRequest, match="business error"):
            await handler(MagicMock())
