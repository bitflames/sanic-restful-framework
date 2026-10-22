# 异常处理

SRF 定义了多个异常类，并在 `GenericAPIView.as_view()` 内将 Pydantic / Tortoise
的验证错误转换为 422 异常。它没有安装全局统一异常处理器。

## SRF 异常

```python
from srf.exceptions import ImproperlyConfigured, PydanticValidationException, TargetObjectAlreadyExist
```

- `TargetObjectAlreadyExist`：`HTTPException` 子类，状态码 409（`quiet=True`）。
- `ImproperlyConfigured`：`HTTPException` 子类，状态码 500。
- `PydanticValidationException`：`HTTPException` 子类，状态码 422（`quiet=True`）。

它们只定义状态码，没有自定义 JSON 响应结构；最终响应格式由 Sanic 的默认
异常处理（或应用注册的处理器）决定。

## ViewSet 内置处理

`as_view()` 只在调用 handler 的 `try` 块中捕获两类验证错误：

| 异常 | 处理 |
|---|---|
| `pydantic.ValidationError` | 转为 `PydanticValidationException`（422），message 为 `str(error)` |
| `tortoise.exceptions.ValidationError` | 同上，转为 422 |

除这两类之外，`as_view()` **不捕获**其他异常：

- `get_object()` 抛出的 Sanic `NotFound`（404）直接交给 Sanic 处理。
- handler 内抛出的任何 `HTTPException`（如 `BadRequest`、`Forbidden`）也直接交给 Sanic。
- `check_permissions()` 在 `try` 块之前执行，其抛出的 `Forbidden` 同样由 Sanic 处理。

例如：

```python
from sanic.exceptions import BadRequest
from srf.views import BaseViewSet


class ProductViewSet(BaseViewSet):
    async def create(self, request):
        if request.json is None:
            raise BadRequest("请求体不能为空")
        # ...
```

## CRUD 的特殊行为

- `get_object()` 使用 `get_or_none()`，对象不存在或主键无法解析时抛出 Sanic `NotFound`。
- `perform_create()` 把 Tortoise `IntegrityError` 转成 409
  `TargetObjectAlreadyExist(message="data conflict")`。
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

注意：`as_view()` 转换出的 `PydanticValidationException` 也是 `HTTPException`，
会到达上面这个全局处理器；应用可以据此输出统一格式。

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
