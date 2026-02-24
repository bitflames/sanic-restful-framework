"""Unit tests for srf.views.decorators (action)."""

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
        @action(detail=True)
        def archive(self, request, pk):
            pass

        assert archive.extra_info["methods"] == ["get"]

    def test_action_default_url_path(self):
        @action(detail=False)
        def list_featured(self, request):
            pass

        assert list_featured.extra_info["url_path"] == "/list_featured"
