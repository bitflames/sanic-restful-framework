"""Unit tests for srf.views.decorators (action)."""

import pytest

from srf.views.decorators import action


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

    def test_action_keyword_only(self):
        with pytest.raises(TypeError):

            @action(False, ("GET",), "path")
            def positional_args(self, request):
                pass
