# API Reference: HTTP Status

`HTTPStatus` is an `IntEnum`: it provides readable constant names and can also be passed directly to Sanic as an integer. Use it instead of bare numbers when returning values from ViewSets. See [HTTP Status](../usage/advanced/http-status.md) for usage.

```python
from sanic.response import JSONResponse

from srf.views.http_status import HTTPStatus


async def handler(request):
    return JSONResponse({"ok": True}, status=HTTPStatus.HTTP_201_CREATED)
```

## Status code enum

::: srf.views.http_status.HTTPStatus
    options:
      heading_level: 4
      members: true
      show_source: false
      inherited_members: false

## Range predicates

These functions accept an integer (or an `HTTPStatus` member) and return a boolean:

| Function | Range |
| --- | --- |
| `is_informational` | `100 – 199` |
| `is_success` | `200 – 299` |
| `is_redirect` | `300 – 399` |
| `is_client_error` | `400 – 499` |
| `is_server_error` | `500 – 599` |

::: srf.views.http_status.is_informational
    options:
      heading_level: 4
      show_source: false

::: srf.views.http_status.is_success
    options:
      heading_level: 4
      show_source: false

::: srf.views.http_status.is_redirect
    options:
      heading_level: 4
      show_source: false

::: srf.views.http_status.is_client_error
    options:
      heading_level: 4
      show_source: false

::: srf.views.http_status.is_server_error
    options:
      heading_level: 4
      show_source: false

!!! note "Non-standard status codes"
    The enum also includes status codes that are not RFC standards or are deprecated, such as `HTTP_306_RESERVED` and `HTTP_509_BANDWIDTH_LIMIT_EXCEEDED`. They are kept only for naming completeness.
