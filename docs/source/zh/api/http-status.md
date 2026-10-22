# API 参考：HTTP Status

`HTTPStatus` 是 `IntEnum`，既提供可读的常量名，也能直接作为整数传给 Sanic。写 ViewSet 返回值时用它代替裸数字。使用说明见 [状态码](../usage/advanced/http-status.md)。

```python
from sanic.response import JSONResponse

from srf.views.http_status import HTTPStatus


async def handler(request):
    return JSONResponse({"ok": True}, status=HTTPStatus.HTTP_201_CREATED)
```

## 状态码枚举

::: srf.views.http_status.HTTPStatus
    options:
      heading_level: 4
      members: true
      show_source: false
      inherited_members: false

## 区间判断函数

这些函数接收整数（或 `HTTPStatus` 成员）并返回布尔值：

| 函数 | 区间 |
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

!!! note "非标准状态码"
    枚举中也包含 `HTTP_306_RESERVED`、`HTTP_509_BANDWIDTH_LIMIT_EXCEEDED` 等非 RFC 标准或已弃用的状态码，保留它们只是为了命名完整性。
