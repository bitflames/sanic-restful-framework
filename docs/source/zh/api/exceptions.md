# API 参考：Exceptions

SRF 的公开异常都继承自 Sanic 的 `HTTPException`，由 Sanic 统一转换成 JSON 响应。使用说明见 [异常](../usage/advanced/exceptions.md)。

```python
from srf.exceptions import (
    ImproperlyConfigured,
    PydanticValidationException,
    TargetObjectAlreadyExist,
    TooManyRequest,
)
```

## 异常一览

| 异常                          | 状态码 | 典型触发场景                                              |
| ----------------------------- | ------ | --------------------------------------------------------- |
| `TargetObjectAlreadyExist`    | `409`  | 创建时违反唯一约束；自定义更新逻辑中也可主动抛出          |
| `PydanticValidationException` | `422`  | Pydantic 或 Tortoise 的 `ValidationError`                 |
| `ImproperlyConfigured`        | `500`  | 配置项类型不合法（如 `INSTALLED_APPS` 不是列表）          |
| `TooManyRequest`              | `429`  | 验证码错误次数超限（如注册时的 `confirmations` 重试过多） |

`TargetObjectAlreadyExist`、`PydanticValidationException` 与 `TooManyRequest` 设置了 `quiet = True`，Sanic 不会把对应请求记为错误日志。

## 异常在 ViewSet 中的转换

`GenericAPIView.as_view()` 包裹视图方法，并做以下转换：

| 原始异常                              | 转换结果                                                                    |
| ------------------------------------- | --------------------------------------------------------------------------- |
| `pydantic.ValidationError`            | `PydanticValidationException` → `422`                                       |
| `tortoise.exceptions.ValidationError` | `PydanticValidationException` → `422`                                       |
| `tortoise.exceptions.IntegrityError`  | `CreateModelMixin.perform_create()` 转为 `TargetObjectAlreadyExist` → `409` |

`UpdateModelMixin.perform_update()` 本身不捕获 `IntegrityError`；需要把唯一约束冲突转成 409 时，应在子类（参考 `UserViewSet.perform_update`）中捕获并抛出 `TargetObjectAlreadyExist`。

`NotFound`、`Forbidden`、`BadRequest`、`MethodNotAllowed` 等 Sanic 内置异常保持原状态码，不做包装。

响应体由 Sanic 的 `JSONRenderer` 生成：

```json
{
  "description": "Unprocessable Entity",
  "status": 422,
  "message": "..."
}
```

## 异常类

::: srf.exceptions.TargetObjectAlreadyExist
options:
heading_level: 4
members: false
show_source: false
inherited_members: false

::: srf.exceptions.PydanticValidationException
options:
heading_level: 4
members: false
show_source: false
inherited_members: false

::: srf.exceptions.ImproperlyConfigured
options:
heading_level: 4
members: false
show_source: false
inherited_members: false

`ImproperlyConfigured` 主要在 `LazySettings` 初始化时抛出：`ALLOWED_HOSTS`、`INSTALLED_APPS`、`TEMPLATE_DIRS`、`LOCALE_PATHS`、`SECRET_KEY_FALLBACKS` 必须是列表或元组。
