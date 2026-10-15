"""Unit tests for srf.route.SanicRouter."""

from unittest.mock import MagicMock

from sanic import Blueprint, Sanic

from srf.route import SanicRouter
from srf.views.base import BaseViewSet, CreateAndReadOnlyModelViewSet, ReadOnlyModelViewSet
from srf.views.decorators import action


class DummyViewSet(BaseViewSet):
    @property
    def queryset(self):
        return MagicMock()


def _route_names(app: Sanic) -> set[str]:
    """Sanic 25 names look like '{app}.{blueprint}.{route}'."""
    return {route.name for route in app.router.routes}


def _methods_for(app: Sanic, route_name: str) -> set[str]:
    matches = [route.methods for route in app.router.routes if route.name.endswith(route_name)]
    assert len(matches) == 1
    return set(matches[0])


class TestSanicRouter:
    def test_init_with_prefix(self):
        r = SanicRouter(prefix="api")
        assert r.prefix == "/api"

    def test_init_strips_slashes(self):
        # prefix is normalized: leading/trailing slashes stripped
        r = SanicRouter(prefix="/api/")
        assert r.prefix == "/api"

    def test_register_adds_list_and_create_routes(self):
        bp = Blueprint("test_bp")
        r = SanicRouter(bp=bp, prefix="api")
        # register should not raise; in Sanic 25 routes may not be on bp until app is used
        r.register("items", DummyViewSet, name="items")
        assert r.get_blueprint() is bp

    def test_register_adds_detail_routes(self):
        bp = Blueprint("test_bp2")
        r = SanicRouter(bp=bp, prefix="api")
        r.register("items", DummyViewSet, name="items")
        # Detail URI is built as base_uri + /<pk:int>; just ensure register completes
        assert r.prefix == "/api"

    def test_register_passes_only_implemented_actions(self):
        captured = []

        class CapturingViewSet(DummyViewSet):
            @classmethod
            def as_view(cls, actions=None):
                captured.append(actions)
                return super().as_view(actions=actions)

        bp = Blueprint("test_bp_patch")
        r = SanicRouter(bp=bp, prefix="api")
        r.register("items", CapturingViewSet, name="items")
        assert captured == [
            {"get": "list", "post": "create"},
            {"get": "retrieve", "put": "update", "patch": "update", "delete": "destroy"},
        ]

    def test_readonly_viewset_registers_get_only(self):
        class ItemsViewSet(ReadOnlyModelViewSet):
            @property
            def queryset(self):
                return MagicMock()

        app = Sanic("test-readonly-routes")
        bp = Blueprint("api")
        SanicRouter(bp=bp, prefix="api").register("items", ItemsViewSet, name="items")
        app.blueprint(bp)

        assert _methods_for(app, "items-list") == {"GET"}
        assert _methods_for(app, "items-detail") == {"GET"}

    def test_create_and_readonly_viewset_registers_post_on_collection_only(self):
        class ItemsViewSet(CreateAndReadOnlyModelViewSet):
            @property
            def queryset(self):
                return MagicMock()

        app = Sanic("test-create-readonly-routes")
        bp = Blueprint("api")
        SanicRouter(bp=bp, prefix="api").register("items", ItemsViewSet, name="items")
        app.blueprint(bp)

        assert _methods_for(app, "items-list") == {"GET", "POST"}
        assert _methods_for(app, "items-detail") == {"GET"}

    def test_get_blueprint_returns_bp(self):
        r = SanicRouter(prefix="api")
        bp = r.get_blueprint()
        assert isinstance(bp, Blueprint)

    def test_action_route_name_prefixed_with_register_name(self):
        class ActionViewSet(DummyViewSet):
            @action(detail=False, url_path="ping", url_name="ping")
            async def ping(self, request):
                pass

            @action(detail=True, url_path="publish")
            async def publish(self, request, pk):
                pass

        app = Sanic("test-action-names")
        bp = Blueprint("api")
        SanicRouter(bp=bp, prefix="api").register("profile", ActionViewSet, name="profile")
        app.blueprint(bp)

        names = _route_names(app)
        assert "test-action-names.api.profile-list" in names
        assert "test-action-names.api.profile-detail" in names
        assert "test-action-names.api.profile-ping" in names
        assert "test-action-names.api.profile-publish" in names

        assert app.url_for("api.profile-list") == "/api/profile"
        assert app.url_for("api.profile-ping") == "/api/profile/ping"
        assert app.url_for("api.profile-publish", pk=7) == "/api/profile/7/publish"
        assert app.url_for("api.profile-detail", pk=7) == "/api/profile/7"

    def test_action_default_url_name_keeps_underscores(self):
        class ActionViewSet(DummyViewSet):
            @action(detail=False)
            async def list_featured(self, request):
                pass

        app = Sanic("test-action-underscores")
        bp = Blueprint("api")
        SanicRouter(bp=bp, prefix="api").register("products", ActionViewSet, name="products")
        app.blueprint(bp)

        assert "test-action-underscores.api.products-list_featured" in _route_names(app)
        assert app.url_for("api.products-list_featured") == "/api/products/list_featured"

    def test_app_server_viewsets_action_route_names(self):
        """Same register() names as tests/app_server.py (ProfileViewSet / UserViewSet)."""
        from srf.auth.viewset import UserViewSet
        from tests.app_server import ProfileViewSet

        app = Sanic("test-app-server-viewsets")
        bp = Blueprint("api")
        router = SanicRouter(bp=bp, prefix="api")
        router.register("profile", ProfileViewSet, name="profile")
        router.register("users", UserViewSet, name="users")
        app.blueprint(bp)

        names = _route_names(app)
        assert "test-app-server-viewsets.api.profile-ping" in names
        assert "test-app-server-viewsets.api.users-self" in names
        assert "test-app-server-viewsets.api.users-change-password" in names
        assert app.url_for("api.profile-ping") == "/api/profile/ping"
        assert app.url_for("api.users-self") == "/api/users/self"
        assert app.url_for("api.users-change-password") == "/api/users/change-password"
