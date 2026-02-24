import inspect

from sanic import Blueprint

from srf.views.base import BaseViewSet


class SanicRouter:
    def __init__(self, bp: Blueprint = None, prefix: str = ""):
        self.prefix = f"/{prefix.strip('/')}" if prefix else ""
        self.bp = bp or Blueprint(self.prefix.strip("/") or "api")

    def register(self, path: str, view_cls: BaseViewSet, name: str = None):
        name = name or path
        path = path.strip("/")
        base_uri = f"{self.prefix}/{path}"

        # List and create: collection route (no pk)
        self.bp.add_route(
            view_cls.as_view(actions={"get": "list", "post": "create"}),
            base_uri,
            methods=["GET", "POST"],
            name=f"{name}-list",
        )

        # Retrieve, update, destroy: detail route (with pk)
        detail_uri = f"{base_uri}/<pk:int>"
        self.bp.add_route(
            view_cls.as_view(
                actions={
                    "get": "retrieve",
                    "put": "update",
                    "patch": "update",
                    "delete": "destroy",
                }
            ),
            detail_uri,
            methods=["GET", "PUT", "PATCH", "DELETE"],
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
                            "<pk:int>",
                            extra_info["url_path"].lstrip("/"),
                        ]
                    )
                self.bp.add_route(
                    action_view,
                    methods=extra_info["methods"],
                    uri=uri,
                    name=extra_info["url_name"],
                )

    def get_blueprint(self):
        return self.bp
