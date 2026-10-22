"""SanicRouter.register and direct add_route both dispatch the action map passed to as_view."""

import pytest
from sanic import Blueprint, Sanic, json
from sanic.exceptions import MethodNotAllowed

from srf.route import SanicRouter
from srf.views.base import GenericAPIView


class CustomActionViewSet(GenericAPIView):
    """Action name is whatever as_view is given; it does not have to be list/retrieve."""

    async def qwe(self, request):
        return json({"action": self.action, "handler": "qwe"})


class EchoViewSet(GenericAPIView):
    async def list(self, request):
        return json({"action": self.action, "kind": "list"})

    async def retrieve(self, request, pk):
        return json({"action": self.action, "kind": "retrieve", "pk": pk})

    async def create(self, request):
        return json({"action": self.action, "kind": "create"}, status=201)


def test_router_register_dispatches_implemented_actions():
    app = Sanic("reg-router")
    bp = Blueprint("reg-router-api")
    SanicRouter(bp, prefix="api").register("echo", EchoViewSet, name="echo")
    app.blueprint(bp)

    _, listed = app.test_client.get("/api/echo")
    assert listed.status == 200
    assert listed.json == {"action": "list", "kind": "list"}

    _, created = app.test_client.post("/api/echo")
    assert created.status == 201
    assert created.json["action"] == "create"

    _, detail = app.test_client.get("/api/echo/7")
    assert detail.status == 200
    assert detail.json == {"action": "retrieve", "kind": "retrieve", "pk": "7"}

    # EchoViewSet has no update, so the detail route does not include PUT.
    _, updated = app.test_client.put("/api/echo/7")
    assert updated.status == 405


def test_add_route_dispatches_explicit_actions():
    app = Sanic("reg-manual")
    bp = Blueprint("reg-manual-api")
    bp.add_route(
        EchoViewSet.as_view({"get": "list", "post": "create"}),
        "/api/manual",
        methods=["GET", "POST"],
        name="manual-list",
    )
    app.blueprint(bp)
    # methods omitted: Sanic accepts GET only. The action name still comes from as_view.
    app.add_route(
        EchoViewSet.as_view({"get": "retrieve"}),
        "/api/manual/<pk>",
        name="manual-detail",
    )

    _, listed = app.test_client.get("/api/manual")
    assert listed.status == 200
    assert listed.json == {"action": "list", "kind": "list"}

    _, created = app.test_client.post("/api/manual")
    assert created.status == 201
    assert created.json["action"] == "create"

    _, detail = app.test_client.get("/api/manual/3")
    assert detail.status == 200
    assert detail.json == {"action": "retrieve", "kind": "retrieve", "pk": "3"}

    _, updated = app.test_client.put("/api/manual/3")
    assert updated.status == 405


def test_as_view_custom_action_name_runs():
    app = Sanic("reg-custom-action")
    app.add_route(
        CustomActionViewSet.as_view({"get": "qwe"}),
        "/api/public/qwe",
        name="custom-qwe",
    )

    _, response = app.test_client.get("/api/public/qwe")
    assert response.status == 200
    assert response.json == {"action": "qwe", "handler": "qwe"}


@pytest.mark.asyncio
async def test_as_view_does_not_keep_unpassed_actions():
    view_fn = EchoViewSet.as_view({"get": "list"})
    request = type("Request", (), {"method": "POST"})()
    with pytest.raises(MethodNotAllowed):
        await view_fn(request)
