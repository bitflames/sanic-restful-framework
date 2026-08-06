# 异常处理

SRF 定义了两个异常类，并在 `BaseViewSet.as_view()` 内捕获部分 ORM、
Pydantic 和 HTTP 异常。它没有安装全局统一异常处理器。

## SRF 异常

```python
from srf.exceptions import ImproperlyConfigured, TargetObjectAlreadyExist
```

- `TargetObjectAlreadyExist`：`HTTPException` 子类，状态码 409。
- `ImproperlyConfigured`：`HTTPException` 子类，状态码 500。

它们只定义状态码和说明，没有自定义 JSON 响应结构。最终响应格式取决于异常
发生位置：在 ViewSet handler 内会经过 SRF 的捕获逻辑，其他路由则由 Sanic
处理。

## ViewSet 内置处理

`BaseViewSet.as_view()` 在调用 handler 时处理：

| 异常 | 响应 |
|---|---|
| `tortoise.exceptions.DoesNotExist` | 404 文本响应 |
| `pydantic.ValidationError` | 422 JSON：`{"detail": str(error)}` |
| `sanic.exceptions.HTTPException` | 异常状态码，JSON：`{"detail": ...}` |

例如：

```python
from sanic.exceptions import BadRequest


class ProductViewSet(BaseViewSet):
    async def create(self, request):
        if request.json is None:
            raise BadRequest("请求体不能为空")
        # ...
```

权限检查发生在这个 `try` 块之前，因此 `check_permissions()` 抛出的
`Forbidden` 由 Sanic 处理，不经过上述 JSON 转换。

## CRUD 的特殊行为

- `get_object()` 使用 `get_or_none()`，对象不存在时抛出 Sanic `NotFound`。
- `perform_create()` 把 Tortoise `IntegrityError` 转成 409
  `HTTPException(detail="data conflict")`。
- 请求 JSON 为 `None` 时，内置 create/update 直接返回空 400 响应。

## 全局统一响应

如果应用需要一致格式，应注册 Sanic 异常处理器：

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

注意：ViewSet 已捕获并转换的异常不会再到达这个全局处理器。若要让所有端点
完全统一，需要同时调整 `BaseViewSet.as_view()` 的捕获策略。

生产环境可另加兜底处理器，但不要向客户端暴露堆栈：

```python
from sanic.log import error_logger


@app.exception(Exception)
async def handle_unexpected_error(request, exception):
    error_logger.exception("Unhandled exception")
    return json(
        {"error": "INTERNAL_ERROR", "message": "服务器内部错误"},
        status=500,
    )
```

## Pydantic 错误

当前内置响应使用 `str(error)`。若客户端需要结构化字段错误，可在自定义
ViewSet handler 中返回 `error.errors()`，或修改框架捕获逻辑：

```python
except ValidationError as error:
    return JSONResponse(
        {"errors": error.errors(include_url=False)},
        status=422,
    )
```

## 最佳实践

1. **分类异常**：为不同类型的错误使用不同的异常类
2. **友好的错误信息**：提供清晰、有帮助的错误消息
3. **统一响应格式**：使用一致的错误响应结构
4. **记录详细日志**：记录错误的上下文信息
5. **隐藏内部细节**：生产环境不暴露内部错误
6. **使用适当的状态码**：为不同错误使用正确的 HTTP 状态码
7. **国际化**：支持多语言错误消息
## 下一步

- 学习 [HTTP 状态码](http-status.md) 了解状态码使用
- 阅读 [认证](../core/authentication.md) 了解认证异常
- 查看 [视图](../core/viewsets.md) 了解 ViewSet 中的异常处理
