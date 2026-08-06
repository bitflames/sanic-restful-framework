# Exception Handling

SRF defines two exception classes and catches some ORM, Pydantic, and HTTP exceptions within `BaseViewSet.as_view()`. It does not install a global unified exception handler.

## SRF Exceptions

```python
from srf.exceptions import ImproperlyConfigured, TargetObjectAlreadyExist
```

- `TargetObjectAlreadyExist`: Subclass of `HTTPException`, status code 409.
- `ImproperlyConfigured`: Subclass of `HTTPException`, status code 500.

They only define status codes and descriptions, without custom JSON response structure. The final response format depends on where the exception occurs: inside ViewSet handler it goes through SRF's catching logic, while other routes are handled by Sanic.

## ViewSet Built-in Handling

`BaseViewSet.as_view()` handles the following when calling the handler:

| Exception | Response |
|---|---|
| `tortoise.exceptions.DoesNotExist` | 404 text response |
| `pydantic.ValidationError` | 422 JSON: `{"detail": str(error)}` |
| `sanic.exceptions.HTTPException` | Exception status code, JSON: `{"detail": ...}` |

For example:

```python
from sanic.exceptions import BadRequest


class ProductViewSet(BaseViewSet):
    async def create(self, request):
        if request.json is None:
            raise BadRequest("Request body cannot be empty")
        # ...
```

Permission checks happen before this `try` block, so `Forbidden` raised by `check_permissions()` is handled by Sanic, not going through the above JSON conversion.

## Special Behavior for CRUD

- `get_object()` uses `get_or_none()`, throwing Sanic `NotFound` if the object doesn't exist.
- `perform_create()` converts Tortoise `IntegrityError` to 409 `HTTPException(detail="data conflict")`.
- When the request JSON is `None`, built-in create/update directly returns an empty 400 response.

## Global Unified Response

If your application needs consistent formatting, register a Sanic exception handler:

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

Note: Exceptions already caught and converted by ViewSet will not reach this global handler. To achieve full uniformity across all endpoints, you need to adjust the catching strategy in `BaseViewSet.as_view()` as well.

In production environment, you can add a fallback handler, but do not expose stack traces to clients:

```python
from sanic.log import error_logger


@app.exception(Exception)
async def handle_unexpected_error(request, exception):
    error_logger.exception("Unhandled exception")
    return json(
        {"error": "INTERNAL_ERROR", "message": "Server internal error"},
        status=500,
    )
```

## Pydantic Errors

The current built-in response uses `str(error)`. If the client needs structured field errors, you can return `error.errors()` in a custom ViewSet handler, or modify the framework's catching logic:

```python
except ValidationError as error:
    return JSONResponse(
        {"errors": error.errors(include_url=False)},
        status=422,
    )
```

## Best Practices

1. **Categorize Exceptions**: Use different exception classes for different types of errors
2. **Friendly Error Messages**: Provide clear and helpful error messages
3. **Consistent Response Format**: Use a consistent error response structure
4. **Log Detailed Context**: Record context information for errors
5. **Hide Internal Details**: Do not expose internal errors in production
6. **Use Appropriate Status Codes**: Use correct HTTP status codes for different errors
7. **Internationalization**: Support multilingual error messages
## Next Steps

- Learn [HTTP Status Codes](http-status.md) to understand their usage
- Read [Authentication](../core/authentication.md) to understand authentication exceptions
- View [Views](../core/viewsets.md) to understand exception handling in ViewSet