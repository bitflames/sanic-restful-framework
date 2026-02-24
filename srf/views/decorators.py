from functools import wraps
from typing import List


def action(
    methods: List[str] = None,
    detail: bool = None,
    url_path: str = None,
    url_name: str = None,
    **kwargs,
):
    """
    Mark a method as a viewset action.

    :param methods: List of HTTP methods allowed for this action
    :param detail: If True, action requires a pk parameter. If False, action is on collection.
    :param url_path: Custom URL path for this action
    :param url_name: Custom URL name for this action
    """
    if methods is None:
        methods = ["get"]
    if not isinstance(detail, (bool, type(None))):
        raise TypeError("detail must be bool or None")

    def decorator(fun):
        fun.extra_info = {
            "methods": methods,
            "detail": detail,
            "url_path": url_path if url_path else f"/{fun.__name__}",
            "url_name": (url_name if url_name else fun.__name__),  # TODO: support class-qualified name if needed
            **kwargs,
        }

        @wraps(fun)
        def wrapper(self, *args, **kwargs):
            return fun(self, *args, **kwargs)

        return wrapper

    return decorator
