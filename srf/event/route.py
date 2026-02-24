from sanic import Blueprint, Sanic

from .viewset import temp_event


def setup_routes(app: Sanic):
    bp = Blueprint(name="event", url_prefix="api")
    bp.add_route(temp_event, uri='events', methods=['POST'])
    app.blueprint(bp)
