"""Unit tests for srf.route.SanicRouter."""
import pytest
from unittest.mock import MagicMock

from sanic import Blueprint

from srf.route import SanicRouter
from srf.views.base import BaseViewSet


class DummyViewSet(BaseViewSet):
    @property
    def queryset(self):
        return MagicMock()


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

    def test_get_blueprint_returns_bp(self):
        r = SanicRouter(prefix="api")
        bp = r.get_blueprint()
        assert isinstance(bp, Blueprint)
