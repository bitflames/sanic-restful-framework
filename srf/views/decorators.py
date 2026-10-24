import asyncio
from collections.abc import Callable, Sequence
from functools import wraps

from pydantic import ValidationError
from sanic.exceptions import BadRequest


def action(
    *,
    detail: bool = False,
    methods: Sequence[str] = ("GET",),
    url_path: str | None = None,
    url_name: str | None = None,
    **kwargs,
) -> Callable:
    """
    Mark a method as a viewset action.

    :param methods: List of HTTP methods allowed for this action
    :param detail: If True, action requires a pk parameter. If False, action is on collection.
    :param url_path: Custom URL path for this action, default to be the name of the method
    :param url_name: Custom URL name for this action, default to be the name of the method
    """
    if not isinstance(detail, bool):
        raise TypeError("detail must be bool")

    def decorator(fun):
        is_async = asyncio.iscoroutinefunction(fun)

        if is_async:

            @wraps(fun)
            async def wrapper(self, *args, **kwargs):
                return await fun(self, *args, **kwargs)

        else:

            @wraps(fun)
            def wrapper(self, *args, **kwargs):
                return fun(self, *args, **kwargs)

        wrapper.extra_info = {
            "methods": methods,
            "detail": detail,
            "url_path": url_path if url_path else f"/{fun.__name__}",
            "url_name": url_name if url_name else fun.__name__,
            **kwargs,
        }

        return wrapper

    return decorator


def validate_request(show_errors: bool = False):
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            try:
                return await func(request, *args, **kwargs)
            except ValidationError as exc:
                if not show_errors:
                    message = "Invalid request parameters."
                else:
                    message = [
                        {
                            "field": ".".join(str(part) for part in error["loc"]),
                            "reason": error["msg"],
                        }
                        for error in exc.errors()
                    ]

                raise BadRequest(message) from None

        return wrapper

    return decorator
