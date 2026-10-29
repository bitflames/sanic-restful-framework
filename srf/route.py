import inspect

from sanic import Blueprint, Sanic

from srf.views.base import GenericAPIView

COLLECTION_ACTIONS = {"get": "list", "head": "list", "post": "create"}
DETAIL_ACTIONS = {"get": "retrieve", "head": "retrieve", "put": "update", "patch": "update", "delete": "destroy"}


def implemented_actions(view_cls: type[GenericAPIView], mapping: dict[str, str]) -> dict[str, str]:
    """Keep method→action pairs the view class actually defines."""
    return {method: action for method, action in mapping.items() if callable(getattr(view_cls, action, None))}


class SanicRouter:
    """
    DRF-style router that registers a ViewSet as collection/detail routes on a
    Sanic app or Blueprint, and auto-discovers ``@action`` methods.

    Route names follow ``{name}-list``, ``{name}-detail`` and ``{name}-{url_name}``.
    """

    def __init__(self, instance: Sanic | Blueprint, prefix: str = ""):
        """
        Args:
            instance: Sanic app or Blueprint to register routes on.
            prefix: Optional URL prefix, e.g. ``"api"`` produces ``/api/<path>``.
        """
        self.prefix = f"/{prefix.strip('/')}" if prefix else ""
        if not isinstance(instance, (Sanic, Blueprint)):
            raise TypeError("instance must be a Sanic or Blueprint instance")
        self.instance = instance

    def register(self, path: str, view_cls: type[GenericAPIView], name: str | None = None) -> None:
        """
        Register ``view_cls`` under ``path``.

        Only implemented actions get routes: ``GET/POST {path}`` map to
        ``list``/``create``, ``GET/PUT/PATCH/DELETE {path}/<pk>`` map to
        ``retrieve``/``update``/``update``/``destroy``. Methods decorated with
        ``@action`` are discovered and registered automatically.

        Args:
            path: Resource path, e.g. ``"books"``.
            view_cls: The ViewSet class to register.
            name: Route name prefix; defaults to ``path``.
        """
        name = name or path
        path = path.strip("/")
        base_uri = f"{self.prefix}/{path}"

        # HTTP method → view action. patch stays on update until partial_update exists.
        collection = implemented_actions(view_cls, COLLECTION_ACTIONS)
        if collection:
            self.instance.add_route(
                view_cls.as_view(actions=collection),
                base_uri,
                methods=[method.upper() for method in collection],
                name=f"{name}-list",
            )

        detail = implemented_actions(view_cls, DETAIL_ACTIONS)
        if detail:
            self.instance.add_route(
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
                self.instance.add_route(
                    action_view,
                    methods=extra_info["methods"],
                    uri=uri,
                    name=f"{name}-{extra_info['url_name']}",
                )
