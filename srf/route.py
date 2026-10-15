import inspect

from sanic import Blueprint

from srf.views.base import GenericAPIView

COLLECTION_ACTIONS = {"get": "list", "post": "create"}
DETAIL_ACTIONS = {"get": "retrieve", "put": "update", "patch": "update", "delete": "destroy"}


def implemented_actions(view_cls: type[GenericAPIView], mapping: dict[str, str]) -> dict[str, str]:
    """Keep method→action pairs the view class actually defines."""
    return {method: action for method, action in mapping.items() if callable(getattr(view_cls, action, None))}


class SanicRouter:

    def __init__(self, bp: Blueprint = None, prefix: str = ""):
        self.prefix = f"/{prefix.strip('/')}" if prefix else ""
        self.bp = bp or Blueprint(self.prefix.strip("/") or "api")

    def register(self, path: str, view_cls: type[GenericAPIView], name: str | None = None) -> None:
        name = name or path
        path = path.strip("/")
        base_uri = f"{self.prefix}/{path}"

        # HTTP method → view action. patch stays on update until partial_update exists.
        collection = implemented_actions(view_cls, COLLECTION_ACTIONS)
        if collection:
            self.bp.add_route(
                view_cls.as_view(actions=collection),
                base_uri,
                methods=[method.upper() for method in collection],
                name=f"{name}-list",
            )

        detail = implemented_actions(view_cls, DETAIL_ACTIONS)
        if detail:
            self.bp.add_route(
                view_cls.as_view(actions=detail),
                f"{base_uri}/<pk>",
                methods=[method.upper() for method in detail],
                name=f"{name}-detail",
            )

        # decorator route: custom @action methods use the same as_view() so permission/exception handling are unified
        for func_name, func in inspect.getmembers(view_cls, predicate=inspect.isfunction):
            if extra_info := getattr(func, "extra_info", None):
                func_methods = {m.lower(): func_name for m in extra_info["methods"]}
                action_view = view_cls.as_view(actions=func_methods)

                if not extra_info.get("detail"):
                    uri = "/".join(
                        [
                            self.prefix.lstrip("/"),
                            path.rstrip("/"),
                            extra_info["url_path"].lstrip("/"),
                        ]
                    )
                else:
                    uri = "/".join(
                        [
                            self.prefix.lstrip("/"),
                            path.rstrip("/"),
                            "<pk>",
                            extra_info["url_path"].lstrip("/"),
                        ]
                    )
                self.bp.add_route(
                    action_view,
                    methods=extra_info["methods"],
                    uri=uri,
                    name=f"{name}-{extra_info['url_name']}",
                )

    def get_blueprint(self):
        return self.bp
