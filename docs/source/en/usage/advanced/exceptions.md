# Exception Handling

SRF defines several exception classes and, inside `GenericAPIView.as_view()`, converts Pydantic / Tortoise
validation errors into 422 exceptions. It does not install a global unified exception handler.

## SRF exceptions

```python
from srf.exceptions import ImproperlyConfigured, PydanticValidationException, TargetObjectAlreadyExist, TooManyRequest
```

- `TargetObjectAlreadyExist`: An `HTTPException` subclass with status code 409 (`quiet=True`).
- `ImproperlyConfigured`: An `HTTPException` subclass with status code 500.
- `PydanticValidationException`: An `HTTPException` subclass with status code 422 (`quiet=True`).
- `TooManyRequest`: An `HTTPException` subclass with status code 429 (`quiet=True`), raised when verification code attempts exceed the limit.

They only define status codes and have no custom JSON response structure; the final response format is decided by Sanic's default
exception handling (or handlers registered by the application).

## Built-in ViewSet handling

`as_view()` only catches two kinds of validation errors in the `try` block around the handler call:

| Exception                             | Handling                                                                    |
| ------------------------------------- | --------------------------------------------------------------------------- |
| `pydantic.ValidationError`            | Converted to `PydanticValidationException` (422), with message `str(error)` |
| `tortoise.exceptions.ValidationError` | Same as above, converted to 422                                             |

Apart from these two kinds, `as_view()` **does not catch** other exceptions:

- Sanic `NotFound` (404) raised by `get_object()` is passed directly to Sanic.
- Any `HTTPException` raised inside the handler (such as `BadRequest`, `Forbidden`) is also passed directly to Sanic.
- `check_permissions()` runs before the `try` block, and the `Forbidden` it raises is likewise handled by Sanic.

For example:

```python
from sanic.exceptions import BadRequest
from srf.views import BaseViewSet


class ProductViewSet(BaseViewSet):
    async def create(self, request):
        if request.json is None:
            raise BadRequest("The request body cannot be empty")
        # ...
```

## Special CRUD behavior

- `get_object()` uses `get_or_none()` and raises Sanic `NotFound` when the object does not exist or the primary key cannot be parsed.
- `perform_create()` converts Tortoise `IntegrityError` into a 409
  `TargetObjectAlreadyExist(message="data conflict")`.
- When the request JSON is `None`, the built-in create/update return an empty 400 response directly.

## Global unified responses

If the application needs a consistent format, register a Sanic exception handler:

```python
from sanic.exceptions import HTTPException
from sanic.response import json


@app.exception(HTTPException)
async def handle_http_exception(request, exception):
    return json(
        {
            "error": type(exception).__name__,
            "message": getattr(exception, "message", str(exception)),
        },
        status=exception.status_code,
    )
```

Note: the `PydanticValidationException` produced by `as_view()` is also an `HTTPException`,
so it reaches this global handler; the application can use that to output a unified format.

In production you can add a fallback handler, but do not expose stack traces to clients:

```python
from sanic.log import error_logger


@app.exception(Exception)
async def handle_unexpected_error(request, exception):
    error_logger.exception("Unhandled exception")
    return json(
        {"error": "INTERNAL_ERROR", "message": "Internal server error"},
        status=500,
    )
```

## Pydantic errors

The built-in response currently uses `str(error)`. If clients need structured field errors, you can return `error.errors()`
in a custom ViewSet handler, or modify the framework's capture logic:

```python
except ValidationError as error:
    return JSONResponse(
        {"errors": error.errors(include_url=False)},
        status=422,
    )
```

## Best practices

1. **Classify exceptions**: use different exception classes for different kinds of errors
2. **Friendly error messages**: provide clear, helpful error messages
3. **Unified response format**: use a consistent error response structure
4. **Log details**: log contextual information about errors
5. **Hide internal details**: do not expose internal errors in production
6. **Use appropriate status codes**: use the correct HTTP status code for different errors
7. **Internationalization**: support error messages in multiple languages

## Next steps

- Study [HTTP Status](http-status.md) to learn about using status codes
- Read [Authentication](../core/authentication.md) to learn about authentication exceptions
- See [Views](../core/viewsets.md) to learn about exception handling in ViewSets
